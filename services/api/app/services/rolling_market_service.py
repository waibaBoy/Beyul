from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import re
from uuid import UUID

import httpx
from sqlalchemy import func, insert, select

from app.core.config import settings
from app.core.exceptions import ConflictError
from app.db.session import SessionLocal
from app.db.tables import market_outcomes, markets, settlement_sources
from app.repositories.base import MarketRepository
from app.schemas.admin import RollingUpDownRunRequest, RollingUpDownRunResponse
from app.schemas.market import MarketResponse
from app.schemas.portfolio import MarketSettlementFinalizeRequest, MarketSettlementRequestCreateRequest

_ROLLING_SLUG_RE = re.compile(r"^(?P<symbol>[a-z0-9]+)-(?P<interval>\d+)m-up-down-(?P<window>\d{12})$")


@dataclass(frozen=True)
class _Window:
    start_at: datetime
    end_at: datetime


def _floor_to_interval(now: datetime, interval_minutes: int) -> datetime:
    total_minutes = now.hour * 60 + now.minute
    floored_minutes = total_minutes - (total_minutes % interval_minutes)
    return now.replace(hour=floored_minutes // 60, minute=floored_minutes % 60, second=0, microsecond=0)


def _window_slug(symbol: str, interval_minutes: int, window_start: datetime) -> str:
    asset = symbol.lower().replace("/", "").replace("-", "")
    return f"{asset}-{interval_minutes}m-up-down-{window_start.strftime('%Y%m%d%H%M')}"


def _window_title(symbol: str, interval_minutes: int, window: _Window) -> str:
    asset = symbol.replace("USDT", "/USDT")
    return f"{asset} up in next {interval_minutes}m? ({window.start_at:%H:%M}–{window.end_at:%H:%M} UTC)"


def _window_question(symbol: str, interval_minutes: int, window: _Window) -> str:
    asset = symbol.replace("USDT", "/USDT")
    return (
        f"Will {asset} close higher at {window.end_at:%H:%M} UTC than at {window.start_at:%H:%M} UTC "
        f"for the {interval_minutes}-minute interval?"
    )


class RollingMarketService:
    def __init__(self, market_repository: MarketRepository) -> None:
        self._market_repository = market_repository

    async def run_up_down_cycle(self, admin_actor_id: UUID, payload: RollingUpDownRunRequest) -> RollingUpDownRunResponse:
        if settings.repository_backend != "postgres":
            raise ConflictError("Rolling 5-minute automation currently requires repository_backend=postgres.")

        if payload.interval_minutes < 1 or payload.interval_minutes > 60:
            raise ConflictError("interval_minutes must be between 1 and 60.")
        if payload.lookahead_windows < 1 or payload.lookahead_windows > 24:
            raise ConflictError("lookahead_windows must be between 1 and 24.")

        symbol = payload.symbol.strip().upper() or "BTCUSDT"
        now = datetime.now(UTC)
        floor = _floor_to_interval(now, payload.interval_minutes)

        response = RollingUpDownRunResponse(symbol=symbol, interval_minutes=payload.interval_minutes)
        existing = {market.slug: market for market in await self._market_repository.list_markets()}

        # Create the next N rolling windows.
        for offset in range(payload.lookahead_windows):
            start_at = floor + timedelta(minutes=offset * payload.interval_minutes)
            end_at = start_at + timedelta(minutes=payload.interval_minutes)
            window = _Window(start_at=start_at, end_at=end_at)
            slug = _window_slug(symbol, payload.interval_minutes, start_at)
            if slug in existing:
                response.skipped_existing_markets.append(slug)
                continue
            created = await self._create_direct_market(
                admin_actor_id=admin_actor_id,
                symbol=symbol,
                interval_minutes=payload.interval_minutes,
                slug=slug,
                window=window,
            )
            response.created_markets.append(created.slug)
            existing[created.slug] = created
            if payload.auto_open_markets:
                opened = await self._market_repository.update_market_status(created.slug, "open")
                existing[opened.slug] = opened
                response.opened_markets.append(opened.slug)

        # Trigger settlement flow for elapsed rolling windows.
        if payload.request_settlement_for_due:
            for market in list(existing.values()):
                window = self._parse_rolling_window(market.slug)
                if window is None:
                    continue
                if market.status not in {"open", "pending_liquidity"}:
                    continue
                if window.end_at > now:
                    continue
                try:
                    settlement = await self._market_repository.request_settlement(
                        market.slug,
                        admin_actor_id,
                        MarketSettlementRequestCreateRequest(
                            source_reference_url=self._build_reference_url(symbol),
                            notes=f"Auto-requested by rolling {payload.interval_minutes}m scheduler.",
                        ),
                    )
                    response.settlement_requested.append(market.slug)
                    if payload.finalize_due_markets:
                        winner_code = await self._compute_winner_code(
                            symbol=symbol,
                            interval_minutes=payload.interval_minutes,
                            window=window,
                        )
                        winner = next((outcome for outcome in market.outcomes if outcome.code == winner_code), None)
                        if winner is None:
                            response.warnings.append(
                                f"Could not find {winner_code} outcome for {market.slug}; skipped finalize."
                            )
                            continue
                        await self._market_repository.settle_market(
                            market.slug,
                            admin_actor_id,
                            MarketSettlementFinalizeRequest(
                                winning_outcome_id=winner.id,
                                source_reference_url=self._build_reference_url(symbol),
                                notes=f"Auto-finalized from {symbol} kline open/close.",
                                candidate_id=settlement.candidate_id,
                            ),
                        )
                        response.settlement_finalized.append(market.slug)
                except Exception as exc:  # best-effort loop; continue processing others
                    response.warnings.append(f"{market.slug}: {exc}")

        return response

    async def _create_direct_market(
        self,
        *,
        admin_actor_id: UUID,
        symbol: str,
        interval_minutes: int,
        slug: str,
        window: _Window,
    ) -> MarketResponse:
        settlement_source_id = await self._resolve_or_create_settlement_source()
        async with SessionLocal() as session:
            result = await session.execute(
                insert(markets)
                .values(
                    slug=slug,
                    title=_window_title(symbol, interval_minutes, window),
                    question=_window_question(symbol, interval_minutes, window),
                    description=(
                        "Automated rolling interval market. Resolves Yes if close price is greater than open price "
                        f"for the {interval_minutes}-minute window."
                    ),
                    rules_text=(
                        f"Reference symbol: {symbol}. Compare Binance kline open and close for "
                        f"{window.start_at.isoformat()} to {window.end_at.isoformat()}."
                    ),
                    market_access_mode="public",
                    rail_mode="onchain",
                    status="pending_liquidity",
                    resolution_mode="oracle",
                    settlement_source_id=settlement_source_id,
                    settlement_reference_url=self._build_reference_url(symbol),
                    settlement_reference_label="Binance Spot (rolling interval)",
                    trading_opens_at=window.start_at,
                    trading_closes_at=window.end_at,
                    resolution_due_at=window.end_at,
                    min_seed_amount=0,
                    min_liquidity_amount=0,
                    min_participants=2,
                    creator_id=admin_actor_id,
                    creator_fee_bps=0,
                    platform_fee_bps=200,
                    total_volume=0,
                    total_trades_count=0,
                    metadata={
                        "contract": {
                            "contract_type": "up_down_interval",
                            "category": "crypto",
                            "subcategory": "rolling",
                            "reference_asset": symbol,
                            "reference_symbol": symbol,
                            "interval_label": f"{interval_minutes}m",
                            "reference_source_label": "Binance Spot",
                            "notes": "Auto-generated rolling up/down interval market.",
                        }
                    },
                    created_at=func.now(),
                    updated_at=func.now(),
                )
                .returning(markets.c.slug)
            )
            market_slug = result.scalar_one()
            await session.execute(
                insert(market_outcomes).values(
                    market_id=select(markets.c.id).where(markets.c.slug == market_slug).scalar_subquery(),
                    code="YES",
                    label="Yes",
                    outcome_index=0,
                    status="active",
                    created_at=func.now(),
                    updated_at=func.now(),
                )
            )
            await session.execute(
                insert(market_outcomes).values(
                    market_id=select(markets.c.id).where(markets.c.slug == market_slug).scalar_subquery(),
                    code="NO",
                    label="No",
                    outcome_index=1,
                    status="active",
                    created_at=func.now(),
                    updated_at=func.now(),
                )
            )
            await session.commit()
        return await self._market_repository.get_market(slug)

    async def _resolve_or_create_settlement_source(self) -> UUID:
        async with SessionLocal() as session:
            existing = (
                await session.execute(
                    select(settlement_sources.c.id).where(settlement_sources.c.code == "binance_rolling_oracle")
                )
            ).scalar_one_or_none()
            if existing is not None:
                return existing
            created = await session.execute(
                insert(settlement_sources)
                .values(
                    code="binance_rolling_oracle",
                    name="Binance rolling interval oracle",
                    resolution_mode="oracle",
                    base_url=self._build_reference_url("BTCUSDT"),
                )
                .returning(settlement_sources.c.id)
            )
            settlement_source_id = created.scalar_one()
            await session.commit()
            return settlement_source_id

    def _parse_rolling_window(self, slug: str) -> _Window | None:
        match = _ROLLING_SLUG_RE.match(slug)
        if match is None:
            return None
        interval_minutes = int(match.group("interval"))
        start_at = datetime.strptime(match.group("window"), "%Y%m%d%H%M").replace(tzinfo=UTC)
        return _Window(start_at=start_at, end_at=start_at + timedelta(minutes=interval_minutes))

    async def _compute_winner_code(self, *, symbol: str, interval_minutes: int, window: _Window) -> str:
        open_price, close_price = await self._fetch_open_close(
            symbol=symbol,
            interval_minutes=interval_minutes,
            window=window,
        )
        return "YES" if close_price > open_price else "NO"

    async def _fetch_open_close(self, *, symbol: str, interval_minutes: int, window: _Window) -> tuple[float, float]:
        interval = f"{interval_minutes}m"
        params = {
            "symbol": symbol,
            "interval": interval,
            "startTime": int(window.start_at.timestamp() * 1000),
            "endTime": int(window.end_at.timestamp() * 1000),
            "limit": 1,
        }
        async with httpx.AsyncClient(base_url=settings.binance_api_base_url, timeout=10.0) as client:
            response = await client.get("/api/v3/klines", params=params)
            response.raise_for_status()
            payload = response.json()
        if not payload:
            raise ConflictError("No Binance kline data found for settlement window.")
        candle = payload[0]
        return float(candle[1]), float(candle[4])  # open, close

    @staticmethod
    def _build_reference_url(symbol: str) -> str:
        return f"https://www.binance.com/en/trade/{symbol}"
