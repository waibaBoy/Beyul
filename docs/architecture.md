# Architecture

## Goal

Build a prediction market platform with low-latency matching, durable trade state, clean service boundaries, and a trust-minimized settlement path that can graduate from beta orchestration to audited on-chain payout enforcement.

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

Current settlement path:
FastAPI/Admin/Automation -> Oracle Service -> UMA Optimistic Oracle or mock provider -> Resolution state

Reference data path:
External data sources such as Chainlink, Binance, and official URLs -> market metadata, source evidence, and user-facing contract details

Future on-chain payout path:
FastAPI/Rust execution state -> Polygon contracts -> escrow, payout claims, and oracle-authorized finality
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

### Solidity + Oracle adapters

- current Solidity scaffold anchors market metadata and oracle-authorized settlement status
- current API oracle layer supports mock and UMA optimistic oracle modes
- Chainlink and other data providers are reference/evidence sources, not the primary settlement rail today
- future Solidity expansion must add escrow, share accounting, payout claims, callback enforcement, and audit-ready access controls

## Settlement and trust model

This section clarifies how “zero trust,” **on-chain settlement**, and **off-chain services** fit together so engineers, operators, and counsel share the same picture.

### Terminology

- **Zero trust (security)**: identity and access are always verified (sessions, RBAC, service auth). It does **not** mean “users never rely on any assumption about money.”
- **Trust-minimized settlement (product)**: for markets that use the **on-chain rail**, **final economic outcomes** (who gets paid, under which rules) are intended to be enforced by **smart contracts** and an **oracle** rather than by mutable rows in Postgres as the ultimate source of truth.

### What is authoritative on-chain

Where the **on-chain + oracle path** is active for a market:

- **Escrow, resolution, and claims** are intended to be governed by the **contract** and the **oracle model** once the on-chain rail is fully implemented. Today, the API implements the active oracle lifecycle and the Solidity contract is a scaffold.
- Users should treat **on-chain state and emitted events** as the **final word** for that rail once a payout path is executed, subject to the **oracle and contract design** (upgradeability, admin keys, pausability, and economic security are part of that design).

### What remains off-chain (and why it still matters)

Even with on-chain settlement:

- **Next.js + FastAPI + Postgres + Rust engine** handle **UX, auth, discovery, order intake, matching, and operational state** before and until those actions are reflected on-chain (batches, intents, bridging, or whatever integration you ship).
- That stack must be **correct and available** for a good experience; it is simply **not the same layer** as **final on-chain settlement** for rails that are fully non-custodial on-chain.

### Oracle trust boundary

An **oracle** is always a **design choice**: economic games such as UMA, feed networks such as Chainlink, APIs such as Binance, or privileged attestors each carry assumptions about liveness, data quality, and governance. The current beta direction is UMA Optimistic Oracle for settlement assertions, with Chainlink/Binance/official URLs used as reference sources or evidence depending on the market. Document the specific oracle and dispute flow per market type in runbooks and user-facing copy (`/about`, terms) as implementations harden.

### Contract status

`contracts/polygon/src/BeyulMarket.sol` is not a production settlement contract. It currently supports owner-created market records and oracle-authorized settlement metadata only. It does not implement:

- escrow or deposits
- share minting/burning/accounting
- payout claims
- fee distribution
- UMA callback validation
- withdrawal safety
- upgrade, pause, and admin-key governance reviews

Do not present the current Polygon contract as production-ready, trustless payout infrastructure until those pieces are implemented, tested, and audited.

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
7. Expand Polygon contracts from metadata scaffold into audited escrow/payout contracts

## Open design decisions

- source of truth for balances **per rail** (custodial vs on-chain) and the exact handoff from off-chain matching to on-chain finality
- exact contract between FastAPI order intake and Rust order execution
- whether price feed data is only for display or also used for resolution candidate generation
- final model for admin approvals and market dispute handling (including how disputes interact with oracle timelines)
- production path for UMA signer funding, bond token approval, assertion submission, dispute windows, and reconciliation
- scope and audit path for escrow/payout smart contracts

## Implementation status

- **Web (`apps/web`)**: App Router pages for landing, markets, market detail/trading, portfolio, communities, market requests, admin review, auth, profile, leaderboard, creators, wallet, ops, legal, and API keys.
- **API (`services/api`)**: FastAPI with optional in-memory repository for local dev; Postgres repository for durable mode; route groups for auth, markets, market requests, admin, portfolio, liquidity, advanced orders, notifications, push, transfers, API keys, social, creators, profiles, and posts. `Settings` rejects unsafe defaults when `APP_ENV` is `production`, `prod`, or `staging`.
- **Oracle**: Mock and UMA providers exist. UMA supports simulated and live execution modes, readiness checks, approval helpers, assertion metadata, transaction submission, and reconciliation fields. Live use still requires funded signer, token balance, token allowance, and network-specific operational validation.
- **Contracts**: Polygon contract is a scaffold only. It is not yet the final escrow/payout rail.
- **Database**: Apply all migrations under `supabase/migrations` before pointing the API at Postgres.
- **Domain traceability**: See `docs/domain-rules-parity.md` for a concise map from domain rules to routes and known gaps.
