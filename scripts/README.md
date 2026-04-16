# Scripts

Repo automation lives here. The directory is no longer only a placeholder.

## Current scripts

- `oracle-dispute-smoke.ps1` runs a market request -> publish -> settlement request -> dispute -> evidence -> oracle callback/finalization smoke flow. It supports skip-order and two-user matched-order paths.
- `scheduler/` contains scheduler helpers for local automation.
- `supabase/` contains migration/compliance helper scripts.

## Still needed

- local one-command bootstrap
- repeatable database migration runner
- seed data loaders for beta environments
- contract deployment wrappers
- release packaging and deployment smoke checks
