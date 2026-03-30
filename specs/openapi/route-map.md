# FastAPI Route Map

This route map turns the current schema into a first-pass REST surface for the API service.

## Auth

- `POST /auth/signup`
- `POST /auth/login`
- `POST /auth/logout`
- `POST /auth/refresh`
- `GET /auth/me`

Purpose:
- issue sessions
- hydrate current user profile
- bridge Supabase Auth with backend session checks where needed

## Profiles

- `GET /profiles/{username}`
- `PATCH /profiles/me`
- `GET /profiles/me/wallets`
- `POST /profiles/me/wallets`
- `PATCH /profiles/me/wallets/{wallet_id}`
- `DELETE /profiles/me/wallets/{wallet_id}`

Backed by:
- `profiles`
- `user_wallets`

## Communities

- `GET /communities`
- `POST /communities`
- `GET /communities/{community_slug}`
- `PATCH /communities/{community_slug}`
- `GET /communities/{community_slug}/members`
- `POST /communities/{community_slug}/members`
- `PATCH /communities/{community_slug}/members/{member_id}`
- `DELETE /communities/{community_slug}/members/{member_id}`

Backed by:
- `communities`
- `community_members`

## Posts

- `GET /communities/{community_slug}/posts`
- `POST /communities/{community_slug}/posts`
- `GET /posts/{post_id}`
- `PATCH /posts/{post_id}`
- `POST /posts/{post_id}/submit`
- `POST /posts/{post_id}/approve`
- `POST /posts/{post_id}/reject`

Backed by:
- `posts`

## Settlement sources

- `GET /settlement-sources`
- `GET /settlement-sources/{code}`

Backed by:
- `settlement_sources`

## Market creation requests

- `GET /market-requests/me`
- `POST /market-requests`
- `GET /market-requests/{request_id}`
- `PATCH /market-requests/{request_id}`
- `POST /market-requests/{request_id}/submit`
- `POST /market-requests/{request_id}/approve`
- `POST /market-requests/{request_id}/reject`
- `PUT /market-requests/{request_id}/answers/{question_key}`

Backed by:
- `market_creation_requests`
- `market_creation_request_answers`

## Markets

- `GET /markets`
- `GET /markets/{market_slug}`
- `GET /markets/{market_slug}/outcomes`
- `GET /markets/{market_slug}/order-book`
- `GET /markets/{market_slug}/trades`
- `GET /markets/{market_slug}/resolution`

Backed by:
- `markets`
- `market_outcomes`
- `trades`
- `market_resolutions`

Notes:
- `order-book` will likely be read from Redis/Rust, not only Postgres.

## Orders

- `GET /orders/me`
- `POST /orders`
- `GET /orders/{order_id}`
- `POST /orders/{order_id}/cancel`

Backed by:
- `orders`

Notes:
- writes should go through backend validation, not direct DB writes from the frontend

## Portfolio

- `GET /portfolio/me`
- `GET /portfolio/me/positions`
- `GET /portfolio/me/activity`
- `GET /portfolio/me/payment-intents`
- `POST /portfolio/me/deposits`
- `POST /portfolio/me/withdrawals`
- `POST /portfolio/me/claims`

Backed by:
- `positions`
- `trades`
- `payment_intents`
- secured ledger views/RPCs

## Disputes

- `GET /markets/{market_slug}/disputes`
- `POST /markets/{market_slug}/disputes`
- `GET /disputes/{dispute_id}`
- `POST /disputes/{dispute_id}/evidence`
- `POST /disputes/{dispute_id}/withdraw`

Backed by:
- `disputes`
- `dispute_evidence`

## Admin and operations

- `GET /admin/moderation/posts`
- `GET /admin/moderation/market-requests`
- `POST /admin/markets/{market_id}/open`
- `POST /admin/markets/{market_id}/pause`
- `POST /admin/markets/{market_id}/cancel`
- `POST /admin/markets/{market_id}/resolution-candidates`
- `POST /admin/resolution-candidates/{candidate_id}/votes`
- `POST /admin/markets/{market_id}/resolve`
- `POST /admin/disputes/{dispute_id}/uphold`
- `POST /admin/disputes/{dispute_id}/dismiss`

Backed by:
- `posts`
- `market_creation_requests`
- `market_resolution_candidates`
- `market_resolution_votes`
- `market_resolutions`
- `disputes`

## Suggested implementation order

1. `auth`
2. `profiles`
3. `communities`
4. `posts`
5. `market-requests`
6. `markets`
7. `orders`
8. `portfolio`
9. `disputes`
10. `admin`
