"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { AuthFeedback } from "@/components/auth/auth-feedback";
import { useAuth } from "@/components/auth/auth-provider";
import { useAuthAction } from "@/components/auth/use-auth-action";
import { beyulApiFetch } from "@/lib/api/beyul-api";
import type { AdminFundBalanceInput, BackendUser, PortfolioPosition, PortfolioSummary } from "@/lib/api/types";

/* ── Formatters ──────────────────────────────────────────── */
const fmt = (v: string | number | null, decimals = 2) => {
  if (v === null || v === undefined) return "—";
  const n = Number(v);
  if (!Number.isFinite(n)) return "—";
  return n.toLocaleString(undefined, { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
};
const fmtPrice = (v: string | null) => (v ? `${Math.round(Number(v) * 100)}¢` : "—");
const fmtPnl = (v: string) => {
  const n = Number(v);
  const sign = n >= 0 ? "+" : "";
  return `${sign}${fmt(v)}`;
};
const fmtTime = (v: string | null) => {
  if (!v) return "—";
  return new Date(v).toLocaleDateString([], { month: "short", day: "numeric", year: "numeric" });
};
const pnlClass = (v: string | number) => {
  const n = Number(v);
  if (n > 0) return "pnl-positive";
  if (n < 0) return "pnl-negative";
  return "pnl-zero";
};
const positionLabel = (qty: string, outcome: string) => {
  const n = Number(qty);
  if (n > 0) return `Long ${outcome}`;
  if (n < 0) return `Short ${outcome}`;
  return outcome;
};
const statusLabel = (marketStatus: string, qty: string) =>
  marketStatus === "settled" && Number(qty) === 0 ? "Settled" : marketStatus.replace(/_/g, " ");

/* ── PnL Chart ───────────────────────────────────────────── */
type ChartPoint = { x: number; y: number; label: string; value: number };

function buildPnlCurve(positions: PortfolioPosition[]) {
  if (positions.length === 0) return { points: [], min: 0, max: 0, pathD: "", areaD: "", zeroY: 0, W: 560, H: 200 };

  const W = 560;
  const H = 200;
  const PAD = { top: 20, right: 24, bottom: 36, left: 60 };
  const chartW = W - PAD.left - PAD.right;
  const chartH = H - PAD.top - PAD.bottom;

  // Sort by last trade date, fallback to market title alpha
  const sorted = [...positions].sort((a, b) => {
    if (a.last_trade_at && b.last_trade_at) return a.last_trade_at.localeCompare(b.last_trade_at);
    return a.market_title.localeCompare(b.market_title);
  });

  // Cumulative realized PnL per position
  let running = 0;
  const rawPoints: ChartPoint[] = sorted.map((pos, i) => {
    running += Number(pos.realized_pnl);
    return {
      x: i,
      y: running,
      label: pos.market_title.slice(0, 22),
      value: running
    };
  });

  // Also add unrealized for open positions as a dashed lookahead
  const unrealizedTotal = positions.reduce((acc, p) => acc + Number(p.unrealized_pnl), 0);

  const allValues = rawPoints.map((p) => p.y);
  const min = Math.min(0, ...allValues);
  const max = Math.max(0, ...allValues, unrealizedTotal !== 0 ? running + unrealizedTotal : 0);
  const range = max - min || 1;

  const toX = (i: number) => PAD.left + (i / Math.max(rawPoints.length - 1, 1)) * chartW;
  const toY = (v: number) => PAD.top + chartH - ((v - min) / range) * chartH;
  const zeroY = toY(0);

  const points: ChartPoint[] = rawPoints.map((p, i) => ({ ...p, x: toX(i), y: toY(p.y) }));

  // Smooth path (catmull-rom approximation)
  const pathD = points.length < 2
    ? `M ${points[0]?.x ?? 0} ${points[0]?.y ?? 0}`
    : points.reduce((acc, pt, i) => {
        if (i === 0) return `M ${pt.x} ${pt.y}`;
        const prev = points[i - 1];
        const cpx = (prev.x + pt.x) / 2;
        return `${acc} C ${cpx} ${prev.y} ${cpx} ${pt.y} ${pt.x} ${pt.y}`;
      }, "");

  const last = points[points.length - 1];
  const first = points[0];
  const areaD = last && first
    ? `${pathD} L ${last.x} ${zeroY} L ${first.x} ${zeroY} Z`
    : "";

  return { points, min, max, pathD, areaD, zeroY, W, H, PAD, toY, toX };
}

type Tab = "positions" | "orders" | "trades";

export const PortfolioWorkspace = () => {
  const { getAccessToken, session } = useAuth();
  const [backendUser, setBackendUser] = useState<BackendUser | null>(null);
  const [portfolio, setPortfolio] = useState<PortfolioSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<Tab>("positions");
  const [hoveredPoint, setHoveredPoint] = useState<ChartPoint | null>(null);
  const [fundForm, setFundForm] = useState<AdminFundBalanceInput>({
    profile_id: "",
    asset_code: "USDC",
    rail_mode: "onchain",
    amount: "100",
    description: "Admin funding"
  });
  const { errorMessage, isSubmitting, runAction, setStatusMessage, statusMessage } = useAuthAction("");

  const loadPortfolio = async () => {
    const accessToken = await getAccessToken();
    const [nextUser, nextPortfolio] = await Promise.all([
      beyulApiFetch<BackendUser>("/api/v1/auth/me", { accessToken }),
      beyulApiFetch<PortfolioSummary>("/api/v1/portfolio/me", { accessToken })
    ]);
    setBackendUser(nextUser);
    setFundForm((c) => ({ ...c, profile_id: c.profile_id || nextUser.id }));
    setPortfolio(nextPortfolio);
    setStatusMessage("");
  };

  useEffect(() => {
    let alive = true;
    const load = async () => {
      if (!session) { if (alive) { setBackendUser(null); setPortfolio(null); setIsLoading(false); } return; }
      try { await loadPortfolio(); }
      catch (e) { if (alive) setStatusMessage(e instanceof Error ? e.message : "Failed to load portfolio."); }
      finally { if (alive) setIsLoading(false); }
    };
    void load();
    return () => { alive = false; };
  }, [session]);

  /* ── Summary metrics ─────────────────────────────────── */
  const summary = useMemo(() => {
    if (!portfolio) return null;
    const totalAvailable = portfolio.balances.reduce((s, b) => s + Number(b.available_balance), 0);
    const totalSettled = portfolio.balances.reduce((s, b) => s + Number(b.settled_balance), 0);
    const totalReserved = portfolio.balances.reduce((s, b) => s + Number(b.reserved_balance), 0);
    const realizedPnl = portfolio.positions.reduce((s, p) => s + Number(p.realized_pnl), 0);
    const unrealizedPnl = portfolio.positions.reduce((s, p) => s + Number(p.unrealized_pnl), 0);
    const openPositions = portfolio.positions.filter((p) => p.market_status === "open").length;
    return { totalAvailable, totalSettled, totalReserved, realizedPnl, unrealizedPnl, openPositions };
  }, [portfolio]);

  /* ── PnL chart ───────────────────────────────────────── */
  const chart = useMemo(() => buildPnlCurve(portfolio?.positions ?? []), [portfolio]);
  const isChartPositive = (summary?.realizedPnl ?? 0) >= 0;

  /* ── Tabs ────────────────────────────────────────────── */
  const tabs: { id: Tab; label: string; count: number }[] = [
    { id: "positions", label: "Positions", count: portfolio?.positions.length ?? 0 },
    { id: "orders", label: "Open orders", count: portfolio?.open_orders.length ?? 0 },
    { id: "trades", label: "Trade history", count: portfolio?.recent_trades.length ?? 0 }
  ];

  if (!session && !isLoading) {
    return (
      <div className="pf-signin-prompt">
        <div className="pf-signin-icon" aria-hidden="true">📊</div>
        <h2>Sign in to view your portfolio</h2>
        <p>Track your positions, balances, open orders, and realized PnL all in one place.</p>
        <div className="button-row" style={{ justifyContent: "center" }}>
          <Link className="button-primary hero-link" href="/auth/sign-in">Sign in</Link>
          <Link className="button-secondary hero-link" href="/auth/sign-up">Create account</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="pf-shell">

      {/* ── Summary bar ─────────────────────────────────── */}
      <div className="pf-summary-bar">
        {isLoading ? (
          Array.from({ length: 5 }).map((_, i) => (
            <div className="pf-stat-card pf-stat-skeleton" key={i} />
          ))
        ) : summary ? (
          <>
            <div className="pf-stat-card">
              <span className="pf-stat-label">Available balance</span>
              <strong className="pf-stat-value">{fmt(summary.totalAvailable)}</strong>
              <span className="pf-stat-sub">{fmt(summary.totalReserved)} reserved</span>
            </div>
            <div className="pf-stat-card">
              <span className="pf-stat-label">Settled balance</span>
              <strong className="pf-stat-value">{fmt(summary.totalSettled)}</strong>
              <span className="pf-stat-sub">across {portfolio?.balances.length ?? 0} account{portfolio?.balances.length !== 1 ? "s" : ""}</span>
            </div>
            <div className="pf-stat-card">
              <span className="pf-stat-label">Realized PnL</span>
              <strong className={`pf-stat-value ${pnlClass(summary.realizedPnl)}`}>{fmtPnl(String(summary.realizedPnl))}</strong>
              <span className="pf-stat-sub">from closed positions</span>
            </div>
            <div className="pf-stat-card">
              <span className="pf-stat-label">Unrealized PnL</span>
              <strong className={`pf-stat-value ${pnlClass(summary.unrealizedPnl)}`}>{fmtPnl(String(summary.unrealizedPnl))}</strong>
              <span className="pf-stat-sub">mark-to-market</span>
            </div>
            <div className="pf-stat-card">
              <span className="pf-stat-label">Open positions</span>
              <strong className="pf-stat-value">{summary.openPositions}</strong>
              <span className="pf-stat-sub">{portfolio?.open_orders.length ?? 0} resting orders</span>
            </div>
          </>
        ) : null}
      </div>

      {/* ── PnL chart ───────────────────────────────────── */}
      <div className="pf-chart-card">
        <div className="pf-chart-header">
          <div>
            <h2 className="pf-chart-title">Cumulative PnL</h2>
            <p className="pf-chart-sub">Realized PnL accrued across all closed positions, in order of last trade.</p>
          </div>
          {hoveredPoint && (
            <div className="pf-chart-tooltip">
              <span>{hoveredPoint.label}</span>
              <strong className={pnlClass(hoveredPoint.value)}>{fmtPnl(String(hoveredPoint.value))}</strong>
            </div>
          )}
        </div>

        {isLoading ? (
          <div className="pf-chart-loading">Loading chart data…</div>
        ) : (portfolio?.positions.length ?? 0) === 0 ? (
          <div className="pf-chart-empty">
            <span>No position history yet.</span>
            <Link href="/markets" className="button-secondary hero-link" style={{ marginTop: 12 }}>Browse markets</Link>
          </div>
        ) : (
          <div className="pf-chart-area">
            {/* Y-axis labels */}
            <div className="pf-chart-y-axis">
              {[chart.max, (chart.max + chart.min) / 2, chart.min].map((v, i) => (
                <span key={i} className={`pf-y-label ${pnlClass(v)}`}>{v >= 0 ? "+" : ""}{Math.round(v)}</span>
              ))}
            </div>
            <div className="pf-chart-svg-wrap">
              <svg
                className="pf-chart-svg"
                viewBox={`0 0 ${chart.W} ${chart.H}`}
                preserveAspectRatio="none"
              >
                <defs>
                  <linearGradient id="pf-grad-pos" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="var(--yes)" stopOpacity="0.28" />
                    <stop offset="100%" stopColor="var(--yes)" stopOpacity="0.02" />
                  </linearGradient>
                  <linearGradient id="pf-grad-neg" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="var(--no)" stopOpacity="0.02" />
                    <stop offset="100%" stopColor="var(--no)" stopOpacity="0.22" />
                  </linearGradient>
                  <clipPath id="pf-clip-pos">
                    <rect x="0" y="0" width={chart.W} height={chart.zeroY} />
                  </clipPath>
                  <clipPath id="pf-clip-neg">
                    <rect x="0" y={chart.zeroY} width={chart.W} height={chart.H} />
                  </clipPath>
                </defs>

                {/* Grid lines */}
                {[0.25, 0.5, 0.75].map((frac) => {
                  const y = (chart.H ?? 200) * frac;
                  return <line key={frac} x1={0} x2={chart.W} y1={y} y2={y} className="pf-grid-line" />;
                })}

                {/* Zero baseline */}
                <line x1={0} x2={chart.W} y1={chart.zeroY} y2={chart.zeroY} className="pf-zero-line" />

                {/* Area fill — positive (above zero) */}
                <path d={chart.areaD} fill="url(#pf-grad-pos)" clipPath="url(#pf-clip-pos)" />
                {/* Area fill — negative (below zero) */}
                <path d={chart.areaD} fill="url(#pf-grad-neg)" clipPath="url(#pf-clip-neg)" />

                {/* Main line */}
                <path
                  d={chart.pathD}
                  className={`pf-chart-line ${isChartPositive ? "pf-line-pos" : "pf-line-neg"}`}
                />

                {/* Hover dots */}
                {chart.points.map((pt, i) => (
                  <g key={i}>
                    <circle
                      cx={pt.x}
                      cy={pt.y}
                      r={hoveredPoint === pt ? 6 : 4}
                      className={`pf-chart-dot ${pt.value >= 0 ? "pf-dot-pos" : "pf-dot-neg"} ${hoveredPoint === pt ? "pf-dot-active" : ""}`}
                      onMouseEnter={() => setHoveredPoint(pt)}
                      onMouseLeave={() => setHoveredPoint(null)}
                    />
                    {/* Hit area */}
                    <circle
                      cx={pt.x}
                      cy={pt.y}
                      r={16}
                      fill="transparent"
                      onMouseEnter={() => setHoveredPoint(pt)}
                      onMouseLeave={() => setHoveredPoint(null)}
                    />
                  </g>
                ))}

                {/* Vertical crosshair on hover */}
                {hoveredPoint && (
                  <line
                    x1={hoveredPoint.x}
                    x2={hoveredPoint.x}
                    y1={0}
                    y2={chart.H}
                    className="pf-crosshair"
                  />
                )}
              </svg>

              {/* X-axis labels */}
              {chart.points.length > 0 && (
                <div className="pf-chart-x-axis">
                  {chart.points
                    .filter((_, i) => i === 0 || i === Math.floor(chart.points.length / 2) || i === chart.points.length - 1)
                    .map((pt, i) => (
                      <span key={i} className="pf-x-label">{pt.label}</span>
                    ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Balance breakdown strip */}
        {!isLoading && (portfolio?.balances.length ?? 0) > 0 && (
          <div className="pf-balance-strip">
            {portfolio!.balances.map((b) => (
              <div className="pf-balance-item" key={b.account_code}>
                <div className="pf-balance-labels">
                  <strong>{b.asset_code}</strong>
                  <span className="market-meta-chip">{b.rail_mode}</span>
                </div>
                <div className="pf-balance-bars">
                  <div className="pf-balance-bar-row">
                    <span>Available</span>
                    <div className="pf-bar-track">
                      <div
                        className="pf-bar-fill pf-bar-available"
                        style={{ width: `${(Number(b.available_balance) / Math.max(Number(b.settled_balance), 1)) * 100}%` }}
                      />
                    </div>
                    <span className="pf-bar-val">{fmt(b.available_balance)}</span>
                  </div>
                  <div className="pf-balance-bar-row">
                    <span>Reserved</span>
                    <div className="pf-bar-track">
                      <div
                        className="pf-bar-fill pf-bar-reserved"
                        style={{ width: `${(Number(b.reserved_balance) / Math.max(Number(b.settled_balance), 1)) * 100}%` }}
                      />
                    </div>
                    <span className="pf-bar-val">{fmt(b.reserved_balance)}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── Tab panel ───────────────────────────────────── */}
      <div className="pf-tab-panel">
        <div className="pf-tabs" role="tablist">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              role="tab"
              aria-selected={activeTab === tab.id}
              className={`pf-tab ${activeTab === tab.id ? "is-active" : ""}`}
              onClick={() => setActiveTab(tab.id)}
              type="button"
            >
              {tab.label}
              <span className="pf-tab-count">{tab.count}</span>
            </button>
          ))}
        </div>

        {/* Positions */}
        {activeTab === "positions" && (
          <div className="pf-table-wrap">
            {isLoading ? (
              <div className="pf-table-loading">Loading positions…</div>
            ) : (portfolio?.positions.length ?? 0) === 0 ? (
              <div className="pf-table-empty">
                <p>No positions yet.</p>
                <Link href="/markets" className="button-primary hero-link">Browse markets</Link>
              </div>
            ) : (
              <table className="pf-table">
                <thead>
                  <tr>
                    <th>Market</th>
                    <th>Position</th>
                    <th className="pf-th-num">Qty</th>
                    <th className="pf-th-num">Avg entry</th>
                    <th className="pf-th-num">Cost</th>
                    <th className="pf-th-num">Realized PnL</th>
                    <th className="pf-th-num">Unrealized</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {portfolio!.positions.map((pos) => (
                    <tr key={`${pos.market_id}-${pos.outcome_id}`} className="pf-table-row">
                      <td className="pf-td-market">
                        <Link href={`/markets/${pos.market_slug}`} className="pf-market-link">
                          {pos.market_title}
                        </Link>
                        <span className="pf-td-date">{fmtTime(pos.last_trade_at)}</span>
                      </td>
                      <td>
                        <span className={`pf-side-badge ${Number(pos.quantity) >= 0 ? "pf-side-long" : "pf-side-short"}`}>
                          {positionLabel(pos.quantity, pos.outcome_label)}
                        </span>
                      </td>
                      <td className="pf-td-num">{fmt(pos.quantity, 0)}</td>
                      <td className="pf-td-num">{fmtPrice(pos.average_entry_price)}</td>
                      <td className="pf-td-num">{fmt(pos.net_cost)}</td>
                      <td className={`pf-td-num pf-td-pnl ${pnlClass(pos.realized_pnl)}`}>
                        {fmtPnl(pos.realized_pnl)}
                      </td>
                      <td className={`pf-td-num pf-td-pnl ${pnlClass(pos.unrealized_pnl)}`}>
                        {pos.market_status === "settled" ? "—" : fmtPnl(pos.unrealized_pnl)}
                      </td>
                      <td>
                        <span className={`pf-status-chip pf-status-${pos.market_status.replace(/_/g, "-")}`}>
                          {statusLabel(pos.market_status, pos.quantity)}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}

        {/* Open orders */}
        {activeTab === "orders" && (
          <div className="pf-table-wrap">
            {isLoading ? (
              <div className="pf-table-loading">Loading orders…</div>
            ) : (portfolio?.open_orders.length ?? 0) === 0 ? (
              <div className="pf-table-empty">
                <p>No open orders right now.</p>
              </div>
            ) : (
              <table className="pf-table">
                <thead>
                  <tr>
                    <th>Market</th>
                    <th>Side</th>
                    <th className="pf-th-num">Qty</th>
                    <th className="pf-th-num">Remaining</th>
                    <th className="pf-th-num">Limit price</th>
                    <th className="pf-th-num">Collateral</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {portfolio!.open_orders.map((order) => (
                    <tr key={order.id} className="pf-table-row">
                      <td className="pf-td-market">
                        <strong className="pf-market-link">{order.outcome_label}</strong>
                      </td>
                      <td>
                        <span className={`pf-side-badge ${order.side === "buy" ? "pf-side-long" : "pf-side-short"}`}>
                          {order.side === "buy" ? "Buy" : "Sell"}
                        </span>
                      </td>
                      <td className="pf-td-num">{fmt(order.quantity, 0)}</td>
                      <td className="pf-td-num">{fmt(order.remaining_quantity, 0)}</td>
                      <td className="pf-td-num">{fmtPrice(order.price)}</td>
                      <td className="pf-td-num">{order.max_total_cost ? fmt(order.max_total_cost) : "—"}</td>
                      <td>
                        <span className={`pf-status-chip pf-status-${order.status.replace(/_/g, "-")}`}>
                          {order.status.replace(/_/g, " ")}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}

        {/* Trade history */}
        {activeTab === "trades" && (
          <div className="pf-table-wrap">
            {isLoading ? (
              <div className="pf-table-loading">Loading trades…</div>
            ) : (portfolio?.recent_trades.length ?? 0) === 0 ? (
              <div className="pf-table-empty">
                <p>No trades on this account yet.</p>
              </div>
            ) : (
              <table className="pf-table">
                <thead>
                  <tr>
                    <th>Outcome</th>
                    <th className="pf-th-num">Price</th>
                    <th className="pf-th-num">Qty</th>
                    <th className="pf-th-num">Gross notional</th>
                    <th>Time</th>
                  </tr>
                </thead>
                <tbody>
                  {portfolio!.recent_trades.map((trade) => (
                    <tr key={trade.id} className="pf-table-row">
                      <td className="pf-td-market">
                        <strong>{trade.outcome_label}</strong>
                      </td>
                      <td className="pf-td-num">{fmtPrice(trade.price)}</td>
                      <td className="pf-td-num">{fmt(trade.quantity, 0)}</td>
                      <td className="pf-td-num">{fmt(trade.gross_notional)}</td>
                      <td className="pf-td-date-cell">
                        {trade.executed_at
                          ? new Date(trade.executed_at).toLocaleTimeString([], { hour: "numeric", minute: "2-digit", second: "2-digit" })
                          : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}
      </div>

      {/* ── Admin funding (collapsed accordion) ─────────── */}
      {backendUser?.is_admin && (
        <details className="pf-admin-details">
          <summary className="pf-admin-summary">
            <span>Admin — fund balance</span>
            <span className="pill">admin only</span>
          </summary>
          <div className="pf-admin-body">
            <form
              className="auth-form"
              onSubmit={(e) => {
                e.preventDefault();
                void runAction("Funding balance...", async () => {
                  const accessToken = await getAccessToken();
                  const next = await beyulApiFetch<PortfolioSummary>("/api/v1/admin/fund-balance", {
                    method: "POST", accessToken, json: fundForm
                  });
                  if (backendUser.id === fundForm.profile_id) setPortfolio(next);
                  return next;
                }, { successMessage: "Funding adjustment posted." });
              }}
            >
              <div className="pf-admin-grid">
                <div className="field">
                  <label htmlFor="fund-profile-id">Profile ID</label>
                  <input id="fund-profile-id" value={fundForm.profile_id}
                    onChange={(e) => setFundForm((c) => ({ ...c, profile_id: e.target.value }))} />
                </div>
                <div className="field">
                  <label htmlFor="fund-amount">Amount</label>
                  <input id="fund-amount" inputMode="decimal" value={fundForm.amount}
                    onChange={(e) => setFundForm((c) => ({ ...c, amount: e.target.value }))} />
                </div>
                <div className="field">
                  <label htmlFor="fund-asset">Asset</label>
                  <select className="select-field" id="fund-asset" value={fundForm.asset_code}
                    onChange={(e) => setFundForm((c) => ({ ...c, asset_code: e.target.value }))}>
                    <option value="USDC">USDC</option>
                    <option value="AUD">AUD</option>
                  </select>
                </div>
                <div className="field">
                  <label htmlFor="fund-rail">Rail</label>
                  <select className="select-field" id="fund-rail" value={fundForm.rail_mode}
                    onChange={(e) => setFundForm((c) => ({ ...c, rail_mode: e.target.value }))}>
                    <option value="onchain">onchain</option>
                    <option value="custodial">custodial</option>
                  </select>
                </div>
              </div>
              <div className="field">
                <label htmlFor="fund-description">Description</label>
                <input id="fund-description" value={fundForm.description || ""}
                  onChange={(e) => setFundForm((c) => ({ ...c, description: e.target.value }))} />
              </div>
              <div className="button-row">
                <button className="button-primary" disabled={isSubmitting} type="submit">
                  Post adjustment
                </button>
              </div>
            </form>
          </div>
        </details>
      )}

      <AuthFeedback errorMessage={errorMessage} statusMessage={statusMessage} />
    </div>
  );
};
