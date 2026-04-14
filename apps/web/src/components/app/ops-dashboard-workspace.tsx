"use client";

import { useEffect, useState } from "react";
import { beyulApiFetch } from "@/lib/api/beyul-api";
import { useAuth } from "@/components/auth/auth-provider";

type SystemStatus = {
  status: string;
  app_env: string;
  repository_backend: string;
  oracle_provider: string;
  oracle_execution_mode: string;
  market_data_provider: string;
  blocked_jurisdictions: string[];
  uptime_seconds: number;
  server_time: string;
  db_status: string | null;
  db_backend: string | null;
};

type DbHealth = {
  backend: string;
  status: string;
  missing_relations: string[];
  detail: string | null;
};

type ModerationSlaItem = {
  request_id: string;
  title: string;
  submitted_at: string;
  hours_pending: number;
};

type ModerationSlaReport = {
  sla_hours: number;
  breaching_count: number;
  items: ModerationSlaItem[];
};

type SettlementQueueItem = {
  market_id: string;
  market_slug: string;
  market_title: string;
  status: string;
  finalizes_at: string | null;
  proposed_at: string | null;
};

type SettlementQueue = {
  pending_count: number;
  items: SettlementQueueItem[];
};

function uptimeLabel(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`;
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return `${h}h ${m}m`;
}

function statusDot(status: string): string {
  if (status === "ok" || status === "healthy") return "ops-dot-green";
  if (status === "degraded" || status === "warning") return "ops-dot-yellow";
  return "ops-dot-red";
}

export const OpsDashboardWorkspace = () => {
  const { getAccessToken, session } = useAuth();
  const [system, setSystem] = useState<SystemStatus | null>(null);
  const [db, setDb] = useState<DbHealth | null>(null);
  const [sla, setSla] = useState<ModerationSlaReport | null>(null);
  const [queue, setQueue] = useState<SettlementQueue | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

  const load = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const accessToken = await getAccessToken();
      const [sys, dbh] = await Promise.all([
        beyulApiFetch<SystemStatus>("/health/system"),
        beyulApiFetch<DbHealth>("/health/db"),
      ]);
      setSystem(sys);
      setDb(dbh);

      try {
        const [slaData, queueData] = await Promise.all([
          beyulApiFetch<ModerationSlaReport>("/api/v1/admin/moderation/sla", { accessToken }),
          beyulApiFetch<SettlementQueue>("/api/v1/admin/settlement/queue", { accessToken }),
        ]);
        setSla(slaData);
        setQueue(queueData);
      } catch {
        // admin endpoints may fail for non-admin users
      }

      setLastRefresh(new Date());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load status");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => { void load(); }, [session]);

  if (isLoading && !system) {
    return <div className="ops-loading">Loading system status…</div>;
  }

  if (error && !system) {
    return <div className="ops-error">{error}</div>;
  }

  return (
    <div className="ops-shell">
      <div className="ops-header">
        <h1>Operations Dashboard</h1>
        <div className="ops-header-right">
          <span className="ops-refresh-time">
            Last refresh: {lastRefresh.toLocaleTimeString()}
          </span>
          <button type="button" className="ops-refresh-btn" onClick={() => void load()} disabled={isLoading}>
            {isLoading ? "Refreshing…" : "Refresh"}
          </button>
        </div>
      </div>

      {/* System status cards */}
      {system ? (
        <div className="ops-status-grid">
          <div className="ops-card">
            <div className="ops-card-header">
              <span className={`ops-dot ${statusDot(system.status)}`} />
              <strong>API Status</strong>
            </div>
            <div className="ops-kv">
              <span>Status</span><strong>{system.status}</strong>
              <span>Environment</span><strong>{system.app_env}</strong>
              <span>Uptime</span><strong>{uptimeLabel(system.uptime_seconds)}</strong>
              <span>Server time</span><strong>{new Date(system.server_time).toLocaleString()}</strong>
            </div>
          </div>

          <div className="ops-card">
            <div className="ops-card-header">
              <span className={`ops-dot ${statusDot(db?.status ?? "unknown")}`} />
              <strong>Database</strong>
            </div>
            <div className="ops-kv">
              <span>Backend</span><strong>{db?.backend ?? system.db_backend ?? "—"}</strong>
              <span>Status</span><strong>{db?.status ?? system.db_status ?? "—"}</strong>
              <span>Missing tables</span><strong>{db?.missing_relations.length ?? "—"}</strong>
            </div>
            {db?.missing_relations.length ? (
              <div className="ops-warning-list">
                {db.missing_relations.map((r) => <span key={r} className="ops-warning-tag">{r}</span>)}
              </div>
            ) : null}
          </div>

          <div className="ops-card">
            <div className="ops-card-header">
              <span className="ops-dot ops-dot-blue" />
              <strong>Providers</strong>
            </div>
            <div className="ops-kv">
              <span>Repository</span><strong>{system.repository_backend}</strong>
              <span>Oracle</span><strong>{system.oracle_provider} ({system.oracle_execution_mode})</strong>
              <span>Market data</span><strong>{system.market_data_provider || "none"}</strong>
            </div>
          </div>

          <div className="ops-card">
            <div className="ops-card-header">
              <span className="ops-dot ops-dot-blue" />
              <strong>Jurisdiction gating</strong>
            </div>
            {system.blocked_jurisdictions.length > 0 ? (
              <div className="ops-tag-list">
                {system.blocked_jurisdictions.map((j) => (
                  <span key={j} className="ops-blocked-tag">{j}</span>
                ))}
              </div>
            ) : (
              <p className="ops-muted">No jurisdictions blocked</p>
            )}
          </div>
        </div>
      ) : null}

      {/* Moderation SLA */}
      {sla ? (
        <div className="ops-section">
          <h2>
            Moderation SLA
            {sla.breaching_count > 0 ? (
              <span className="ops-badge ops-badge-warn">{sla.breaching_count} breaching</span>
            ) : (
              <span className="ops-badge ops-badge-ok">All clear</span>
            )}
          </h2>
          {sla.items.length > 0 ? (
            <table className="ops-table">
              <thead>
                <tr>
                  <th>Title</th>
                  <th>Submitted</th>
                  <th>Hours pending</th>
                </tr>
              </thead>
              <tbody>
                {sla.items.map((item) => (
                  <tr key={item.request_id}>
                    <td>{item.title}</td>
                    <td>{new Date(item.submitted_at).toLocaleString()}</td>
                    <td className={item.hours_pending > sla.sla_hours ? "ops-text-warn" : ""}>
                      {item.hours_pending.toFixed(1)}h
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="ops-muted">No market requests breaching SLA.</p>
          )}
        </div>
      ) : null}

      {/* Settlement queue */}
      {queue ? (
        <div className="ops-section">
          <h2>
            Settlement queue
            <span className={`ops-badge ${queue.pending_count > 0 ? "ops-badge-warn" : "ops-badge-ok"}`}>
              {queue.pending_count} pending
            </span>
          </h2>
          {queue.items.length > 0 ? (
            <table className="ops-table">
              <thead>
                <tr>
                  <th>Market</th>
                  <th>Status</th>
                  <th>Proposed</th>
                  <th>Finalizes at</th>
                </tr>
              </thead>
              <tbody>
                {queue.items.map((item) => (
                  <tr key={item.market_id}>
                    <td>{item.market_title}</td>
                    <td>{item.status}</td>
                    <td>{item.proposed_at ? new Date(item.proposed_at).toLocaleString() : "—"}</td>
                    <td>{item.finalizes_at ? new Date(item.finalizes_at).toLocaleString() : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="ops-muted">Settlement queue is empty.</p>
          )}
        </div>
      ) : null}
    </div>
  );
};
