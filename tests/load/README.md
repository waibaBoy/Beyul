# Load Testing

Uses [k6](https://k6.io/) for load testing the Satta API.

## Prerequisites

Install k6: https://k6.io/docs/getting-started/installation/

## Run

```bash
k6 run smoke.js           # quick smoke (5 VUs, 30s)
k6 run trading-load.js    # trading stress (50 VUs, 2m)
```

## Scenarios

- `smoke.js` — Basic API health and market listing
- `trading-load.js` — Concurrent order placement and portfolio reads
