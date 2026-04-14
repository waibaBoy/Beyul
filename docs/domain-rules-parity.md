# Domain rules ↔ implementation parity

This maps `docs/domain-rules.md` to the current API routes, data model, and web UI. Use it to track product intent versus what ships today.

| Domain area | Rule (summary) | Current implementation | Gap / next step |
|-------------|----------------|------------------------|-----------------|
| Settlement rail | One rail per market: `custodial` or `onchain` | `markets` includes settlement metadata; custodial flows dominate local dev | Enforce rail at create/publish; block mixed-liquidity markets in API |
| Community scope | Public vs community-linked markets | Markets expose `community_slug` / `community_name`; discovery filters by category | Dedicated “private group” UX and council path still thin |
| Market lifecycle | draft → review → `pending_liquidity` → `open` → resolution | FastAPI status transitions; web detail workspace surfaces status-driven UI | Automate `min_participants` / seed gates in API, not only UI hints |
| Market requests | Questionnaire + review before canonical market | `market_creation_requests`, `image_url`, admin publish path | Full moderation queue UI vs single request detail |
| Resolution | Oracle / API / council semantics | Resolution state + oracle harness on market detail (admin) | Council voting, fee-backed disputes, append-only evidence hardening |
| Disputes | Fee, append-only claimant evidence | Dispute forms and evidence types in UI | Persist fee collection and immutable evidence chain in ledger |
| Ledger truth | Balances from ledger entries | Schema in migrations; API may still use simplified balance paths | Align portfolio/read models strictly with ledger derivation |
| Social moderation | Separate queues for posts vs markets | Communities and posts exist in schema | Wire moderator queues per `domain-rules` social section |
| On-chain settlement | Oracle-finalized payouts for `onchain` rail | Contracts + oracle services in repo; see architecture doc | Per-market docs: oracle choice, dispute windows, custodial vs on-chain in UI |

## Trust and settlement (narrative)

Technical trust boundaries (zero trust vs trust-minimized settlement, oracle assumptions, hybrid rails) are documented in **`docs/architecture.md`** under **Settlement and trust model**. User-facing language is summarized on the web at **`/about`**.

## Web routes (reference)

- `/` — Landing (market discovery, lazy-loaded card sparklines).
- `/about` — Product story, fees, creator rewards, settlement positioning (keep in sync with architecture doc).
- `/markets`, `/markets/[slug]` — Browse and trading shell, orders, resolution tools.
- `/market-requests`, `/market-requests/[id]` — Creation pipeline and image upload.
- `/portfolio`, `/communities/*` — User positions and community surfaces.

## API surface (reference)

- `/api/v1/markets`, `/api/v1/markets/{slug}/trading-shell`, `history`, `holders`, `resolution`, `orders/me`
- `/api/v1/auth/me`, `/api/v1/portfolio/me`
- Market requests and admin publish endpoints under `/api/v1/market-requests` (see OpenAPI / route modules)

When adding a feature, update this table in the same PR so reviewers can see domain alignment.
