# Supabase helper scripts

## `010_legal_acceptances_standalone.sql`

Idempotent-ish script mirroring `supabase/migrations/010_legal_acceptances.sql` for running **directly** in the Supabase SQL editor or via `psql` when you are not applying the full migration chain.

**Prerequisites:** migrations through `009` (and `public.profiles`, `public.current_user_is_admin()` from `007_rls_policies.sql`).

**Run with psql (example):**

```bash
psql "$DATABASE_URL" -f scripts/supabase/010_legal_acceptances_standalone.sql
```

On Windows PowerShell, set `DATABASE_URL` to your Supabase session pooler or direct connection string first.
