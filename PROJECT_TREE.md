# Project Tree

```text
Beyul/
|-- .editorconfig
|-- .gitignore
|-- README.md
|-- package.json
|-- pnpm-workspace.yaml
|-- PROJECT_TREE.md
|-- apps/
|   `-- web/
|       |-- README.md
|       |-- next-env.d.ts
|       |-- next.config.mjs
|       |-- package.json
|       |-- public/
|       |-- src/
|       |   |-- app/                 # App Router: /, /markets, /portfolio, /auth/*, /communities, /market-requests, /admin
|       |   |-- components/          # app/* workspaces, auth/*
|       |   |-- lib/                 # api client, markets, supabase, realtime
|       |   `-- middleware.ts
|       `-- tsconfig.json
|-- contracts/
|   `-- polygon/
|       |-- .env.example
|       |-- README.md
|       |-- foundry.toml
|       |-- script/
|       |   `-- Deploy.s.sol
|       |-- src/
|       |   `-- BeyulMarket.sol
|       `-- test/
|           `-- BeyulMarket.t.sol
|-- docs/
|   |-- architecture.md
|   |-- competitive-notes-polymarket-kalshi.md
|   |-- database-schema.md
|   |-- domain-rules.md
|   |-- domain-rules-parity.md
|   |-- phase-execution-roadmap.md
|   |-- supabase-project-setup.md
|   `-- rls-policy-plan.md
|-- infra/
|   |-- aws/
|   |   `-- README.md
|   `-- docker/
|       `-- docker-compose.local.yml
|-- scripts/
|   |-- README.md
|   |-- scheduler/
|   |   `-- rolling-settlement-loop.ps1
|   `-- supabase/
|       |-- README.md
|       |-- 010_legal_acceptances_standalone.sql
|       |-- 011_notifications_standalone.sql
|       `-- 012_creator_reward_tiers_standalone.sql
|-- services/
|   |-- api/
|   |   |-- README.md
|   |   |-- app/
|   |   |   |-- __init__.py
|   |   |   |-- api/            # router, routes (auth, markets, portfolio, communities, posts, market_requests, admin, health)
|   |   |   |-- core/           # config (env + production validators), container, slug, exceptions
|   |   |   |-- db/             # SQLAlchemy session, tables
|   |   |   |-- main.py
|   |   |   |-- models/
|   |   |   |-- repositories/   # memory + postgres
|   |   |   |-- schemas/
|   |   |   `-- services/
|   |   |-- pyproject.toml
|   |   `-- tests/
|   |       |-- __init__.py
|   |       `-- test_health.py
|   `-- realtime/
|       |-- .env.example
|       |-- Cargo.toml
|       |-- README.md
|       `-- crates/
|           |-- matching-engine/
|           |   |-- Cargo.toml
|           |   `-- src/
|           |       `-- main.rs
|           |-- price-feed/
|           |   |-- Cargo.toml
|           |   `-- src/
|           |       `-- main.rs
|           |-- shared/
|           |   |-- Cargo.toml
|           |   `-- src/
|           |       `-- lib.rs
|           `-- ws-gateway/
|               |-- Cargo.toml
|               `-- src/
|                   `-- main.rs
|-- specs/
|   |-- events/
|   |   `-- README.md
|   `-- openapi/
|       |-- README.md
|       `-- route-map.md
`-- supabase/
    |-- .env.example
    |-- README.md
    |-- migrations/
    |   |-- 001_extensions_and_types.sql
    |   |-- 002_core_identity_and_social.sql
    |   |-- 003_markets_and_trading.sql
    |   |-- 004_resolution_and_disputes.sql
    |   |-- 005_ledger_and_payments.sql
    |   |-- 006_seed_reference_data.sql
    |   |-- 007_rls_policies.sql
    |   |-- 008_market_image_url.sql
    |   |-- 009_market_request_image_url.sql
    |   |-- 010_legal_acceptances.sql
    |   |-- 011_notifications.sql
    |   `-- 012_creator_reward_tiers.sql
    |-- schema.sql
    `-- seed.sql
```

## Notes

- `apps/web` is the Next.js App Router frontend (markets, portfolio, auth, communities, market requests).
- `services/api` is FastAPI with pluggable repositories (`memory` for local, `postgres` for real data); set `APP_ENV` to `production`/`staging` only with hardened env (see `app/core/config.py`).
- `services/realtime` is the Rust workspace for engine, feed, and websocket services.
- `contracts/polygon` is the Polygon/Foundry contract scaffold.
- `supabase` holds ordered migrations (`001`–`012`); apply through `012` for `creator_reward_tiers` and prior schema before running the API against Postgres.
- `docs/domain-rules.md` and `docs/domain-rules-parity.md` tie product rules to the current surface area; `docs/rls-policy-plan.md` and `docs/supabase-project-setup.md` cover access control and project setup.
