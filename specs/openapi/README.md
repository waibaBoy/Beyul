# OpenAPI Plan

This directory will hold the public and admin API definitions.

Initial resource groups:

- `/auth`
- `/profiles`
- `/communities`
- `/posts`
- `/settlement-sources`
- `/market-requests`
- `/markets`
- `/orders`
- `/portfolio`
- `/disputes`
- `/admin/markets`
- `/admin/settlement`

Initial non-goals:

- exposing engine internals directly to the frontend
- mixing admin and public authorization concerns in the same route groups

Detailed route planning lives in `specs/openapi/route-map.md`.
