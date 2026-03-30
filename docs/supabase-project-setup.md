# Supabase Project Setup

This document prepares the repo for connecting to a real Supabase project once you are ready.

## Required project values

Collect these from the Supabase project dashboard when the project exists:

- `SUPABASE_PROJECT_REF`
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_DB_PASSWORD`

## Where they are used

- Root `.env`: shared local defaults
- `apps/web/.env`: browser-safe public values only
- `services/api/.env`: backend-only secrets and service access
- `supabase/.env`: project-level migration/deployment context

## Recommended connection model

### Frontend

Use:

- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`

The frontend should never receive the service role key.

### FastAPI backend

Use:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_JWT_SECRET`

The backend can use:

- Supabase Auth JWT verification
- elevated reads/writes where direct client access should be blocked
- RPC or server-side workflows for orders, settlement, and ledger changes

### Database migrations

Treat `supabase/migrations/` as the source of truth and apply migrations in order.

## Suggested rollout once the project exists

1. Create the Supabase project.
2. Add the project values to the repo env files.
3. Apply migrations in order from `supabase/migrations/`.
4. Verify tables, enums, views, and triggers exist.
5. Verify RLS is enabled on the intended tables.
6. Only then start wiring FastAPI and Next.js to the live project.

## What stays local for now

- `schema.sql` and `seed.sql` remain consolidated review snapshots
- `docs/domain-rules.md` remains the product-rule reference
- `docs/rls-policy-plan.md` remains the policy design reference beside the actual RLS migration
