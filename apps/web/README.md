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
