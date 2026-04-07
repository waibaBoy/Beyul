"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { beyulApiFetch } from "@/lib/api/beyul-api";
import { useAuth } from "@/components/auth/auth-provider";
import { AuthFeedback } from "@/components/auth/auth-feedback";
import { useAuthAction } from "@/components/auth/use-auth-action";
import type { BackendUser, PortfolioSummary } from "@/lib/api/types";

const formatValue = (value: number) =>
  value.toLocaleString(undefined, { maximumFractionDigits: 2 });

const buildSparklinePath = (
  points: number[]
): { path: string; isPositive: boolean } => {
  if (points.length <= 1) {
    return { path: "M 0 24 L 100 24", isPositive: true };
  }
  const max = Math.max(...points);
  const min = Math.min(...points);
  const range = max - min || 1;
  const isPositive = points[points.length - 1] >= points[0];
  const path = points
    .map((point, index) => {
      const x = (index / (points.length - 1)) * 100;
      const y = 42 - ((point - min) / range) * 38;
      return `${index === 0 ? "M" : "L"} ${x.toFixed(2)} ${y.toFixed(2)}`;
    })
    .join(" ");
  return { path, isPositive };
};

export const AccountCard = () => {
  const router = useRouter();
  const { getAccessToken, session, signOut, user } = useAuth();
  const [backendUser, setBackendUser] = useState<BackendUser | null>(null);
  const [portfolio, setPortfolio] = useState<PortfolioSummary | null>(null);
  const [isLoadingSnapshot, setIsLoadingSnapshot] = useState(true);
  const { errorMessage, isSubmitting, runAction, statusMessage } = useAuthAction("");

  const displayName =
    backendUser?.display_name ??
    user?.user_metadata?.display_name ??
    user?.email ??
    "Account";
  const userGlyph = displayName.charAt(0).toUpperCase();

  const loadAccountSnapshot = async () => {
    const accessToken = await getAccessToken();
    const [nextBackendUser, nextPortfolio] = await Promise.all([
      beyulApiFetch<BackendUser>("/api/v1/auth/me", { accessToken }),
      beyulApiFetch<PortfolioSummary>("/api/v1/portfolio/me", { accessToken })
    ]);
    setBackendUser(nextBackendUser);
    setPortfolio(nextPortfolio);
    return nextBackendUser;
  };

  useEffect(() => {
    let isMounted = true;

    const load = async () => {
      if (!session) {
        if (isMounted) {
          setBackendUser(null);
          setPortfolio(null);
          setIsLoadingSnapshot(false);
        }
        return;
      }
      try {
        await loadAccountSnapshot();
      } catch {
        if (isMounted) setPortfolio(null);
      } finally {
        if (isMounted) setIsLoadingSnapshot(false);
      }
    };

    void load();
    return () => {
      isMounted = false;
    };
  }, [session]);

  const metrics = useMemo(() => {
    if (!portfolio) return null;

    const settled = portfolio.balances.reduce(
      (s, b) => s + Number(b.settled_balance),
      0
    );
    const available = portfolio.balances.reduce(
      (s, b) => s + Number(b.available_balance),
      0
    );
    const reserved = portfolio.balances.reduce(
      (s, b) => s + Number(b.reserved_balance),
      0
    );
    const pnl = portfolio.positions.reduce((s, p) => {
      return (
        s +
        Number(p.realized_pnl) +
        (p.market_status === "settled" ? 0 : Number(p.unrealized_pnl))
      );
    }, 0);

    const orderedPositions = [...portfolio.positions].sort((a, b) => {
      const at = a.last_trade_at ? Date.parse(a.last_trade_at) : 0;
      const bt = b.last_trade_at ? Date.parse(b.last_trade_at) : 0;
      return at - bt;
    });

    const pnlPoints =
      orderedPositions.length > 0
        ? orderedPositions.reduce<number[]>((series, p) => {
            const prev = series[series.length - 1] ?? 0;
            const positionPnl =
              Number(p.realized_pnl) +
              (p.market_status === "settled" ? 0 : Number(p.unrealized_pnl));
            series.push(prev + positionPnl);
            return series;
          }, [0])
        : [0, pnl || 0];

    return {
      settled,
      available,
      reserved,
      pnl,
      sparkline: buildSparklinePath(pnlPoints),
      positionsCount: portfolio.positions.length,
      openOrdersCount: portfolio.open_orders.length,
      tradesCount: portfolio.recent_trades.length,
      topPositions: portfolio.positions.slice(0, 3)
    };
  }, [portfolio]);

  return (
    <section className="auth-section">
      <h2>Account overview</h2>

      {/* Identity header */}
      <div className="acct-profile">
        <div className="acct-avatar">{userGlyph}</div>
        <div className="acct-info">
          <div className="acct-name">{displayName}</div>
          <div className="acct-handle">
            {backendUser?.username
              ? `@${backendUser.username}`
              : (user?.email ?? "Not signed in")}
          </div>
          <div className="acct-badges">
            <span className={`acct-status-dot ${session ? "" : "offline"}`} />
            <span className={`acct-status-text ${session ? "" : "offline"}`}>
              {session ? "Active session" : "Signed out"}
            </span>
            {backendUser?.is_admin ? (
              <span className="acct-admin-badge">Admin</span>
            ) : null}
          </div>
        </div>
      </div>

      {/* Identity details */}
      <dl className="kv-list">
        <div>
          <dt>User ID</dt>
          <dd className="kv-truncate">{user?.id ?? "—"}</dd>
        </div>
        <div>
          <dt>Email</dt>
          <dd>{user?.email ?? "—"}</dd>
        </div>
        {user?.phone ? (
          <div>
            <dt>Phone</dt>
            <dd>{user.phone}</dd>
          </div>
        ) : null}
      </dl>

      {/* Portfolio snapshot */}
      {isLoadingSnapshot ? (
        <div className="acct-loading">Loading portfolio snapshot…</div>
      ) : !metrics ? (
        <div className="acct-empty">Sign in to view portfolio metrics.</div>
      ) : (
        <>
          {/* PnL row with sparkline */}
          <div className="acct-pnl-row">
            <div>
              <div className="acct-stat-label">Total PnL</div>
              <div
                className={`acct-pnl-value ${metrics.pnl >= 0 ? "positive" : "negative"}`}
              >
                {metrics.pnl >= 0 ? "+" : ""}
                {formatValue(metrics.pnl)}
              </div>
            </div>
            <svg
              aria-hidden="true"
              className="acct-sparkline"
              viewBox="0 0 100 48"
              preserveAspectRatio="none"
            >
              <path
                className={`acct-sparkline-path ${metrics.sparkline.isPositive ? "positive" : "negative"}`}
                d={metrics.sparkline.path}
              />
            </svg>
          </div>

          {/* Stats grid */}
          <div className="acct-stat-grid">
            <div className="acct-stat">
              <span className="acct-stat-label">Available</span>
              <span className="acct-stat-value">{formatValue(metrics.available)}</span>
            </div>
            <div className="acct-stat">
              <span className="acct-stat-label">Reserved</span>
              <span className="acct-stat-value">{formatValue(metrics.reserved)}</span>
            </div>
            <div className="acct-stat">
              <span className="acct-stat-label">Settled</span>
              <span className="acct-stat-value">{formatValue(metrics.settled)}</span>
            </div>
            <div className="acct-stat">
              <span className="acct-stat-label">Positions</span>
              <span className="acct-stat-value">{metrics.positionsCount}</span>
            </div>
            <div className="acct-stat">
              <span className="acct-stat-label">Open orders</span>
              <span className="acct-stat-value">{metrics.openOrdersCount}</span>
            </div>
            <div className="acct-stat">
              <span className="acct-stat-label">Trades</span>
              <span className="acct-stat-value">{metrics.tradesCount}</span>
            </div>
          </div>

          {/* Top positions */}
          {metrics.topPositions.length > 0 ? (
            <div className="acct-positions">
              {metrics.topPositions.map((position) => {
                const pnl =
                  Number(position.realized_pnl) +
                  (position.market_status === "settled"
                    ? 0
                    : Number(position.unrealized_pnl));
                return (
                  <div
                    className="acct-position-row"
                    key={`${position.market_id}-${position.outcome_id}`}
                  >
                    <div className="acct-position-left">
                      <div className="acct-position-market">
                        {position.market_title}
                      </div>
                      <div className="acct-position-outcome">
                        {position.outcome_label} · {position.market_status}
                      </div>
                    </div>
                    <span
                      className={`acct-position-pnl ${pnl >= 0 ? "positive" : "negative"}`}
                    >
                      {pnl >= 0 ? "+" : ""}
                      {formatValue(pnl)}
                    </span>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="acct-empty">No active positions yet.</div>
          )}
        </>
      )}

      <div className="button-row">
        <button
          className="button-primary"
          disabled={isSubmitting || !session}
          onClick={() =>
            void runAction("Refreshing…", loadAccountSnapshot, {
              successMessage: "Account refreshed."
            })
          }
          type="button"
        >
          Refresh
        </button>
        <button
          className="button-secondary"
          disabled={isSubmitting || !session}
          onClick={() => router.push("/portfolio")}
          type="button"
        >
          Full portfolio
        </button>
        <button
          className="button-secondary"
          disabled={isSubmitting || !session}
          onClick={() =>
            void runAction(
              "Signing out…",
              async () => {
                await signOut();
                setBackendUser(null);
                router.replace("/auth/sign-in");
              },
              { successMessage: "Signed out." }
            )
          }
          type="button"
        >
          Sign out
        </button>
      </div>

      <AuthFeedback errorMessage={errorMessage} statusMessage={statusMessage} />
    </section>
  );
};
