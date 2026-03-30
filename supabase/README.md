# Supabase

This directory contains the initial PostgreSQL schema and seed data intended for Supabase.

Files:

- `migrations/`: ordered migration files that should be treated as the source of truth
- `schema.sql`: first-pass relational schema
- `seed.sql`: initial lookup and whitelist seed data

The schema assumes:

- Supabase Auth is enabled
- application users are linked through `profiles.id = auth.users.id`
- business tables live in the `public` schema

Migration order:

1. `001_extensions_and_types.sql`
2. `002_core_identity_and_social.sql`
3. `003_markets_and_trading.sql`
4. `004_resolution_and_disputes.sql`
5. `005_ledger_and_payments.sql`
6. `006_seed_reference_data.sql`
7. `007_rls_policies.sql`

Notes:

- `schema.sql` and `seed.sql` remain useful as consolidated snapshots for review.
- Apply migrations in order for actual environment setup.
- Repo/project connection guidance lives in `docs/supabase-project-setup.md`.
