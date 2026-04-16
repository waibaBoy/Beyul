"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AuthFeedback } from "@/components/auth/auth-feedback";
import { useAuthAction } from "@/components/auth/use-auth-action";
import { MarketIcon } from "@/components/app/market-icon";
import { beyulApiFetch } from "@/lib/api/beyul-api";
import type { Market } from "@/lib/api/types";

const formatVolume = (value: string) => {
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed <= 0) return "—";
  if (parsed >= 1_000_000) return `$${(parsed / 1_000_000).toFixed(1)}M`;
  if (parsed >= 1_000) return `$${Math.round(parsed / 1_000)}k`;
  return `$${Math.round(parsed)}`;
};

const formatPricePercent = (value: string | null): string => {
  if (!value) return "—";
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return "—";
  return `${Math.round(parsed * 100)}%`;
};

const formatCountdown = (value: string | null): string | null => {
  if (!value) return null;
  const diffMs = new Date(value).getTime() - Date.now();
  if (!Number.isFinite(diffMs) || diffMs <= 0) return null;
  const totalMinutes = Math.floor(diffMs / 60000);
  const days = Math.floor(totalMinutes / (60 * 24));
  const hours = Math.floor((totalMinutes % (60 * 24)) / 60);
  if (days > 0) return `${days}d left`;
  if (hours > 0) return `${hours}h left`;
  return `${totalMinutes}m left`;
};

