# Project Tree

```text
Beyul/
|-- .editorconfig
|-- .env.example
|-- .gitignore
|-- README.md
|-- package.json
|-- pnpm-workspace.yaml
|-- PROJECT_TREE.md
|-- apps/
|   `-- web/
|       |-- .env.example
|       |-- README.md
|       |-- next-env.d.ts
|       |-- next.config.mjs
|       |-- package.json
|       |-- public/
|       |-- src/
|       |   `-- app/
|       |       |-- globals.css
|       |       |-- layout.tsx
|       |       `-- page.tsx
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
|   |-- database-schema.md
|   |-- domain-rules.md
|   |-- supabase-project-setup.md
|   `-- rls-policy-plan.md
|-- infra/
|   |-- aws/
|   |   `-- README.md
|   `-- docker/
|       `-- docker-compose.local.yml
|-- scripts/
|   `-- README.md
|-- services/
|   |-- api/
|   |   |-- .env.example
|   |   |-- README.md
|   |   |-- app/
|   |   |   |-- __init__.py
|   |   |   |-- api/
|   |   |   |   |-- __init__.py
|   |   |   |   `-- routes/
|   |   |   |       |-- __init__.py
|   |   |   |       `-- health.py
|   |   |   |-- core/
|   |   |   |   |-- __init__.py
|   |   |   |   `-- config.py
|   |   |   |-- db/
|   |   |   |   `-- __init__.py
|   |   |   |-- main.py
|   |   |   |-- models/
|   |   |   |   `-- __init__.py
|   |   |   |-- schemas/
|   |   |   |   `-- __init__.py
|   |   |   `-- services/
|   |   |       `-- __init__.py
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
    |   `-- 007_rls_policies.sql
    |-- schema.sql
    `-- seed.sql
```

## Notes

- `apps/web` is the Next.js frontend scaffold.
- `services/api` is the FastAPI service boundary.
- `services/realtime` is the Rust workspace for engine, feed, and websocket services.
- `contracts/polygon` is the Polygon/Foundry contract scaffold.
- `supabase` contains the first-pass PostgreSQL schema and seed data.
- `docs/domain-rules.md`, `docs/rls-policy-plan.md`, and `docs/supabase-project-setup.md` define product defaults, access control, and project connection prep.
