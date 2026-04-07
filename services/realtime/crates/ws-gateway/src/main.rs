use anyhow::{Context, Result};
use axum::{
    extract::{
        ws::{Message, WebSocket, WebSocketUpgrade},
        Path, State,
    },
    response::IntoResponse,
    routing::get,
    Json, Router,
};
use chrono::{DateTime, Utc};
use futures_util::StreamExt;
use serde::Serialize;
use serde_json::{json, Value};
use shared::{scaffold_banner, EngineBookUpdatedEvent, EngineOrderUpdatedEvent, EngineTradeExecutedEvent};
use std::{
    collections::HashMap,
    env, fs,
    sync::Arc,
};
use tokio::sync::{broadcast, RwLock};
use tracing::{error, info, warn};
use uuid::Uuid;

#[derive(Clone)]
struct GatewayConfig {
    host: String,
    port: u16,
    redis_url: String,
    orders_events_channel: String,
    trades_channel: String,
    books_channel: String,
}

impl GatewayConfig {
    fn from_env() -> Self {
        for candidate in env_candidates() {
            let _ = dotenvy::from_path_override(&candidate);
        }

        Self {
            host: env::var("WS_GATEWAY_HOST")
                .ok()
                .or_else(|| read_env_value("WS_GATEWAY_HOST"))
                .or_else(|| env::var("WS_HOST").ok())
                .or_else(|| read_env_value("WS_HOST"))
                .unwrap_or_else(|| "0.0.0.0".to_string()),
            port: env::var("WS_GATEWAY_PORT")
                .ok()
                .or_else(|| read_env_value("WS_GATEWAY_PORT"))
                .or_else(|| env::var("WS_PORT").ok())
                .or_else(|| read_env_value("WS_PORT"))
                .and_then(|value| value.parse::<u16>().ok())
                .unwrap_or(9000),
            redis_url: resolve_redis_url(),
            orders_events_channel: env::var("MATCHING_ENGINE_ORDERS_EVENTS_CHANNEL")
                .unwrap_or_else(|_| "engine.orders.accepted".to_string()),
            trades_channel: env::var("MATCHING_ENGINE_TRADES_CHANNEL")
                .unwrap_or_else(|_| "engine.trades.executed".to_string()),
            books_channel: env::var("MATCHING_ENGINE_BOOKS_CHANNEL")
                .unwrap_or_else(|_| "engine.books.updated".to_string()),
        }
    }
}

#[derive(Clone, Default)]
struct GatewayState {
    market_channels: Arc<RwLock<HashMap<Uuid, broadcast::Sender<String>>>>,
}

impl GatewayState {
    async fn subscribe(&self, market_id: Uuid) -> broadcast::Receiver<String> {
        self.sender_for(market_id).await.subscribe()
    }

    async fn publish(&self, market_id: Uuid, payload: String) {
        let sender = self.sender_for(market_id).await;
        let _ = sender.send(payload);
    }

    async fn sender_for(&self, market_id: Uuid) -> broadcast::Sender<String> {
        if let Some(existing) = self.market_channels.read().await.get(&market_id).cloned() {
            return existing;
        }

        let mut guard = self.market_channels.write().await;
        guard
            .entry(market_id)
            .or_insert_with(|| {
                let (sender, _) = broadcast::channel(256);
                sender
            })
            .clone()
    }
}

#[derive(Serialize)]
struct HealthResponse {
    service: &'static str,
    status: &'static str,
}

#[derive(Serialize)]
struct GatewayEventEnvelope {
    event_type: String,
    market_id: Uuid,
    payload: Value,
    published_at: DateTime<Utc>,
}

#[tokio::main]
async fn main() -> Result<()> {
    tracing_subscriber::fmt()
        .with_env_filter(env::var("RUST_LOG").unwrap_or_else(|_| "ws_gateway=info,redis=warn".to_string()))
        .init();

    let config = GatewayConfig::from_env();
    let state = GatewayState::default();

    info!("{}", scaffold_banner("ws-gateway"));
    info!(
        host = %config.host,
        port = config.port,
        orders_channel = %config.orders_events_channel,
        trades_channel = %config.trades_channel,
        books_channel = %config.books_channel,
        "starting websocket gateway"
    );

    let app = Router::new()
        .route("/health", get(health))
        .route("/ws/markets/{market_id}", get(market_socket))
        .with_state(state.clone());

    let listener = tokio::net::TcpListener::bind((config.host.as_str(), config.port))
        .await
        .context("failed to bind websocket gateway listener")?;

    let pubsub_state = state.clone();
    let pubsub_config = config.clone();
    let pubsub_task = tokio::spawn(async move { run_pubsub_loop(pubsub_config, pubsub_state).await });

    tokio::select! {
        server_result = axum::serve(listener, app) => {
            server_result.context("websocket gateway server exited unexpectedly")?;
        }
        pubsub_result = pubsub_task => {
            pubsub_result
                .context("websocket gateway pubsub task panicked")?
                .context("websocket gateway pubsub loop failed")?;
        }
        ctrl_c = tokio::signal::ctrl_c() => {
            ctrl_c.context("failed to listen for ctrl+c")?;
            info!("received shutdown signal");
        }
    }

    Ok(())
}

async fn health() -> Json<HealthResponse> {
    Json(HealthResponse {
        service: "ws-gateway",
        status: "ok",
    })
}

async fn market_socket(
    ws: WebSocketUpgrade,
    Path(market_id): Path<Uuid>,
    State(state): State<GatewayState>,
) -> impl IntoResponse {
    ws.on_upgrade(move |socket| handle_market_socket(socket, market_id, state))
}

