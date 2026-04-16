"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useAuth } from "@/components/auth/auth-provider";
import { beyulApiFetch } from "@/lib/api/beyul-api";
import type { Market, MarketHistory } from "@/lib/api/types";
import {
  type MarketDiscoveryCategory,
  filterMarketsByDiscoveryCategory,
  getMarketDiscoveryCategory,
  isMarketDiscoveryCategory,
  sortMarketsByVolume
} from "@/lib/markets/discovery";
import { MarketIcon } from "@/components/app/market-icon";

const MAX_GRID_MARKETS = 12;

const formatVolume = (value: string) => {
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed === 0) return "—";
  if (parsed >= 1_000_000) return `$${(parsed / 1_000_000).toFixed(1)}M`;
  if (parsed >= 1_000) return `$${Math.round(parsed / 1_000)}k`;
  return `$${Math.round(parsed)}`;
};

const formatPrice = (value: string | null): number | null => {
  if (!value) return null;
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return null;
  return Math.round(parsed * 100);
};

const formatCountdown = (value: string | null): string | null => {
  if (!value) return null;
  const diffMs = new Date(value).getTime() - Date.now();
  if (!Number.isFinite(diffMs) || diffMs <= 0) return null;
  const totalMinutes = Math.floor(diffMs / 60000);
  const days = Math.floor(totalMinutes / (60 * 24));
  const hours = Math.floor((totalMinutes % (60 * 24)) / 60);
  if (days > 0) return `${days}d`;
  if (hours > 0) return `${hours}h`;
  return `${totalMinutes}m`;
};

const buildSparklinePath = (points: number[]) => {
  if (points.length < 2) return null;
  const width = 100;
  const height = 28;
  const min = Math.min(...points);
  const max = Math.max(...points);
  const span = max - min || 1;
  return points
    .map((value, index) => {
      const x = (index / (points.length - 1)) * width;
      const y = height - ((value - min) / span) * height;
      return `${index === 0 ? "M" : "L"}${x.toFixed(2)} ${y.toFixed(2)}`;
    })
    .join(" ");
};

const LandingMiniSparkline = ({ slug, outcomeId }: { slug: string; outcomeId?: string }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const fetchedRef = useRef(false);
  const [points, setPoints] = useState<number[]>([]);

  useEffect(() => {
    fetchedRef.current = false;
    setPoints([]);
    const el = containerRef.current;
    if (!el || !outcomeId) {
      return;
    }
    let cancelled = false;
    const observer = new IntersectionObserver(
      (entries) => {
        if (!entries[0]?.isIntersecting || fetchedRef.current) {
          return;
        }
        fetchedRef.current = true;
        observer.disconnect();
        void (async () => {
          try {
            const params = new URLSearchParams({
              outcome_id: outcomeId,
              range: "1D"
            });
            const history = await beyulApiFetch<MarketHistory>(`/api/v1/markets/${slug}/history?${params.toString()}`);
            if (cancelled) {
              return;
            }
            const nextPoints = history.buckets
              .map((bucket) => Number(bucket.close_price ?? bucket.open_price))
              .filter((price) => Number.isFinite(price));
            setPoints(nextPoints);
          } catch {
            if (!cancelled) {
              setPoints([]);
            }
          }
        })();
      },
      { rootMargin: "160px 0px", threshold: 0.01 }
    );
    observer.observe(el);
    return () => {
      cancelled = true;
      observer.disconnect();
    };
  }, [slug, outcomeId]);

  return (
    <div ref={containerRef} className="landing-mini-chart" aria-hidden="true">
      <svg viewBox="0 0 100 28" preserveAspectRatio="none">
        <path d={buildSparklinePath(points) ?? "M0 14 L100 14"} className="landing-mini-chart-path" />
      </svg>
    </div>
  );
};

