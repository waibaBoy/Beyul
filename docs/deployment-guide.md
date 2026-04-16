# Satta — Production Deployment Guide

This document covers deploying the Satta prediction market platform to a production (or staging) environment. It assumes you have already cloned the repository and are familiar with the local development setup.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Architecture Overview](#architecture-overview)
3. [Environment Variables](#environment-variables)
4. [Database Setup](#database-setup)
5. [Backend API Deployment](#backend-api-deployment)
6. [Frontend Deployment](#frontend-deployment)
7. [Matching Engine](#matching-engine)
8. [WebSocket Gateway](#websocket-gateway)
9. [Health Checks and Monitoring](#health-checks-and-monitoring)
10. [TLS, DNS, and Reverse Proxy](#tls-dns-and-reverse-proxy)
11. [CI/CD](#cicd)
12. [Operational Runbook](#operational-runbook)

---

## Prerequisites

| Dependency        | Minimum Version | Purpose                        |
| ----------------- | --------------- | ------------------------------ |
| Node.js           | 20 LTS          | Next.js frontend               |
| Python            | 3.12+           | FastAPI backend                |
| Rust toolchain    | stable (latest) | Matching engine, WS gateway    |
| PostgreSQL        | 15+             | Primary datastore              |
| Redis             | 7+              | Pub/sub, order queues, caching |
| Supabase project  | —               | Auth, Row-Level Security       |

Optional: Docker 24+, k6 (load testing), Playwright (E2E tests).

---

## Architecture Overview

```
                ┌────────────┐
  Browser ──────│  Next.js   │──── SSR / static
                │  (Vercel)  │
                └─────┬──────┘
                      │ REST
                      ▼
                ┌────────────┐      ┌─────────────────┐
                │  FastAPI   │◄────►│   PostgreSQL 16  │
                │  (uvicorn) │      └─────────────────┘
                └──┬─────┬───┘
                   │     │ Redis pub/sub
          WebSocket│     ▼
                   │  ┌──────────────────┐
                   │  │ Matching Engine   │
                   │  │ (Rust)            │
                   │  └──────────────────┘
                   ▼
             ┌──────────────┐
             │ WS Gateway   │
             │ (Rust/axum)  │
             └──────────────┘
```

All services communicate through PostgreSQL (persistent state) and Redis (real-time messaging). The matching engine consumes orders from a Redis queue, executes trades, and publishes events back through Redis channels that the API and WS gateway consume.

---

## Environment Variables

### Backend API (`services/api`)

These map to fields in `app/core/config.py` via pydantic-settings (case-insensitive).

#### Core Application

| Variable                | Required | Default             | Description                                      |
| ----------------------- | -------- | ------------------- | ------------------------------------------------ |
| `APP_ENV`               | Yes      | `development`       | `development`, `staging`, or `production`         |
| `API_HOST`              | No       | `0.0.0.0`           | Bind address for uvicorn                          |
| `API_PORT`              | No       | `8000`              | Bind port for uvicorn                             |
| `REPOSITORY_BACKEND`    | Yes      | `memory`            | `memory` (dev only) or `postgres` (required prod) |
| `CORS_ALLOWED_ORIGINS`  | Yes      | `http://localhost:3000` | Comma-separated allowed origins              |
| `BLOCKED_JURISDICTIONS` | No       | `""`                | Comma-separated ISO country codes to block        |

#### Database and Cache

| Variable       | Required | Default                                                     | Description              |
| -------------- | -------- | ----------------------------------------------------------- | ------------------------ |
| `POSTGRES_DSN` | Yes      | `postgresql+asyncpg://beyul:change_me@localhost:5432/beyul` | Async PostgreSQL DSN     |
| `REDIS_URL`    | Yes      | `redis://localhost:6379/0`                                  | Redis connection string  |

> **Production safety**: The API refuses to start if `APP_ENV` is `production` or `staging` and `POSTGRES_DSN` still contains `change_me`.

#### Supabase

| Variable                     | Required | Default | Description                       |
| ---------------------------- | -------- | ------- | --------------------------------- |
| `SUPABASE_URL`               | Yes      | `""`    | Supabase project URL              |
| `SUPABASE_SERVICE_ROLE_KEY`  | Yes      | `""`    | Service-role key (server-side)    |
| `SUPABASE_JWT_SECRET`        | Yes      | `""`    | JWT verification secret           |

#### Authentication

| Variable                     | Required | Default        | Description                                 |
| ---------------------------- | -------- | -------------- | ------------------------------------------- |
| `JWT_SECRET`                 | Yes      | `change_me`    | Must be a strong secret in production        |
| `JWT_ALGORITHM`              | No       | `HS256`        | JWT signing algorithm                        |
| `ACCESS_TOKEN_EXPIRE_MINUTES`| No       | `60`           | Token TTL                                    |
| `ALLOW_DEV_AUTH`             | No       | `true`         | **Must be `false` in production**            |
| `ADMIN_EMAIL`                | No       | `""`           | Email for the admin account                  |

#### Oracle (UMA / Resolution)

| Variable                        | Required        | Default               | Description                         |
| ------------------------------- | --------------- | --------------------- | ----------------------------------- |
| `ORACLE_PROVIDER`               | Yes             | `mock`                | `mock` (dev) or `uma` (production)  |
| `ORACLE_CALLBACK_SECRET`        | Yes (prod)      | `dev-oracle-secret`   | Webhook HMAC secret                 |
| `ORACLE_RPC_URL`                | If `uma`        | `""`                  | Polygon RPC endpoint                |
| `ORACLE_SIGNER_PRIVATE_KEY`     | If `uma`        | `""`                  | Signer wallet private key           |
| `ORACLE_SIGNER_ADDRESS`         | If `uma`        | `""`                  | Signer wallet address               |
| `ORACLE_CURRENCY_ADDRESS`       | If `uma`        | `""`                  | Bond currency contract address      |
| `ORACLE_UMA_OO_ADDRESS`         | If `uma`        | `""`                  | UMA Optimistic Oracle address       |
| `ORACLE_UMA_FINDER_ADDRESS`     | If `uma`        | `""`                  | UMA Finder contract address         |
| `ORACLE_UMA_ASSERTION_IDENTIFIER`| No             | `ASSERT_TRUTH2`       | UMA assertion identifier            |
| `ORACLE_UMA_ESCALATION_MANAGER` | If `uma`        | `""`                  | Escalation manager address          |
| `ORACLE_CHAIN_ID`               | No              | `137`                 | Chain ID (137 = Polygon mainnet)    |
| `ORACLE_REWARD_WEI`             | No              | `0`                   | Assertion reward in wei             |
| `ORACLE_BOND_WEI`               | No              | `0`                   | Assertion bond in wei               |
| `ORACLE_LIVENESS_MINUTES`       | No              | `120`                 | Dispute window duration             |
| `ORACLE_EXECUTION_MODE`         | No              | `simulated`           | `simulated` or `live`               |

#### Market Data

| Variable                | Required | Default                    | Description                   |
| ----------------------- | -------- | -------------------------- | ----------------------------- |
| `MARKET_DATA_PROVIDER`  | No       | `none`                     | `none` or `binance`           |
| `BINANCE_API_BASE_URL`  | No       | `https://api.binance.com`  | Binance REST API base URL     |

#### Matching Engine Channels (shared with Rust services)

| Variable                                | Default                    |
| --------------------------------------- | -------------------------- |
| `MATCHING_ENGINE_ORDERS_QUEUE`          | `engine.orders.incoming`   |
| `MATCHING_ENGINE_ORDERS_EVENTS_CHANNEL` | `engine.orders.accepted`   |
| `MATCHING_ENGINE_TRADES_CHANNEL`        | `engine.trades.executed`   |
| `MATCHING_ENGINE_BOOKS_CHANNEL`         | `engine.books.updated`     |

#### WebSocket

| Variable         | Default                 | Description               |
| ---------------- | ----------------------- | ------------------------- |
| `WS_PUBLIC_URL`  | `ws://localhost:9000`   | Public-facing WS endpoint |

### Frontend (`apps/web`)

Set these as build-time environment variables (prefixed with `NEXT_PUBLIC_` for client-side access):

| Variable                       | Description                                 |
| ------------------------------ | ------------------------------------------- |
| `NEXT_PUBLIC_API_BASE_URL`     | Backend API URL (e.g. `https://api.satta.market`) |
| `NEXT_PUBLIC_WS_BASE_URL`     | WebSocket URL (e.g. `wss://ws.satta.market`)     |
| `NEXT_PUBLIC_SITE_URL`        | Canonical site URL                          |
| `NEXT_PUBLIC_SUPABASE_URL`    | Supabase project URL                        |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anonymous/public key             |
| `NEXT_PUBLIC_VAPID_PUBLIC_KEY` | VAPID key for web push notifications        |

### Realtime Services (`services/realtime`)

| Variable            | Default                           | Description                    |
| ------------------- | --------------------------------- | ------------------------------ |
| `RUST_LOG`          | `info`                            | Log level filter               |
| `REDIS_URL`         | `redis://localhost:6379/0`        | Redis connection               |
| `POSTGRES_URL`      | `postgres://beyul:change_me@...`  | Sync Postgres DSN (for sqlx)   |
| `WS_HOST`           | `0.0.0.0`                         | WS gateway bind host           |
| `WS_PORT`           | `9000`                            | WS gateway bind port           |
| `PRICE_FEED_PROVIDER` | `chainlink`                     | Price feed source              |
| `PRICE_FEED_SYMBOLS`  | `BTC-USD,ETH-USD`               | Comma-separated price symbols  |

---

## Database Setup

Satta uses PostgreSQL with Supabase for auth and Row-Level Security. Migrations are located in `supabase/migrations/` and must be applied in order.

### 1. Provision PostgreSQL

Use a managed service (Supabase, AWS RDS, Azure Database for PostgreSQL) or the local Docker Compose:

```bash
cd infra/docker
docker compose -f docker-compose.local.yml up -d postgres
```

### 2. Run Migrations

Apply all 15 migrations sequentially:

```bash
# Using psql against your production database
for f in supabase/migrations/*.sql; do
  echo "Applying $f ..."
  psql "$DATABASE_URL" -f "$f"
done
```

Or with the Supabase CLI if using a hosted Supabase project:

```bash
supabase db push
```

**Migration inventory** (001–015):

| #   | File                               | Purpose                            |
| --- | ---------------------------------- | ---------------------------------- |
| 001 | `extensions_and_types.sql`         | pgcrypto, custom enums             |
| 002 | `core_identity_and_social.sql`     | Users, profiles, communities       |
| 003 | `markets_and_trading.sql`          | Markets, positions, orders         |
| 004 | `resolution_and_disputes.sql`      | Oracle assertions, disputes        |
| 005 | `ledger_and_payments.sql`          | Ledger entries, balances           |
| 006 | `seed_reference_data.sql`          | Default categories, fee tiers      |
| 007 | `rls_policies.sql`                 | Row-Level Security policies        |
| 008 | `market_image_url.sql`             | Market image URL column            |
| 009 | `market_request_image_url.sql`     | Market request image URL column    |
| 010 | `legal_acceptances.sql`            | Terms of service acceptance        |
| 011 | `notifications.sql`                | Push notification subscriptions    |
| 012 | `creator_reward_tiers.sql`         | Creator incentive tiers            |
| 013 | `social_follows.sql`               | Follow/unfollow relationships      |
| 014 | `deposit_withdrawals.sql`          | Deposit and withdrawal tracking    |
| 015 | `api_keys.sql`                     | API key management                 |

### 3. Verify

```bash
psql "$DATABASE_URL" -c "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;"
```

---

## Backend API Deployment

### Direct (uvicorn)

```bash
cd services/api
pip install -r requirements.txt   # or: pip install -e .

# Production launch
APP_ENV=production \
REPOSITORY_BACKEND=postgres \
POSTGRES_DSN="postgresql+asyncpg://user:pass@db-host:5432/beyul" \
REDIS_URL="redis://redis-host:6379/0" \
JWT_SECRET="<strong-random-secret>" \
ORACLE_CALLBACK_SECRET="<strong-random-secret>" \
ALLOW_DEV_AUTH=false \
  uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4 \
    --proxy-headers \
    --forwarded-allow-ips='*'
```

### Docker

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY services/api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY services/api/ .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--proxy-headers"]
```

Build and run:

```bash
docker build -t satta-api -f Dockerfile.api .
docker run -d --name satta-api \
  --env-file .env.production \
  -p 8000:8000 \
  satta-api
```

### Systemd (bare-metal)

```ini
[Unit]
Description=Satta API
After=network.target postgresql.service redis.service

[Service]
User=satta
Group=satta
WorkingDirectory=/opt/satta/services/api
EnvironmentFile=/opt/satta/.env.production
ExecStart=/opt/satta/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4 --proxy-headers
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

---

## Frontend Deployment

### Option A: Vercel (recommended)

1. Connect the repository to Vercel.
2. Set the **Root Directory** to `apps/web`.
3. Configure environment variables in the Vercel dashboard (all `NEXT_PUBLIC_*` variables).
4. Vercel auto-detects Next.js and handles builds and deployments.

### Option B: Self-hosted

```bash
cd apps/web
npm ci
npm run build
npm run start -- -p 3000
```

For Docker:

```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY apps/web/package*.json ./
RUN npm ci
COPY apps/web/ .
RUN npm run build

FROM node:20-alpine
WORKDIR /app
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
EXPOSE 3000
CMD ["node", "server.js"]
```

> Enable `output: "standalone"` in `next.config.mjs` for the standalone Docker build.

---

## Matching Engine

The matching engine is a Rust binary in `services/realtime/crates/matching-engine`.

### Build

```bash
cd services/realtime
cargo build --release --bin matching-engine
```

The binary is at `target/release/matching-engine`.

### Run

```bash
RUST_LOG=info \
REDIS_URL="redis://redis-host:6379/0" \
POSTGRES_URL="postgres://user:pass@db-host:5432/beyul" \
  ./target/release/matching-engine
```

### Redis Requirements

The matching engine requires Redis 7+ with:

- **Streams** for the order queue (`engine.orders.incoming`)
- **Pub/sub channels** for trade events, order events, and order-book snapshots

Ensure Redis `maxmemory-policy` is set to `noeviction` to prevent data loss under memory pressure.

### Systemd

```ini
[Unit]
Description=Satta Matching Engine
After=network.target redis.service postgresql.service

[Service]
User=satta
Group=satta
EnvironmentFile=/opt/satta/.env.production
ExecStart=/opt/satta/bin/matching-engine
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

---

## WebSocket Gateway

The WebSocket gateway is a Rust binary in `services/realtime/crates/ws-gateway`.

### Build

```bash
cd services/realtime
cargo build --release --bin ws-gateway
```

### Run

```bash
RUST_LOG=info \
REDIS_URL="redis://redis-host:6379/0" \
WS_HOST=0.0.0.0 \
WS_PORT=9000 \
  ./target/release/ws-gateway
```

### Reverse Proxy Considerations

WebSocket connections require HTTP upgrade support. In your reverse proxy (Nginx, Caddy, Cloudflare):

```nginx
location /ws {
    proxy_pass http://127.0.0.1:9000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_read_timeout 86400s;
}
```

---

## Health Checks and Monitoring

### Endpoints

The API exposes three health endpoints (no `/api/v1` prefix, no rate limiting):

| Endpoint          | Purpose                    | Response                                    |
| ----------------- | -------------------------- | ------------------------------------------- |
| `GET /health`     | Liveness probe             | `{"status": "ok"}`                          |
| `GET /health/db`  | Database connectivity      | `{"status": "connected", ...}` or error     |
| `GET /health/system` | Full system status      | App config snapshot, uptime, DB status      |

### Recommended Monitoring Setup

**Liveness probe**: `GET /health` every 10s — restart the container/process if it fails 3 consecutive times.

**Readiness probe**: `GET /health/db` every 15s — remove from load balancer if the database is unreachable.

**Deep health**: `GET /health/system` every 60s — log and alert on anomalies.

### Structured Logging

The API uses Python's `logging` module. Configure JSON structured logging for production:

```bash
# In your startup script or env
LOG_FORMAT=json
LOG_LEVEL=INFO
```

Ship logs to your observability stack (Datadog, Grafana Loki, CloudWatch, etc.) via stdout capture.

### Key Metrics to Monitor

- **API**: Request latency (p50/p95/p99), error rate, active connections
- **Matching Engine**: Order queue depth, trade throughput, processing latency
- **WebSocket Gateway**: Active connections, message throughput
- **Database**: Connection pool utilization, query latency, replication lag
- **Redis**: Memory usage, pub/sub subscriber count, queue length

---

## TLS, DNS, and Reverse Proxy

### Cloudflare Setup (recommended)

1. **DNS**: Point your domain to the server IP (or load balancer) with Cloudflare proxying enabled (orange cloud).
2. **SSL/TLS**: Set encryption mode to **Full (strict)**. Install a Cloudflare Origin Certificate on your server.
3. **Subdomains**:
   - `satta.market` → Next.js frontend (or Vercel CNAME)
   - `api.satta.market` → FastAPI backend
   - `ws.satta.market` → WebSocket gateway
4. **WebSockets**: Enable WebSocket support in Cloudflare dashboard (enabled by default on most plans).
5. **Security**: Enable Bot Fight Mode, configure WAF rules, set rate limiting on `/api/v1/` endpoints.

### Nginx Configuration

```nginx
upstream api {
    server 127.0.0.1:8000;
}

upstream ws_gateway {
    server 127.0.0.1:9000;
}

server {
    listen 443 ssl http2;
    server_name api.satta.market;

    ssl_certificate     /etc/ssl/origin.pem;
    ssl_certificate_key /etc/ssl/origin-key.pem;

    location / {
        proxy_pass http://api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

server {
    listen 443 ssl http2;
    server_name ws.satta.market;

    ssl_certificate     /etc/ssl/origin.pem;
    ssl_certificate_key /etc/ssl/origin-key.pem;

    location / {
        proxy_pass http://ws_gateway;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400s;
    }
}
```

---

## CI/CD

The repository uses GitHub Actions (`.github/workflows/ci.yml`) with the following jobs:

| Job                  | Trigger              | What it does                              |
| -------------------- | -------------------- | ----------------------------------------- |
| `lint-and-type-check`| Push/PR to `main`    | `npm ci`, `tsc --noEmit`, `next lint`     |
| `python-lint`        | Push/PR to `main`    | Ruff linting on `services/api/app/`       |
| `playwright-smoke`   | After lint passes    | Playwright E2E tests with trace upload    |
| `rust-check`         | Push/PR to `main`    | `cargo check --workspace`                 |

### Extending the Pipeline

To add deployment steps, create a separate workflow (e.g., `deploy.yml`) triggered on pushes to `main` that passes CI:

```yaml
on:
  workflow_run:
    workflows: ["CI"]
    types: [completed]
    branches: [main]
```

---

## Operational Runbook

### Startup Order

1. **PostgreSQL** — must be available before any service starts
2. **Redis** — must be available before the matching engine or API starts
3. **Matching Engine** — begins consuming the order queue
4. **WebSocket Gateway** — subscribes to Redis channels
5. **Backend API** — serves HTTP traffic
6. **Frontend** — can start independently once the API URL is known

### Shutdown Order

Reverse of startup. Drain the API first (stop accepting new requests), then shut down remaining services.

### Common Issues

| Symptom                           | Likely Cause                         | Fix                                        |
| --------------------------------- | ------------------------------------ | ------------------------------------------ |
| API refuses to start in prod      | Missing or default secrets           | Check `JWT_SECRET`, `ORACLE_CALLBACK_SECRET`, `POSTGRES_DSN` |
| `REPOSITORY_BACKEND must be postgres` | `APP_ENV=production` with `memory` backend | Set `REPOSITORY_BACKEND=postgres`      |
| WebSocket connections drop        | Proxy timeout too low                | Set `proxy_read_timeout 86400s` in Nginx   |
| Matching engine not processing    | Redis not reachable                  | Verify `REDIS_URL` and Redis health        |
| Migrations fail                   | Applied out of order                 | Apply sequentially: 001 through 015        |

### Backup and Recovery

- **Database**: Enable point-in-time recovery (PITR) on your PostgreSQL provider. Schedule daily logical backups with `pg_dump`.
- **Redis**: Enable AOF persistence (`appendonly yes`). Redis data is ephemeral by design in this architecture — the matching engine rebuilds state from PostgreSQL on restart.
- **Secrets**: Store all secrets in a vault (AWS Secrets Manager, HashiCorp Vault, or equivalent). Never commit `.env` files.
