# Beyul

Beyul is a monorepo scaffold for a prediction-market platform inspired by Polymarket.

This scaffold is optimized around a split-stack architecture:

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
|   `-- architecture.md       # High-level system design
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

This scaffold currently sets up architecture and starter files only.

Planned local workflow:

1. Start infra with `infra/docker/docker-compose.local.yml`
2. Run the Rust workspace from `services/realtime`
3. Run FastAPI from `services/api`
4. Run Next.js from `apps/web`

## Environment files

- Root shared defaults: `.env.example`
- Web: `apps/web/.env.example`
- API: `services/api/.env.example`
- Rust: `services/realtime/.env.example`
- Contracts: `contracts/polygon/.env.example`

## Next review points

The key architecture choices to review before implementation:

- whether order placement is synchronous through FastAPI or asynchronously queued into Rust
- whether the websocket gateway stays standalone or is folded into the API edge
- how much market state is stored in Redis versus reconstructed from PostgreSQL and engine events
- whether settlement is per-market, batched, or epoch-based onchain
