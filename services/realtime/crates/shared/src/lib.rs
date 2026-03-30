use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MarketEvent {
    pub topic: String,
    pub payload: String,
}

pub fn scaffold_banner(service: &str) -> String {
    format!("beyul realtime scaffold: {service}")
}
