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

## Settlement and trust model

This section clarifies how “zero trust,” **on-chain settlement**, and **off-chain services** fit together so engineers, operators, and counsel share the same picture.

### Terminology

- **Zero trust (security)**: identity and access are always verified (sessions, RBAC, service auth). It does **not** mean “users never rely on any assumption about money.”
- **Trust-minimized settlement (product)**: for markets that use the **on-chain rail**, **final economic outcomes** (who gets paid, under which rules) are intended to be enforced by **smart contracts** and an **oracle** rather than by mutable rows in Postgres as the ultimate source of truth.

### What is authoritative on-chain

Where the **on-chain + oracle path** is active for a market:

- **Escrow, resolution, and claims** are governed by the **contract** and the **oracle model** (e.g. UMA-style assertions, Chainlink-backed reference data, or other configured providers—see `services/api` oracle services and `contracts/polygon`).
- Users should treat **on-chain state and emitted events** as the **final word** for that rail once a payout path is executed, subject to the **oracle and contract design** (upgradeability, admin keys, pausability, and economic security are part of that design).

### What remains off-chain (and why it still matters)

Even with on-chain settlement:

- **Next.js + FastAPI + Postgres + Rust engine** handle **UX, auth, discovery, order intake, matching, and operational state** before and until those actions are reflected on-chain (batches, intents, bridging, or whatever integration you ship).
- That stack must be **correct and available** for a good experience; it is simply **not the same layer** as **final on-chain settlement** for rails that are fully non-custodial on-chain.

### Oracle trust boundary

An **oracle** is always a **design choice**: economic games (e.g. UMA), feed networks, or privileged attestors each carry **assumptions** about liveness, data quality, and governance. Document the **specific** oracle and dispute flow **per market type** in runbooks and user-facing copy (`/about`, terms) as implementations harden.

### Hybrid rails

The schema and domain rules allow **custodial** and **on-chain** rails. If some markets are **custodial** and others are **oracle-settled on-chain**, **say so explicitly** in product and legal text: users should never have to infer which trust model applies.

### Regulatory and custody reality

On-chain settlement **does not automatically** satisfy licensing, marketing, KYC/AML, or consumer-law obligations in every jurisdiction. Architecture docs describe **technical** trust; **legal** review is still required for **where** and **how** the product is offered.

### User-facing summary

A shorter, marketing-friendly version of this story lives at **`/about`** in the web app (`apps/web/src/app/about/page.tsx`). Keep **architecture.md** (technical) and **About** (reader-friendly) aligned when the settlement rail or oracle strategy changes.

For **feature gaps vs Polymarket / Kalshi** (checklists and what not to copy blindly), see `docs/competitive-notes-polymarket-kalshi.md`.

## Suggested implementation order

1. Lock the event model in `specs/events/README.md`
2. Lock the REST surface in `specs/openapi/README.md`
3. Build FastAPI auth and market metadata APIs
4. Build Rust engine with Redis event emission
5. Add websocket gateway
6. Add contract lifecycle and settlement path

## Open design decisions

- source of truth for balances **per rail** (custodial vs on-chain) and the exact handoff from off-chain matching to on-chain finality
- exact contract between FastAPI order intake and Rust order execution
- whether price feed data is only for display or also used for resolution candidate generation
- final model for admin approvals and market dispute handling (including how disputes interact with oracle timelines)

## Implementation status

- **Web (`apps/web`)**: App Router pages for markets, portfolio, communities, market requests, auth; market detail consolidates shell, holders, resolution, and signed-in `me` / portfolio / orders in one bootstrap pass; landing card sparklines load on visibility (Intersection Observer) to limit `/history` traffic.
- **API (`services/api`)**: FastAPI with optional in-memory repository for local dev; `Settings` rejects unsafe defaults when `APP_ENV` is `production`, `prod`, or `staging` (Postgres backend, no dev auth, non-default JWT and DB credentials, dedicated oracle callback secret). Startup logs `app_env` and `repository_backend`.
- **Database**: Supabase migrations through `010_legal_acceptances.sql` (includes `009` market/request `image_url` and `010` signup compliance audit). Apply all migrations before pointing the API at Postgres.
- **Domain traceability**: See `docs/domain-rules-parity.md` for a concise map from domain rules to routes and known gaps.
