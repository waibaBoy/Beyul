from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import CurrentActor, get_current_actor
from app.core.container import container
from app.schemas.advanced_orders import (
    ConditionalOrderListResponse,
    ConditionalOrderRequest,
    ConditionalOrderResponse,
)
from app.schemas.common import MessageResponse

router = APIRouter(prefix="/orders/conditional", tags=["advanced-orders"])


def _get_service():
    return container.advanced_order_service


def _order_to_response(order) -> ConditionalOrderResponse:
    return ConditionalOrderResponse(
        id=order.id,
        market_slug=order.market_slug,
        outcome_id=order.outcome_id,
        side=order.side,
        quantity=str(order.quantity),
        trigger_price=str(order.trigger_price),
        limit_price=str(order.limit_price) if order.limit_price else None,
        order_type=order.order_type,
        trailing_offset_bps=order.trailing_offset_bps,
        status=order.status,
        created_at=order.created_at.isoformat(),
    )


@router.post("", response_model=ConditionalOrderResponse)
async def create_conditional_order(
    payload: ConditionalOrderRequest,
    actor: CurrentActor = Depends(get_current_actor),
):
    svc = _get_service()
    order = svc.create_conditional_order(
        profile_id=actor.id,
        market_slug=payload.market_slug,
        outcome_id=payload.outcome_id,
        side=payload.side,
        quantity=payload.quantity,
        trigger_price=payload.trigger_price,
        limit_price=payload.limit_price,
        order_type=payload.order_type,
        trailing_offset_bps=payload.trailing_offset_bps,
    )
    return _order_to_response(order)


@router.get("", response_model=ConditionalOrderListResponse)
async def list_conditional_orders(
    actor: CurrentActor = Depends(get_current_actor),
):
    svc = _get_service()
    orders = svc.list_orders(actor.id)
    return ConditionalOrderListResponse(
        orders=[_order_to_response(o) for o in orders],
        count=len(orders),
    )


@router.delete("/{order_id}", response_model=MessageResponse)
async def cancel_conditional_order(
    order_id: UUID,
    actor: CurrentActor = Depends(get_current_actor),
):
    svc = _get_service()
    result = svc.cancel_order(actor.id, order_id)
    if not result:
        raise HTTPException(status_code=404, detail="Order not found")
    return MessageResponse(message=f"Order {order_id} cancelled")