export const MarketsWorkspace = () => {
  const [markets, setMarkets] = useState<Market[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedCommunityFilter, setSelectedCommunityFilter] = useState("all");
  const { errorMessage, setStatusMessage, statusMessage } = useAuthAction(
    "Load converted canonical markets from the live backend."
  );

  const communityFilters = Array.from(
    new Set(markets.map((market) => market.community_name).filter((value): value is string => Boolean(value)))
  );
  const filteredMarkets = markets.filter((market) => {
    if (selectedCommunityFilter === "all") {
      return true;
    }
    if (selectedCommunityFilter === "standalone") {
      return !market.community_name;
    }
    return market.community_name === selectedCommunityFilter;
  });
  const featuredMarket = filteredMarkets[0] ?? null;
  const remainingMarkets = featuredMarket ? filteredMarkets.slice(1) : [];

  useEffect(() => {
    let isMounted = true;

    const loadMarkets = async () => {
      try {
        const nextMarkets = await beyulApiFetch<Market[]>("/api/v1/markets?limit=50");
        if (isMounted) {
          setMarkets(nextMarkets);
          setStatusMessage(`Loaded ${nextMarkets.length} published markets.`);
        }
      } catch (error) {
        if (isMounted) {
          setStatusMessage(error instanceof Error ? error.message : "Failed to load markets.");
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    void loadMarkets();

    return () => {
      isMounted = false;
    };
  }, [setStatusMessage]);

  return (
    <section className="auth-section">
      <h2>Published markets</h2>
      <p>These are the canonical market rows created from approved market requests.</p>
      <div className="markets-toolbar">
        <div className="markets-filter-bar" aria-label="Market communities">
          <button
            className={`market-filter-pill ${selectedCommunityFilter === "all" ? "is-active" : ""}`}
            onClick={() => setSelectedCommunityFilter("all")}
            type="button"
          >
            All markets
          </button>
          {communityFilters.map((communityName) => (
            <button
              className={`market-filter-pill ${selectedCommunityFilter === communityName ? "is-active" : ""}`}
              key={communityName}
              onClick={() => setSelectedCommunityFilter(communityName)}
              type="button"
            >
              {communityName}
            </button>
          ))}
          {markets.some((market) => !market.community_name) ? (
            <button
              className={`market-filter-pill ${selectedCommunityFilter === "standalone" ? "is-active" : ""}`}
              onClick={() => setSelectedCommunityFilter("standalone")}
              type="button"
            >
              Standalone
            </button>
          ) : null}
        </div>
        <span className="pill">{filteredMarkets.length} shown</span>
      </div>

      {isLoading ? (
        <p>Loading markets...</p>
      ) : markets.length === 0 ? (
        <p>No published markets yet.</p>
      ) : filteredMarkets.length === 0 ? (
        <p>No published markets for this community filter yet.</p>
      ) : (
        <div className="markets-layout">
          {featuredMarket ? (
            <article className="entity-card market-feature-card">
              <div className="market-feature-head">
                <div className="market-feature-label">
                  <MarketIcon market={featuredMarket} size={52} />
                  <div>
                    <p className="market-feature-kicker">Featured market</p>
                    <strong>{featuredMarket.title}</strong>
                  </div>
                </div>
                <span className="pill">{featuredMarket.status}</span>
              </div>
              <p>{featuredMarket.question}</p>
              <div className="market-summary-meta">
                <span className="market-meta-chip">{featuredMarket.community_name || "Standalone"}</span>
                <span className="market-meta-chip">{featuredMarket.rail_mode}</span>
                <span className="market-meta-chip">{featuredMarket.resolution_mode}</span>
              </div>
              <div className="market-signal-strip">
                <div className="market-signal-item">
                  <span>Yes price</span>
                  <strong>{formatPricePercent(featuredMarket.last_price)}</strong>
                </div>
                <div className="market-signal-item">
                  <span>Volume</span>
                  <strong>{formatVolume(featuredMarket.traded_volume)}</strong>
                </div>
                <div className="market-signal-item">
                  <span>Closes</span>
                  <strong>{formatCountdown(featuredMarket.timing.trading_closes_at) ?? "Open"}</strong>
                </div>
              </div>
              <dl className="kv-list compact market-feature-kv">
                <div>
                  <dt>Slug</dt>
                  <dd>{featuredMarket.slug}</dd>
                </div>
                <div>
                  <dt>Outcomes</dt>
                  <dd>{featuredMarket.outcomes.map((outcome) => outcome.label).join(", ")}</dd>
                </div>
                <div>
                  <dt>Access</dt>
                  <dd>{featuredMarket.market_access_mode}</dd>
                </div>
              </dl>
              <div className="button-row">
                <Link className="button-primary hero-link" href={`/markets/${featuredMarket.slug}`}>
                  Open market
                </Link>
              </div>
            </article>
          ) : null}

          <div className="markets-rows">
            {remainingMarkets.map((market) => (
              <article className="entity-card market-row-card" key={market.id}>
                <div className="market-row-main">
                  <div className="market-row-head">
                    <div className="market-row-title-wrap">
                      <MarketIcon market={market} size={42} />
                      <strong>{market.title}</strong>
                    </div>
                    <span className="pill">{market.status}</span>
                  </div>
                  <p>{market.question}</p>
                  <div className="market-summary-meta">
                    <span className="market-meta-chip">{market.community_name || "Standalone"}</span>
                    <span className="market-meta-chip">{market.rail_mode}</span>
                    <span className="market-meta-chip">{formatPricePercent(market.last_price)} YES</span>
                  </div>
                </div>
                <dl className="kv-list compact market-row-kv">
                  <div>
                    <dt>Slug</dt>
                    <dd>{market.slug}</dd>
                  </div>
                  <div>
                    <dt>Outcomes</dt>
                    <dd>{market.outcomes.map((outcome) => outcome.label).join(", ")}</dd>
                  </div>
                  <div>
                    <dt>Volume</dt>
                    <dd>{formatVolume(market.traded_volume)}</dd>
                  </div>
                </dl>
                <div className="button-row market-row-actions">
                  <Link className="button-secondary hero-link" href={`/markets/${market.slug}`}>
                    Open market
                  </Link>
                </div>
              </article>
            ))}
          </div>
        </div>
      )}

      <AuthFeedback errorMessage={errorMessage} statusMessage={statusMessage} />
    </section>
  );
};
