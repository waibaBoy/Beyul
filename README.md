# Beyul

Beyul is a monorepo for a prediction-market platform inspired by Polymarket, with a working local stack (Next.js, FastAPI, Postgres via Supabase migrations, optional in-memory API mode).

The repo is optimized around a split-stack architecture:

- Rust for low-latency matching, market state fanout, and price ingestion
- Python FastAPI for REST, auth, admin, and operational workflows
- Next.js for the user-facing web application
- PostgreSQL for durable market, order, trade, and user data
- Redis for cache, event fanout, and cross-service coordination
- Solidity on Polygon for settlement and escrow logic
- Chainlink for external settlement data
- AWS EC2 as the primary deployment target

## Monorepo layout

```text
.
|-- apps/
|   `-- web/                  # Next.js frontend
|-- contracts/
|   `-- polygon/              # Solidity contracts and deployment/test scaffold
|-- docs/
|   |-- architecture.md       # System design, implementation status, settlement & trust model
|   |-- domain-rules-parity.md # Maps domain rules to routes/UI (living doc)
|   |-- phase-execution-roadmap.md # Phase tracker for competitor-gap implementation
|   `-- competitive-notes-polymarket-kalshi.md # Feature backlog vs Polymarket / Kalshi (living)
|-- infra/
|   |-- aws/                  # EC2 deployment notes and infra placeholders
|   `-- docker/               # Local Postgres/Redis stack
|-- scripts/                  # Repo automation placeholders
|-- services/
|   |-- api/                  # FastAPI service for REST/auth/admin
|   `-- realtime/             # Rust workspace for engine/feed/ws
|-- specs/
|   |-- events/               # Redis/pub-sub and websocket event contracts
|   `-- openapi/              # REST surface planning
|-- .editorconfig
|-- .env.example
|-- .gitignore
|-- package.json
`-- pnpm-workspace.yaml
```

## Service boundaries

### `services/realtime`

Rust workspace split into:

- `matching-engine`: order book, matching, trade generation
- `price-feed`: external market data ingestion and normalization
- `ws-gateway`: websocket fanout for market updates and order status
- `shared`: shared domain types and service utilities

### `services/api`

FastAPI service responsible for:

- authentication and session issuance
- user/account/admin APIs
- market discovery and read APIs
- write-side orchestration for order submission
- persistence into PostgreSQL
- coordination with Redis and Rust services

### `apps/web`

Next.js App Router frontend for:

- market browsing
- portfolio and positions
- order entry
- admin/operator workflows

### `contracts/polygon`

Settlement and escrow contract scaffold for:

- market creation metadata anchoring
- escrow and payout flow
- oracle-authorized settlement

## Local development

Typical local workflow:

1. Start infra with `infra/docker/docker-compose.local.yml` (Postgres/Redis as needed).
2. Apply Supabase SQL migrations under `supabase/migrations` in order through `010_legal_acceptances.sql` (or run `scripts/supabase/010_legal_acceptances_standalone.sql` after `009` if you add compliance later), when using Postgres.
3. Run FastAPI from `services/api` (defaults use `REPOSITORY_BACKEND=memory` unless you point at Postgres).
4. Run Next.js from `apps/web`.
5. Optionally run the Rust workspace from `services/realtime` for matching-engine and websocket features.

Production-like deployments must set `APP_ENV` to `production` or `staging` only together with `REPOSITORY_BACKEND=postgres`, strong `JWT_SECRET`, real `POSTGRES_DSN`, `ALLOW_DEV_AUTH=false`, and a non-default `ORACLE_CALLBACK_SECRET` (validated at API startup).

## Environment files

- Web: configure via `apps/web` (see `apps/web/README.md` if present).
- API: root `.env` at repo root is loaded by `services/api` (`Settings` in `app/core/config.py`).
- Rust: `services/realtime/.env.example`
- Contracts: `contracts/polygon/.env.example`

## Next review points

The key architecture choices to review before implementation:

- whether order placement is synchronous through FastAPI or asynchronously queued into Rust
- whether the websocket gateway stays standalone or is folded into the API edge
- how much market state is stored in Redis versus reconstructed from PostgreSQL and engine events
- whether settlement is per-market, batched, or epoch-based onchain
