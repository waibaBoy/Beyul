# Database Schema

This document defines the first-pass PostgreSQL schema for Beyul on Supabase.

The schema is designed to support four product surfaces at once:

- identity and user profiles
- social communities/pages with moderated posting
- market creation, trading, resolution, and disputes
- dual settlement rails for custodial AUD and onchain USDC

## Design principles

### 1. Separate social from trading

Communities and posts can exist without markets. Markets can optionally belong to a community.

### 2. Keep settlement source control explicit

Markets cannot rely on arbitrary free-text sources. The system records settlement source type, provider, and the exact reference used at creation time.

### 3. Preserve money movement with a ledger

Custodial balances, fees, refunds, and payout movements should be auditable. The schema uses ledger accounts, transactions, and entries rather than only storing derived balances.

### 4. Allow multiple resolution modes

The same market model supports:

- fully automatic oracle/API settlement
- semi-automatic operator-confirmed API settlement
- multisig/community-verified settlement with dispute windows

## Core domains

- `profiles` and `user_wallets` for identity
- `communities`, `community_members`, and `posts` for the social layer
- `market_creation_requests` and `market_creation_request_answers` for intake/questionnaires
- `markets`, `market_outcomes`, `orders`, `trades`, and `positions` for trading
- `settlement_sources`, `market_resolution_candidates`, `market_resolution_votes`, `market_resolutions`, `disputes`, and `dispute_evidence` for resolution
- `assets`, `ledger_accounts`, `ledger_transactions`, `ledger_entries`, and `payment_intents` for money movement

## Important decisions still open

- whether a single market can support both custodial and onchain participation at the same time
- whether positions are purely derived from trades or persisted as a write-through cache
- how much market activation should be enforced in database constraints versus service logic
- whether community posts and markets share the same moderation workflow or separate queues

## Files

- Migration source of truth: `supabase/migrations/`
- Consolidated schema snapshot: `supabase/schema.sql`
- Consolidated seed snapshot: `supabase/seed.sql`
- Domain rules: `docs/domain-rules.md`
- RLS plan: `docs/rls-policy-plan.md`