async fn handle_market_socket(mut socket: WebSocket, market_id: Uuid, state: GatewayState) {
    let mut receiver = state.subscribe(market_id).await;

    if let Ok(subscribed_payload) = serde_json::to_string(&GatewayEventEnvelope {
        event_type: "subscribed".to_string(),
        market_id,
        payload: json!({ "market_id": market_id }),
        published_at: Utc::now(),
    }) {
        if socket.send(Message::Text(subscribed_payload.into())).await.is_err() {
            return;
        }
    }

    loop {
        tokio::select! {
            market_event = receiver.recv() => match market_event {
                Ok(payload) => {
                    if socket.send(Message::Text(payload.into())).await.is_err() {
                        break;
                    }
                }
                Err(broadcast::error::RecvError::Lagged(skipped)) => {
                    warn!(market_id = %market_id, skipped, "websocket client lagged behind market stream");
                }
                Err(broadcast::error::RecvError::Closed) => break,
            },
            socket_message = socket.recv() => match socket_message {
                Some(Ok(Message::Ping(payload))) => {
                    if socket.send(Message::Pong(payload)).await.is_err() {
                        break;
                    }
                }
                Some(Ok(Message::Close(_))) | None => break,
                Some(Ok(_)) => {}
                Some(Err(error)) => {
                    warn!(market_id = %market_id, ?error, "websocket client error");
                    break;
                }
            }
        }
    }
}

async fn run_pubsub_loop(config: GatewayConfig, state: GatewayState) -> Result<()> {
    let redis_client = redis::Client::open(config.redis_url.clone()).context("failed to create redis client")?;
    let mut pubsub = redis_client
        .get_async_pubsub()
        .await
        .context("failed to open redis pubsub connection")?;

    pubsub
        .subscribe(&config.orders_events_channel)
        .await
        .context("failed to subscribe to order events")?;
    pubsub
        .subscribe(&config.trades_channel)
        .await
        .context("failed to subscribe to trade events")?;
    pubsub
        .subscribe(&config.books_channel)
        .await
        .context("failed to subscribe to book events")?;

    let mut stream = pubsub.on_message();
    while let Some(message) = stream.next().await {
        let channel = message.get_channel_name().to_string();
        let payload: String = message
            .get_payload()
            .context("failed to decode redis pubsub payload")?;

        if let Err(error) = dispatch_pubsub_message(&state, &config, &channel, &payload).await {
            error!(%channel, %payload, ?error, "failed to dispatch pubsub event");
        }
    }

    Ok(())
}

async fn dispatch_pubsub_message(
    state: &GatewayState,
    config: &GatewayConfig,
    channel: &str,
    payload: &str,
) -> Result<()> {
    if channel == config.orders_events_channel {
        let event: EngineOrderUpdatedEvent =
            serde_json::from_str(payload).context("failed to parse order update event")?;
        publish_market_event(state, "order_updated", event.market_id, &event).await?;
    } else if channel == config.trades_channel {
        let event: EngineTradeExecutedEvent =
            serde_json::from_str(payload).context("failed to parse trade executed event")?;
        publish_market_event(state, "trade_executed", event.market_id, &event).await?;
    } else if channel == config.books_channel {
        let event: EngineBookUpdatedEvent =
            serde_json::from_str(payload).context("failed to parse book updated event")?;
        publish_market_event(state, "book_updated", event.market_id, &event).await?;
    }

    Ok(())
}

async fn publish_market_event<T: Serialize>(
    state: &GatewayState,
    event_type: &str,
    market_id: Uuid,
    payload: &T,
) -> Result<()> {
    let envelope = GatewayEventEnvelope {
        event_type: event_type.to_string(),
        market_id,
        payload: serde_json::to_value(payload).context("failed to serialize gateway payload")?,
        published_at: Utc::now(),
    };
    let serialized = serde_json::to_string(&envelope).context("failed to serialize gateway envelope")?;
    state.publish(market_id, serialized).await;
    Ok(())
}

fn resolve_redis_url() -> String {
    if let Ok(redis_url) = env::var("REDIS_URL") {
        return redis_url;
    }
    if let Some(redis_url) = read_env_value("REDIS_URL") {
        return redis_url;
    }

    let host = env::var("REDIS_HOST")
        .ok()
        .or_else(|| read_env_value("REDIS_HOST"))
        .unwrap_or_else(|| "localhost".to_string());
    let port = env::var("REDIS_PORT")
        .ok()
        .or_else(|| read_env_value("REDIS_PORT"))
        .unwrap_or_else(|| "6379".to_string());
    let password = env::var("REDIS_PASSWORD").ok().or_else(|| read_env_value("REDIS_PASSWORD"));

    if let Some(password) = password.filter(|value| !value.is_empty()) {
        format!("redis://:{password}@{host}:{port}/0")
    } else {
        format!("redis://{host}:{port}/0")
    }
}

fn env_candidates() -> Vec<std::path::PathBuf> {
    let mut candidates = Vec::new();
    if let Ok(current_dir) = env::current_dir() {
        for ancestor in current_dir.ancestors() {
            candidates.push(ancestor.join(".env"));
        }
    }
    candidates
}

fn read_env_value(key: &str) -> Option<String> {
    for candidate in env_candidates() {
        let Ok(contents) = fs::read_to_string(candidate) else {
            continue;
        };
        for line in contents.lines() {
            let trimmed = line.trim();
            if trimmed.is_empty() || trimmed.starts_with('#') {
                continue;
            }
            let Some((name, value)) = trimmed.split_once('=') else {
                continue;
            };
            if name.trim() == key {
                return Some(value.trim().trim_matches('"').to_string());
            }
        }
    }
    None
}
