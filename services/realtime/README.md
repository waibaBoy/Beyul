# Realtime Services

Rust workspace for execution-critical services.

Crates:

- `matching-engine`: order matching and execution
- `price-feed`: external reference price ingestion
- `ws-gateway`: websocket fanout
- `shared`: domain primitives shared across crates

## Local matching path

Current v1 wiring:

1. FastAPI writes a new order to `public.orders` with status `pending_acceptance`.
2. FastAPI pushes a JSON command onto Redis list `engine.orders.incoming`.
3. `matching-engine` pops that command, matches against resting orders in Postgres, inserts `public.trades`, and updates `public.orders`.
4. The engine publishes order, trade, and book updates over Redis Pub/Sub for later websocket fanout.

Current Redis keys/channels:

- queue: `engine.orders.incoming`
- pub/sub: `engine.orders.accepted`
- pub/sub: `engine.trades.executed`
- pub/sub: `engine.books.updated`

## Run locally

1. Start Redis.
2. Start FastAPI.
3. From `services/realtime`, run:
   - `cargo run -p matching-engine`
   - `cargo run -p ws-gateway`
4. Create or cancel orders from the web app.
5. Open a market detail page. The web app will subscribe to `ws://localhost:9000/ws/markets/{market_id}` and refresh the shell when book, trade, or order events arrive.
6. If the gateway is not running, the market page falls back to manual refresh after order actions.

Config note:

- the matching engine now looks for the repo root `.env`
- if `POSTGRES_DSN` exists, it will reuse it automatically
- `postgresql+asyncpg://...` is converted to a normal `postgresql://...` URL for Rust/sqlx
- the websocket gateway reads `WS_GATEWAY_HOST` / `WS_GATEWAY_PORT` and also falls back to `WS_HOST` / `WS_PORT`
