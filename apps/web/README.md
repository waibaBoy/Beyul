# Web App

Next.js App Router frontend for trading, positions, and market discovery.

Planned modules:

- public marketing and onboarding
- authenticated trading dashboard
- market detail and order ticket
- positions and portfolio
- admin/operator screens

Auth foundation:

- Supabase App Router SSR client via `@supabase/ssr`
- reusable browser/server client factories
- cookie refresh middleware
- auth callback route for magic links and OAuth
- reusable auth provider with email/password, magic link, phone OTP, and Google sign-in helpers
- bearer token forwarding to the FastAPI backend

## Smoke tests (Playwright)

From `apps/web`, with dependencies installed:

```bash
npx playwright test tests/signup-compliance.smoke.spec.ts
npx playwright test tests/market-history.smoke.spec.ts
```

By default `playwright.config.ts` starts `next dev` on port 3000 when nothing is listening (`reuseExistingServer: true`). To use an already-running dev server only, set `PLAYWRIGHT_SKIP_WEBSERVER=1` and start Next yourself, or rely on reuse when port 3000 is up.

Signup compliance: `/auth/sign-up` requires age + terms checkboxes and stores acceptance metadata on Supabase sign-up; FastAPI syncs rows into `legal_acceptances` after migration `010` when using Postgres.
