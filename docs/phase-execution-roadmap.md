# Phase execution roadmap (Polymarket/Kalshi gap closure)

This turns the gap list into an implementation tracker. Keep statuses honest and update in each PR.

Legend: `todo` | `in_progress` | `beta` | `done`

`done` means implemented and validated enough to treat as complete for the current release target. `beta` means the feature exists, but still needs production hardening, operational validation, security review, or contract/audit work before it should be considered public real-money infrastructure.

## Phase 1 (foundations)

| Item | Status | Notes |
|------|--------|-------|
| Liquidity engine + incentives | done | Fee calculation service (maker 0% / taker 2%), depth KPI service (spread, book depth, imbalance), AMM inventory service with constant-product quoting. Rust matching engine computes fees from market config. |
| Deterministic settlement pipeline | done | Rolling up/down admin runner, settlement queue, automation runner, and PowerShell scheduler script. |
| Trading reliability/performance | done | Market-detail bootstrap endpoint; frontend consolidated to single fetch. |

## Phase 2 (retention + creator loop)

| Item | Status | Notes |
|------|--------|-------|
| Watchlists / alerts / notifications | done | Notification system: DB table, service + emitter, API endpoints, event hooks, frontend bell with dropdown. |
| Creator tooling + reward transparency | done | 6-tier reward model (Starter→Diamond), API + frontend dashboard, leaderboard. |
| Market quality controls | done | Duplicate detection (trigram similarity), anti-spam, content linting, moderation SLA reporting. |

## Phase 3 (pro polish + scale)

| Item | Status | Notes |
|------|--------|-------|
| Advanced charting + analytics | done | Interactive chart with crosshair, OHLC tooltip, drag-to-zoom, Y/X axes. |
| Portfolio/reporting depth | done | Expandable position rows with trade drilldown, fee attribution, CSV export. |
| Mobile-first execution | done | Touch chart, responsive tables, tighter mobile breakpoints. |
| Operations/compliance hardening | done | System status endpoint, jurisdiction gating middleware, incident runbook, ops dashboard. |

## Phase 4 (competitive parity)

| Item | Status | Notes |
|------|--------|-------|
| Social features | done | Trading profiles (`/profile/{username}`), follow/unfollow system, follower/following lists, trading stats view. DB migration `013_social_follows.sql`. |
| Leaderboards + gamification | done | Global PnL leaderboard at `/leaderboard` ranked by realized PnL with medal ranks. |
| Advanced order types | done | Conditional order service: stop-loss, take-profit, trailing stop. In-memory trigger engine, API at `/orders/conditional`. |
| On-chain settlement | beta | UMA oracle live mode with `LiveOracleProvider` (Web3 tx construction, gas estimation, signing), readiness checks, approval helper, and simulated mode. Polygon escrow/payout contracts are still scaffold-only and require implementation/audit before real-money finality. |
| Deposit/withdrawal flows | beta | Transfer request system with `transfer_requests` table, deposit/withdrawal API, fee calculation (0.5% on withdrawals). Migration `014_deposit_withdrawals.sql`. Requires custody/payment/on-chain settlement hardening before public real-money beta. |
| Push notifications | done | Service worker (`sw.js`), push subscription API (`/push/subscribe`, `/push/unsubscribe`), broadcast capability. |
| Multi-outcome markets | done | Custom outcome support in market requests, N-outcome publication in postgres repository, frontend multi-outcome form. |
| API keys / programmatic trading | done | API key system: `sk_live_*` format, SHA-256 hashed storage, create/list/revoke endpoints. Migration `015_api_keys.sql`. |

## Current backend additions (all phases)

### Core trading
- `POST /api/v1/liquidity/fee-preview` — fee preview calculator
- `GET /api/v1/liquidity/depth/{market_id}/{outcome_id}` — depth snapshot
- `GET /api/v1/liquidity/depth/{market_id}` — market depth report
- `GET /api/v1/liquidity/amm/status` — AMM status (admin)

