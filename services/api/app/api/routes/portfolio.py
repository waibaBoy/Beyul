import csv
import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.deps import CurrentActor, get_current_actor, get_trading_service
from app.schemas.portfolio import PortfolioSummaryResponse
from app.services.trading_service import TradingService

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("/me", response_model=PortfolioSummaryResponse)
async def get_my_portfolio(
    actor: CurrentActor = Depends(get_current_actor),
    service: TradingService = Depends(get_trading_service),
) -> PortfolioSummaryResponse:
    return await service.get_portfolio_summary(actor)


@router.get("/me/export.csv")
async def export_portfolio_csv(
    actor: CurrentActor = Depends(get_current_actor),
    service: TradingService = Depends(get_trading_service),
) -> StreamingResponse:
    summary = await service.get_portfolio_summary(actor)
    buf = io.StringIO()
    writer = csv.writer(buf)

    writer.writerow(["Section: Balances"])
    writer.writerow(["Asset", "Rail", "Account", "Settled", "Reserved", "Available"])
    for b in summary.balances:
        writer.writerow([b.asset_code, b.rail_mode, b.account_code, b.settled_balance, b.reserved_balance, b.available_balance])

    writer.writerow([])
    writer.writerow(["Section: Positions"])
    writer.writerow(["Market", "Outcome", "Qty", "Avg Entry", "Cost", "Realized PnL", "Unrealized PnL", "Status", "Last Trade"])
    for p in summary.positions:
        writer.writerow([
            p.market_title, p.outcome_label, p.quantity,
            p.average_entry_price or "", p.net_cost, p.realized_pnl, p.unrealized_pnl,
            p.market_status, str(p.last_trade_at or ""),
        ])

    writer.writerow([])
    writer.writerow(["Section: Recent Trades"])
    writer.writerow(["Outcome", "Price", "Qty", "Gross Notional", "Fee", "Time"])
    for t in summary.recent_trades:
        writer.writerow([t.outcome_label, t.price, t.quantity, t.gross_notional, t.fee_amount, str(t.executed_at)])

    buf.seek(0)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"portfolio_{ts}.csv"
    return StreamingResponse(
        buf,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
