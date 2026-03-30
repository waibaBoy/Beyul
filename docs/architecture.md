# Architecture

## Goal

Build a prediction market platform with low-latency matching, durable trade state, clean service boundaries, and an onchain settlement layer.

## System map

```text
Next.js Web
    |
    | HTTPS / WebSocket
    v
FastAPI REST/Auth/Admin ---- PostgreSQL
    |                           ^
    | Redis commands/events     |
    v                           |
Rust Matching Engine ----------/
    |
    | market/trade events
    v
Rust WebSocket Gateway -----> Clients
    ^
    |
Rust Price Feed <----- External market data / reference prices

Settlement path:
FastAPI Admin -> Polygon Contract -> Chainlink-backed settlement data -> Payout state
```

## Responsibilities

### Next.js

- user onboarding and sign-in UX
- market listing, market detail, and portfolio views
- order ticket submission to FastAPI
- realtime subscriptions through the websocket gateway

### FastAPI

- auth, session, RBAC, and admin actions
- market metadata CRUD
- order validation before engine submission
- write persistence into PostgreSQL
- operator flows for pauses, market resolution prep, and incident tooling

### Rust matching engine

- accept validated order intents
- maintain in-memory books per market
- generate fills and order state transitions
- publish canonical execution events to Redis

### Rust price feed

- ingest external prices
- normalize symbols and time series
- publish price ticks and settlement candidates

### Rust websocket gateway

- maintain client subscriptions
- project Redis/engine events into client-friendly streams
- handle backpressure and per-connection auth

### PostgreSQL

- users, markets, orders, trades, balances, positions
- admin audit trail
- settlement history and reconciliation data

### Redis

- service-to-service pub/sub
- short-lived caches
- rate-limit and session support if needed
- ephemeral market state snapshots

### Solidity + Chainlink

- escrow, market resolution, and claim flow
- oracle-authorized settlement trigger
- final payout state recorded on Polygon

## Suggested implementation order

1. Lock the event model in `specs/events/README.md`
2. Lock the REST surface in `specs/openapi/README.md`
3. Build FastAPI auth and market metadata APIs
4. Build Rust engine with Redis event emission
5. Add websocket gateway
6. Add contract lifecycle and settlement path

## Open design decisions

- source of truth for balances before onchain settlement
- exact contract between FastAPI order intake and Rust order execution
- whether price feed data is only for display or also used for resolution candidate generation
- final model for admin approvals and market dispute handling