export const LandingWorkspace = () => {
  const [markets, setMarkets] = useState<Market[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const { user } = useAuth();
  const searchParams = useSearchParams();
  const categoryParam = searchParams.get("category");
  const selectedCategory: MarketDiscoveryCategory = isMarketDiscoveryCategory(categoryParam)
    ? categoryParam
    : "Trending";

  useEffect(() => {
    let isMounted = true;
    const load = async () => {
      try {
        const next = await beyulApiFetch<Market[]>("/api/v1/markets?limit=20&status=open");
        if (isMounted) setMarkets(next);
      } catch {
        // silent on landing
      } finally {
        if (isMounted) setIsLoading(false);
      }
    };
    void load();
    return () => {
      isMounted = false;
    };
  }, []);

  const sortedMarkets = useMemo(() => sortMarketsByVolume(markets), [markets]);

  const openMarkets = useMemo(() => {
    const live = sortedMarkets.filter((m) => m.status === "open");
    const fallback = sortedMarkets.filter((m) => !["settled", "cancelled"].includes(m.status));
    return (live.length > 0 ? live : fallback).slice(0, MAX_GRID_MARKETS);
  }, [sortedMarkets]);

  const filteredMarkets = useMemo(
    () => filterMarketsByDiscoveryCategory(openMarkets, selectedCategory),
    [openMarkets, selectedCategory]
  );

  const featuredMarkets = useMemo(() => sortedMarkets.slice(0, 3), [sortedMarkets]);

  const communityHighlights = useMemo(() => {
    const seen = new Map<string, { label: string; href: string }>();
    for (const market of sortedMarkets) {
      if (!market.community_slug || !market.community_name || seen.has(market.community_slug)) continue;
      seen.set(market.community_slug, {
        label: market.community_name,
        href: `/communities/${market.community_slug}`
      });
      if (seen.size >= 6) break;
    }
    return Array.from(seen.values());
  }, [sortedMarkets]);

  const liveCount = markets.filter((m) => m.status === "open").length;
  const totalVolume = markets.reduce((s, m) => s + Number(m.traded_volume || 0), 0);
  const totalTrades = markets.reduce((s, m) => s + Number(m.total_trades_count || 0), 0);

  return (
    <main className="landing-shell">

      {/* ── Hero ─────────────────────────────────────── */}
      <section className="landing-hero">
        <div className="landing-hero-body">
          <p className="landing-eyebrow">Prediction markets · Australia</p>
          <h1 className="landing-h1">
            Bet on what<br />happens next.
          </h1>
          <p className="landing-sub">
            Trade real-money contracts on politics, crypto, sports, and more.
            Create your own markets, join communities, get paid when you&apos;re right.
          </p>
          <div className="landing-ctas">
            <Link className="landing-cta-primary" href="/markets">
              Browse markets
            </Link>
            <Link className="landing-cta-secondary" href={user ? "/portfolio" : "/auth/sign-up"}>
              {user ? "My portfolio" : "Get started free"}
            </Link>
          </div>
        </div>

        <div className="landing-stats">
          <div className="landing-stat">
            <strong>{liveCount}</strong>
            <span>live markets</span>
          </div>
          <div className="landing-stat-sep" />
          <div className="landing-stat">
            <strong>{formatVolume(String(totalVolume))}</strong>
            <span>total volume</span>
          </div>
          <div className="landing-stat-sep" />
          <div className="landing-stat">
            <strong>{totalTrades.toLocaleString()}</strong>
            <span>trades placed</span>
          </div>
          <div className="landing-stat-sep" />
          <div className="landing-stat">
            <strong>{markets.length}</strong>
            <span>markets total</span>
          </div>
        </div>
      </section>

      {/* ── Featured markets ─────────────────────────── */}
      {!isLoading && featuredMarkets.length > 0 && (
        <section className="landing-section">
          <div className="landing-section-head">
            <span className="eyebrow">Featured</span>
            <Link className="landing-view-all" href="/markets">View all →</Link>
          </div>
          <div className="landing-featured-row">
            {featuredMarkets.map((market) => {
              const yes = formatPrice(market.last_price);
              const no = yes !== null ? 100 - yes : null;
              const countdown = formatCountdown(market.timing.trading_closes_at);
              return (
                <Link className="landing-feat-card" href={`/markets/${market.slug}`} key={market.id}>
                  <div className="landing-feat-top">
                    <span className={`landing-status-dot ${market.status === "open" ? "is-live" : ""}`} />
                    <span className="landing-cat-tag">{getMarketDiscoveryCategory(market)}</span>
                  </div>
                  <div className="landing-feat-title-row">
                    <MarketIcon market={market} size={42} />
                    <h3 className="landing-feat-title">{market.title}</h3>
                  </div>
                  <div className="landing-prob-bar">
                    <div className="landing-prob-fill" style={{ width: `${yes ?? 50}%` }} />
                  </div>
                  <LandingMiniSparkline slug={market.slug} outcomeId={market.outcomes[0]?.id} />
                  <div className="landing-feat-odds">
                    <span className="landing-yes-label">YES {yes !== null ? `${yes}%` : "—"}</span>
                    <span className="landing-no-label">NO {no !== null ? `${no}%` : "—"}</span>
                  </div>
                  <div className="landing-feat-meta">
                    <span>{formatVolume(market.traded_volume)}</span>
                    {countdown && <span>{countdown} left</span>}
                    {market.community_name && <span>{market.community_name}</span>}
                  </div>
                </Link>
              );
            })}
          </div>
        </section>
      )}

      {/* ── Market grid ──────────────────────────────── */}
      <section className="landing-section">
        <div className="landing-section-head">
          <span className="eyebrow">Open markets</span>
          <Link className="landing-view-all" href="/markets">View all →</Link>
        </div>

        {isLoading ? (
          <div className="landing-grid">
            {Array.from({ length: 6 }).map((_, i) => (
              <div className="landing-card-skeleton" key={i} />
            ))}
          </div>
        ) : filteredMarkets.length === 0 ? (
          <p className="landing-empty">No open markets in this category yet.</p>
        ) : (
          <div className="landing-grid">
            {filteredMarkets.map((market) => {
              const yes = formatPrice(market.last_price);
              const no = yes !== null ? 100 - yes : null;
              const countdown = formatCountdown(market.timing.trading_closes_at);
              return (
                <Link className="landing-card" href={`/markets/${market.slug}`} key={market.id}>
                  <div className="landing-card-top">
                    <span className="landing-cat-tag">{getMarketDiscoveryCategory(market)}</span>
                    {market.status === "open" && (
                      <span className="landing-live-badge">Live</span>
                    )}
                  </div>
                  <div className="landing-card-title-row">
                    <MarketIcon market={market} size={36} />
                    <h3 className="landing-card-title">{market.title}</h3>
                  </div>
                  <div className="landing-prob-bar">
                    <div className="landing-prob-fill" style={{ width: `${yes ?? 50}%` }} />
                  </div>
                  <LandingMiniSparkline slug={market.slug} outcomeId={market.outcomes[0]?.id} />
                  <div className="landing-card-odds">
                    <span className="landing-yes-label">YES {yes !== null ? `${yes}%` : "—"}</span>
                    <span className="landing-no-label">NO {no !== null ? `${no}%` : "—"}</span>
                  </div>
                  <div className="landing-card-meta">
                    <span>{formatVolume(market.traded_volume)} vol</span>
                    {countdown && <span>{countdown} left</span>}
                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </section>

      {/* ── Communities ──────────────────────────────── */}
      {communityHighlights.length > 0 && (
        <section className="landing-section">
          <div className="landing-section-head">
            <span className="eyebrow">Communities</span>
            <Link className="landing-view-all" href="/communities">Browse all →</Link>
          </div>
          <div className="landing-community-strip">
            {communityHighlights.map((c) => (
              <Link className="landing-community-pill" href={c.href} key={c.href}>
                {c.label}
              </Link>
            ))}
            <Link className="landing-community-pill landing-community-pill-ghost" href="/market-requests">
              + Propose a market
            </Link>
          </div>
        </section>
      )}

      {/* ── Footer CTA ───────────────────────────────── */}
      <section className="landing-footer-cta">
        <h2>Ready to call it?</h2>
        <p>Join the platform where your predictions pay off.</p>
        <div className="landing-ctas">
          <Link className="landing-cta-primary" href={user ? "/markets" : "/auth/sign-up"}>
            {user ? "Browse markets" : "Create free account"}
          </Link>
          <Link className="landing-cta-secondary" href="/market-requests">
            Propose a market
          </Link>
        </div>
        <p className="landing-about-teaser">
          New here?{" "}
          <Link href="/about" className="landing-about-link">
            About Satta
          </Link>{" "}
          — how bets work, <strong>2% taker / 0% maker</strong> fees, and creator rewards when markets hit volume
          milestones.
        </p>
      </section>

    </main>
  );
};
