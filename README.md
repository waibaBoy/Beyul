# Beyul

Beyul is a monorepo for a prediction-market platform inspired by Polymarket/Kalshi-style market UX, with a working local stack for market creation, trading, resolution, community surfaces, and operator workflows.

The repo is optimized around a split-stack architecture:

- Rust for low-latency matching, market state fanout, and price ingestion
- Python FastAPI for REST, auth, admin, and operational workflows
- Next.js for the user-facing web application
- PostgreSQL for durable market, order, trade, and user data
- Redis for cache, event fanout, and cross-service coordination
- UMA Optimistic Oracle integration for trust-minimized settlement assertions, with mock/simulated/live modes
- External data sources such as Chainlink/Binance/reference APIs for market metadata, display data, and source evidence
- Solidity on Polygon as the settlement anchoring scaffold; full escrow and payout contracts are not production-complete yet
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
|-- scripts/                  # Repo automation and smoke-test helpers
|-- services/
|   |-- api/                  # FastAPI service for REST/auth/admin
|   `-- realtime/             # Rust workspace for engine/feed/ws
|-- specs/
|   |-- events/               # Redis/pub-sub and websocket event contracts
|   `-- openapi/              # REST surface planning
|-- .editorconfig
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
- user, account, admin, portfolio, and operator APIs
- market discovery, market detail, request intake, and resolution APIs
- write-side orchestration for order submission into the Rust matching path
- persistence into PostgreSQL
- coordination with Redis and Rust services
- oracle/dispute lifecycle orchestration, including mock and UMA-backed flows

### `apps/web`

Next.js App Router frontend for:

- market browsing
- portfolio and positions
- order entry
- market request intake and admin/operator workflows
- communities, profiles, creator tools, notifications, wallet, leaderboard, and ops surfaces

### `contracts/polygon`

Polygon contract scaffold for:

- market creation metadata anchoring
- oracle-authorized settlement metadata

Current status: `contracts/polygon/src/BeyulMarket.sol` is intentionally minimal. It does not yet implement production escrow, deposits, share accounting, payout claims, UMA callback enforcement, or user withdrawal flows. Treat FastAPI/Postgres/Rust as the active beta trading stack and the UMA integration as the active oracle boundary until the contract layer is expanded and audited.

## Settlement direction

The current settlement direction is **UMA optimistic oracle first**:

- `ORACLE_PROVIDER=mock` is the default local path.
- `ORACLE_PROVIDER=uma` with `ORACLE_EXECUTION_MODE=simulated` exercises the UMA metadata path without broadcasting transactions.
- `ORACLE_PROVIDER=uma` with `ORACLE_EXECUTION_MODE=live` signs and submits UMA Optimistic Oracle transactions after signer/RPC/token readiness checks pass.

Chainlink and other APIs are treated as reference sources for market terms, source URLs, display prices, or evidence. They are not currently the primary on-chain settlement mechanism.

## Local development

Typical local workflow:

1. Start infra with `infra/docker/docker-compose.local.yml` (Postgres/Redis as needed).
2. Apply all Supabase SQL migrations under `supabase/migrations` in order when using Postgres.
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

The key architecture choices to review before beta:

- whether beta is explicitly custodial/off-chain ledger first, on-chain settlement first, or hybrid per market rail
- how the expanded Polygon contracts will handle escrow, share accounting, payout claims, and oracle callbacks
- how UMA live assertions are funded, approved, reconciled, and monitored in production
- whether order placement always goes through the Rust matching queue in deployed environments
- how much market state is stored in Redis versus reconstructed from PostgreSQL and engine events
- whether the websocket gateway stays standalone or is folded into the API edge
