# Domain Rules

This document captures the first-pass operating rules implied by the schema.

## Product defaults

- A market uses exactly one settlement rail: `custodial` or `onchain`.
- A market can exist without a community, but private-group markets should belong to a community.
- Multi-outcome markets are supported by schema, but binary markets should be the default product flow.
- Public markets should be treated as whitelisted-source only.
- Community/private-group markets can use the council path when no Tier 1 or Tier 2 source exists.

## Market lifecycle

1. User creates a `market_creation_request`.
2. Questionnaire answers are captured in `market_creation_request_answers`.
3. Market stays `draft` or `pending_review` until approved.
4. Once approved, a canonical `markets` row and its `market_outcomes` are created.
5. Market stays `pending_liquidity` until minimum conditions are met.
6. Market becomes `open` once liquidity and participant requirements are satisfied.
7. Market moves to `awaiting_resolution` after trading closes.
8. Market becomes `disputed`, `settled`, or `cancelled` depending on the resolution path.

## Recommended v1 constraints

- Require one rail per market. Do not mix custodial AUD and onchain USDC liquidity inside the same market.
- Require at least 2 outcomes, but keep the creation UI focused on binary markets first.
- Require `min_participants >= 2` for activation.
- Require creator seed funding before market activation if `min_seed_amount > 0`.
- Keep platform fee at `100` basis points by default and calculate creator fee separately.

## Resolution rules

- `oracle` markets should settle only from machine-resolvable feeds.
- `api` markets should allow automated fetch plus operator confirmation.
- `council` markets should require at least 3 resolver votes and a dispute window.
- Every final resolution should produce exactly one `market_resolutions` row.
- A market should not finalize funds release until the dispute window ends.

## Dispute rules

- Only markets with a posted resolution can be disputed.
- Disputes should require a fee to reduce spam.
- Dispute evidence should be append-only from the claimant side.
- Review outcome should be one of: upheld, dismissed, withdrawn.

## Social moderation rules

- Communities may require post approval.
- Communities may require market approval.
- Only moderators/admins/owners should approve posts or market requests for that community.
- Posts and markets should keep separate moderation queues even if they share the same community staff.

## Ledger rules

- User spendable balance should be derived from ledger entries, not a mutable balance column.
- Every deposit, refund, payout, fee, or dispute charge should create a `ledger_transactions` row.
- Every ledger transaction should balance to zero across its entries.
- `payment_intents` track provider state; `ledger_entries` track accounting truth.