### Social
- `GET /api/v1/social/profile/{username}` — public trading profile
- `POST /api/v1/social/follow` — follow user
- `POST /api/v1/social/unfollow` — unfollow user
- `GET /api/v1/social/followers/{username}` — follower list
- `GET /api/v1/social/following/{username}` — following list
- `GET /api/v1/social/leaderboard` — global PnL leaderboard

### Advanced orders
- `POST /api/v1/orders/conditional` — create conditional order
- `GET /api/v1/orders/conditional` — list conditional orders
- `DELETE /api/v1/orders/conditional/{order_id}` — cancel conditional order

### Transfers
- `POST /api/v1/transfers/deposit` — create deposit request
- `POST /api/v1/transfers/withdrawal` — create withdrawal request
- `GET /api/v1/transfers/me` — list user transfers

### Push notifications
- `POST /api/v1/push/subscribe` — register push subscription
- `POST /api/v1/push/unsubscribe` — remove subscription
- `GET /api/v1/push/stats` — subscription stats (admin)

### API keys
- `POST /api/v1/api-keys` — create API key
- `GET /api/v1/api-keys` — list keys
- `DELETE /api/v1/api-keys/{key_id}` — revoke key

### Existing endpoints (phases 1-3)
- `POST /api/v1/admin/rolling/up-down/run` — rolling market cycle
- `GET /api/v1/admin/settlement/queue` — settlement queue
- `POST /api/v1/admin/settlement/run` — settlement automation
- `GET /api/v1/notifications` — user notifications
- `GET /api/v1/notifications/unread-count` — unread count
- `POST /api/v1/notifications/mark-read` — mark read
- `GET /api/v1/creators/tiers` — reward tiers
- `GET /api/v1/creators/me/stats` — creator stats
- `GET /api/v1/creators/leaderboard` — creator leaderboard
- `POST /api/v1/market-requests/quality-check` — quality preview
- `GET /api/v1/admin/moderation/sla` — moderation SLA
- `GET /api/v1/portfolio/me/export.csv` — portfolio CSV
- `GET /health/system` — system status

## Database migrations

| # | File | Purpose |
|---|------|---------|
| 001 | `001_extensions_and_types.sql` | Core extensions and enums |
| 002 | `002_core_identity_and_social.sql` | Identity, profile, and social foundations |
| 003 | `003_markets_and_trading.sql` | Markets, outcomes, orders, trades, positions |
| 004 | `004_resolution_and_disputes.sql` | Resolution, disputes, evidence |
| 005 | `005_ledger_and_payments.sql` | Ledger and payment primitives |
| 006 | `006_seed_reference_data.sql` | Seed communities/reference data |
| 007 | `007_rls_policies.sql` | Row-level security policies |
| 008 | `008_market_image_url.sql` | Image URL on markets |
| 009 | `009_market_request_image_url.sql` | Image URL on requests |
| 010 | `010_legal_acceptances.sql` | Signup compliance |
| 011 | `011_notifications.sql` | Notifications table |
| 012 | `012_creator_reward_tiers.sql` | Creator tiers + stats view |
| 013 | `013_social_follows.sql` | Follow relationships + trading stats view |
| 014 | `014_deposit_withdrawals.sql` | Transfer requests |
| 015 | `015_api_keys.sql` | API key storage |
| 016 | `016_performance_indexes.sql` | Query performance indexes |

## Frontend pages

| Route | Purpose |
|-------|---------|
| `/` | Landing page |
| `/about` | Product info, fee structure |
| `/markets` | Market discovery |
| `/markets/[slug]` | Market detail + trading |
| `/portfolio` | Portfolio + PnL |
| `/creators` | Creator dashboard |
| `/leaderboard` | Global PnL leaderboard |
| `/profile/[username]` | Public trading profile |
| `/ops` | Operations dashboard |
| `/market-requests` | Propose a market |
| `/communities` | Community hub |
| `/auth/sign-up` | Signup with compliance |
| `/legal/terms` | Terms of Service |
| `/legal/privacy` | Privacy Policy |
