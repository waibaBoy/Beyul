"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AuthFeedback } from "@/components/auth/auth-feedback";
import { useAuthAction } from "@/components/auth/use-auth-action";
import { beyulApiFetch } from "@/lib/api/beyul-api";
import type { Market } from "@/lib/api/types";

export const MarketsWorkspace = () => {
  const [markets, setMarkets] = useState<Market[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const { errorMessage, setStatusMessage, statusMessage } = useAuthAction(
    "Load converted canonical markets from the live backend."
  );

  useEffect(() => {
    let isMounted = true;

    const loadMarkets = async () => {
      try {
        const nextMarkets = await beyulApiFetch<Market[]>("/api/v1/markets");
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

      {isLoading ? (
        <p>Loading markets...</p>
      ) : markets.length === 0 ? (
        <p>No published markets yet.</p>
      ) : (
        <div className="entity-list">
          {markets.map((market) => (
            <article className="entity-card" key={market.id}>
              <div className="entity-card-header">
                <strong>{market.title}</strong>
                <span className="pill">{market.status}</span>
              </div>
              <p>{market.question}</p>
              <dl className="kv-list compact">
                <div>
                  <dt>Slug</dt>
                  <dd>{market.slug}</dd>
                </div>
                <div>
                  <dt>Rail</dt>
                  <dd>{market.rail_mode}</dd>
                </div>
                <div>
                  <dt>Outcomes</dt>
                  <dd>{market.outcomes.map((outcome) => outcome.label).join(", ")}</dd>
                </div>
              </dl>
              <div className="button-row">
                <Link className="button-secondary hero-link" href={`/markets/${market.slug}`}>
                  Open market
                </Link>
              </div>
            </article>
          ))}
        </div>
      )}

      <AuthFeedback errorMessage={errorMessage} statusMessage={statusMessage} />
    </section>
  );
};
