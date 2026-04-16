"use client";

import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { beyulApiFetch } from "@/lib/api/beyul-api";

type OrderType = "stop_loss" | "take_profit" | "trailing_stop";
type Side = "buy" | "sell";

type ConditionalOrder = {
  id: string;
  order_type: OrderType;
  side: Side;
  quantity: string;
  trigger_price: string;
  limit_price: string | null;
  trailing_offset_bps: number | null;
  status: string;
  outcome_id: string;
};

type AdvancedOrderFormProps = {
  marketSlug: string;
  outcomeId: string;
  outcomeName: string;
  currentPrice?: number;
};

const ORDER_TYPE_LABELS: Record<OrderType, string> = {
  stop_loss: "Stop Loss",
  take_profit: "Take Profit",
  trailing_stop: "Trailing Stop",
};

export function AdvancedOrderForm({ marketSlug, outcomeId, outcomeName, currentPrice }: AdvancedOrderFormProps) {
  const { getAccessToken, session } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const [orderType, setOrderType] = useState<OrderType>("stop_loss");
  const [side, setSide] = useState<Side>("buy");
  const [quantity, setQuantity] = useState("");
  const [triggerPrice, setTriggerPrice] = useState("");
  const [limitPrice, setLimitPrice] = useState("");
  const [trailingBps, setTrailingBps] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [orders, setOrders] = useState<ConditionalOrder[]>([]);
  const [isLoadingOrders, setIsLoadingOrders] = useState(false);

  const fetchOrders = useCallback(async () => {
    if (!session) return;
    setIsLoadingOrders(true);
    try {
      const accessToken = await getAccessToken();
      const data = await beyulApiFetch<{ orders: ConditionalOrder[]; count: number }>(
        `/api/v1/orders/conditional?market_slug=${encodeURIComponent(marketSlug)}`,
        { accessToken }
      );
      setOrders(data.orders.filter((o) => o.outcome_id === outcomeId));
    } catch {
      /* silently ignore list errors */
    } finally {
      setIsLoadingOrders(false);
    }
  }, [session, getAccessToken, marketSlug, outcomeId]);

  useEffect(() => {
    if (isOpen && session) {
      void fetchOrders();
    }
  }, [isOpen, session, fetchOrders]);

  const handleSubmit = async () => {
    setError(null);
    setIsSubmitting(true);
    try {
      const accessToken = await getAccessToken();
      const body: Record<string, unknown> = {
        market_slug: marketSlug,
        outcome_id: outcomeId,
        side,
        quantity: Number(quantity),
        trigger_price: Number(triggerPrice),
        order_type: orderType,
      };
      if (orderType !== "trailing_stop" && limitPrice) {
        body.limit_price = Number(limitPrice);
      }
      if (orderType === "trailing_stop" && trailingBps) {
        body.trailing_offset_bps = Number(trailingBps);
      }
      await beyulApiFetch("/api/v1/orders/conditional", {
        method: "POST",
        accessToken,
        json: body,
      });
      setQuantity("");
      setTriggerPrice("");
      setLimitPrice("");
      setTrailingBps("");
      await fetchOrders();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to place order.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancel = async (orderId: string) => {
    try {
      const accessToken = await getAccessToken();
      await beyulApiFetch(`/api/v1/orders/conditional/${orderId}`, {
        method: "DELETE",
        accessToken,
      });
      setOrders((prev) => prev.filter((o) => o.id !== orderId));
    } catch {
      /* silently ignore cancel errors */
    }
  };

  const canSubmit = !isSubmitting && quantity && triggerPrice && (orderType !== "trailing_stop" || trailingBps);

  return (
    <div className="ao-section">
      <button className="ao-header" type="button" onClick={() => setIsOpen((v) => !v)}>
        <span className="ao-header-title">Advanced Orders</span>
        <span className={`ao-chevron ${isOpen ? "is-open" : ""}`}>▼</span>
      </button>

      {isOpen && (
        <div className="ao-body">
          {/* Order type pills */}
          <div className="ao-type-pills">
            {(["stop_loss", "take_profit", "trailing_stop"] as const).map((t) => (
              <button
                key={t}
                className={`ao-type-pill ${orderType === t ? "is-active" : ""}`}
                type="button"
                onClick={() => setOrderType(t)}
              >
                {ORDER_TYPE_LABELS[t]}
              </button>
            ))}
          </div>

          {/* Side pills */}
          <div className="ao-side-pills">
            <button
              className={`ao-side-pill ${side === "buy" ? "is-buy" : ""}`}
              type="button"
              onClick={() => setSide("buy")}
            >
              Buy
            </button>
            <button
              className={`ao-side-pill ${side === "sell" ? "is-sell" : ""}`}
              type="button"
              onClick={() => setSide("sell")}
            >
              Sell
            </button>
          </div>

          {/* Quantity */}
          <div className="ao-field">
            <label className="ao-label">Quantity</label>
            <input
              className="ao-input"
              type="number"
              min="0"
              step="any"
              placeholder="0"
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
            />
          </div>

          {/* Trigger price */}
          <div className="ao-field">
            <label className="ao-label">Trigger Price</label>
            <input
              className="ao-input"
              type="number"
              min="0"
              max="1"
              step="0.01"
              placeholder="0.00"
              value={triggerPrice}
              onChange={(e) => setTriggerPrice(e.target.value)}
            />
            {currentPrice != null && (
              <span className="ao-hint">
                Current price: {Math.round(currentPrice * 100)}¢ ({outcomeName})
              </span>
            )}
          </div>

          {/* Limit price — only for stop_loss / take_profit */}
          {orderType !== "trailing_stop" && (
            <div className="ao-field">
              <label className="ao-label">Limit Price (optional)</label>
              <input
                className="ao-input"
                type="number"
                min="0"
                max="1"
                step="0.01"
                placeholder="0.00"
                value={limitPrice}
                onChange={(e) => setLimitPrice(e.target.value)}
              />
            </div>
          )}

          {/* Trailing offset — only for trailing_stop */}
          {orderType === "trailing_stop" && (
            <div className="ao-field">
              <label className="ao-label">Trail % (basis points)</label>
              <input
                className="ao-input"
                type="number"
                min="0"
                step="1"
                placeholder="e.g. 500 = 5%"
                value={trailingBps}
                onChange={(e) => setTrailingBps(e.target.value)}
              />
            </div>
          )}

          {error && <p className="ao-hint" style={{ color: "#ef4444" }}>{error}</p>}

          <button
            className="ao-submit"
            type="button"
            disabled={!canSubmit}
            onClick={handleSubmit}
          >
            {isSubmitting ? "Placing..." : `Place ${ORDER_TYPE_LABELS[orderType]} Order`}
          </button>

          {/* Active conditional orders */}
          <div className="ao-orders">
            <span className="ao-orders-title">Active conditional orders</span>
            {isLoadingOrders ? (
              <p className="ao-empty">Loading…</p>
            ) : orders.length === 0 ? (
              <p className="ao-empty">No conditional orders for this outcome.</p>
            ) : (
              orders.map((order) => (
                <div className="ao-order-row" key={order.id}>
                  <div className="ao-order-info">
                    <span className="ao-order-type">{order.order_type.replace(/_/g, " ")}</span>
                    <span>{order.side}</span>
                    <span>qty {order.quantity}</span>
                    <span>@ {Math.round(Number(order.trigger_price) * 100)}¢</span>
                    <span className="pill">{order.status}</span>
                  </div>
                  <button className="ao-order-cancel" type="button" onClick={() => handleCancel(order.id)}>
                    Cancel
                  </button>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
