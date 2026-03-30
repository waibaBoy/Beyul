# API Service

FastAPI service for REST APIs, auth, admin workflows, and operational orchestration.

Planned responsibilities:

- auth and session issuance
- user and admin API surfaces
- market metadata management
- order validation and submission handoff
- persistence and reconciliation workflows

Primary route groups:

- auth
- profiles
- communities
- posts
- settlement sources
- market requests
- markets
- orders
- portfolio
- disputes
- admin

Reference:

- `specs/openapi/route-map.md`

Local backend modes:

- `REPOSITORY_BACKEND=memory` keeps all profile/community/market-request flows in local in-memory storage.
- `REPOSITORY_BACKEND=postgres` switches those flows to the Postgres/Supabase repositories.
- `GET /health/db` reports whether the required schema relations exist before you attempt live requests.

Temporary dev auth for Postgres mode:

- Set `DEV_AUTH_USER_ID` to a real UUID from `auth.users` in your Supabase project.
- Optional overrides: `DEV_AUTH_USERNAME`, `DEV_AUTH_DISPLAY_NAME`, `DEV_AUTH_IS_ADMIN`.
- You can also send `X-Beyul-User-Id`, `X-Beyul-Username`, `X-Beyul-Display-Name`, and `X-Beyul-Is-Admin` headers per request.
- The API will upsert the matching row in `public.profiles` before handling the request.

Bearer token auth:

- The API verifies Supabase access tokens against `SUPABASE_URL/auth/v1/.well-known/jwks.json`.
- Protected routes accept `Authorization: Bearer <supabase_access_token>`.
- When a valid token is provided, the API provisions or updates the matching `public.profiles` row using the token `sub`.
- `ALLOW_DEV_AUTH=true` keeps the local header/env-based fallback available for development. Set it to `false` when you want to require real bearer tokens.
