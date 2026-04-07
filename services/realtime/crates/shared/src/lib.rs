use chrono::{DateTime, Utc};
use rust_decimal::Decimal;
use serde::{Deserialize, Serialize};
use uuid::Uuid;

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum EngineCommandType {
    MatchOrder,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EngineOrderCommand {
    pub event_type: EngineCommandType,
    pub order_id: Uuid,
    pub market_id: Uuid,
    pub outcome_id: Uuid,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum EngineOrderStatus {
    PendingAcceptance,
    Open,
    PartiallyFilled,
    Filled,
    Cancelled,
    Rejected,
    Expired,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EngineOrderUpdatedEvent {
    pub order_id: Uuid,
    pub market_id: Uuid,
    pub outcome_id: Uuid,
    pub status: EngineOrderStatus,
    pub matched_quantity: Decimal,
    pub remaining_quantity: Decimal,
    pub accepted_at: Option<DateTime<Utc>>,
    pub rejection_reason: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EngineTradeExecutedEvent {
    pub trade_id: Uuid,
    pub market_id: Uuid,
    pub outcome_id: Uuid,
    pub maker_order_id: Uuid,
    pub taker_order_id: Uuid,
    pub quantity: Decimal,
    pub price: Decimal,
    pub gross_notional: Decimal,
    pub executed_at: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EngineBookUpdatedEvent {
    pub market_id: Uuid,
    pub outcome_id: Uuid,
    pub best_bid: Option<Decimal>,
    pub best_ask: Option<Decimal>,
    pub updated_at: DateTime<Utc>,
}

pub fn scaffold_banner(service: &str) -> String {
    format!("satta realtime: {service}")
}
