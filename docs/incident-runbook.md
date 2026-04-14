# Incident Runbook

Operational playbook for Satta platform incidents.

---

## Severity levels

| Level | Description | Response time |
|-------|-------------|---------------|
| P0 | Total outage, data loss risk, funds at risk | Immediate |
| P1 | Major feature broken (trading, settlement) | < 30 min |
| P2 | Degraded experience, partial outage | < 2 hours |
| P3 | Minor issue, cosmetic, workaround exists | Next business day |

---

## Health check endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Basic liveness |
| `GET /health/db` | Database connectivity + schema check |
| `GET /health/system` | Full system status (env, uptime, providers, jurisdictions) |

---

## Common incidents

### 1. API not responding (P0)

**Symptoms**: 5xx errors, health check failing, frontend shows errors.

**Steps**:
1. Check `GET /health` — if down, the process has crashed
2. Check logs: `docker logs satta-api` or hosting provider logs
3. Verify database connectivity: `GET /health/db`
4. Check environment variables are set (especially `POSTGRES_DSN`, `JWT_SECRET`)
5. Restart the service
6. If persistent, check for resource exhaustion (memory, connections)

### 2. Settlement stuck (P1)

**Symptoms**: Markets in `settlement_proposed` for > 2 hours, users complaining.

**Steps**:
1. Check settlement queue: `GET /api/v1/admin/settlement/queue`
2. Look for markets with `finalizes_at` in the past
3. Run settlement automation: `POST /api/v1/admin/settlement/run`
4. Check oracle provider status (UMA dashboard or mock logs)
5. If oracle is down, manually finalize via admin API

### 3. Trading failures (P1)

**Symptoms**: Orders rejected, "insufficient balance" errors on funded accounts.

**Steps**:
1. Check order status in portfolio: `GET /api/v1/portfolio/me`
2. Verify market is in `open` status
3. Check order book depth for the outcome
4. Look for matching engine logs
5. Verify collateral calculation is correct

### 4. Rolling market automation stopped (P2)

**Symptoms**: No new 5-min BTC markets being created.

**Steps**:
1. Check the scheduler script is running: `Get-Process -Name powershell`
2. Check script logs in the terminal output
3. Verify API is accessible from the scheduler host
4. Check admin token hasn't expired
5. Restart: `.\scripts\scheduler\rolling-settlement-loop.ps1`

### 5. Notifications not appearing (P2)

**Symptoms**: Bell shows no notifications despite trading activity.

**Steps**:
1. Check notification service is wired: `GET /api/v1/notifications?limit=5`
2. Verify the `notifications` table exists in the database
3. Check RLS policies allow the user to read their own notifications
4. Look for errors in API logs around notification emission

### 6. Jurisdiction block incorrectly applied (P2)

**Symptoms**: Legitimate users getting 451 errors.

**Steps**:
1. Verify `BLOCKED_JURISDICTIONS` env var is correct (comma-separated ISO country codes)
2. Check the `CF-IPCountry` or `X-Country-Code` header value
3. If CDN misconfigured, check Cloudflare/proxy settings
4. Temporarily clear `BLOCKED_JURISDICTIONS` to unblock all

---

## Monitoring checklist (daily)

- [ ] `GET /health/system` returns `status: ok`
- [ ] Database has no missing relations
- [ ] Settlement queue has no items older than SLA (48h for moderation, 2h for settlement)
- [ ] Rolling market scheduler is running
- [ ] No unread P0/P1 alerts in logs

---

## Escalation

1. **Platform operator** handles P2/P3
2. **Engineering lead** handles P1, on-call for P0
3. **All hands** for P0 with data loss or funds at risk
