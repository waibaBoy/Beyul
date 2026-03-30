"use client";

import { useEffect, useState } from "react";
import { AuthFeedback } from "@/components/auth/auth-feedback";
import { useAuthAction } from "@/components/auth/use-auth-action";
import { beyulApiFetch } from "@/lib/api/beyul-api";
import type { Market } from "@/lib/api/types";

type MarketDetailWorkspaceProps = {
  slug: string;
};

export const MarketDetailWorkspace = ({ slug }: MarketDetailWorkspaceProps) => {
  const [market, setMarket] = useState<Market | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const { errorMessage, setStatusMessage, statusMessage } = useAuthAction(
    "Load the canonical published market details."
  );

  useEffect(() => {
    let isMounted = true;

    const loadMarket = async () => {
      try {
        const nextMarket = await beyulApiFetch<Market>(`/api/v1/markets/${slug}`);
        if (isMounted) {
          setMarket(nextMarket);
          setStatusMessage(`Loaded market ${nextMarket.slug}.`);
        }
      } catch (error) {
        if (isMounted) {
          setStatusMessage(error instanceof Error ? error.message : "Failed to load market.");
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    void loadMarket();

    return () => {
      isMounted = false;
    };
  }, [setStatusMessage, slug]);

  return (
    <section className="auth-section">
      <h2>Market detail</h2>
      {isLoading ? (
        <p>Loading market...</p>
      ) : market ? (
        <>
          <dl className="kv-list">
            <div>
              <dt>Title</dt>
              <dd>{market.title}</dd>
            </div>
            <div>
              <dt>Status</dt>
              <dd>{market.status}</dd>
            </div>
            <div>
              <dt>Rail</dt>
              <dd>{market.rail_mode}</dd>
            </div>
            <div>
              <dt>Community</dt>
              <dd>{market.community_name || "Standalone"}</dd>
            </div>
          </dl>
          <p>{market.question}</p>
          <pre className="code-block">{market.rules_text}</pre>
          <div className="entity-list">
            {market.outcomes.map((outcome) => (
              <article className="entity-card" key={outcome.id}>
                <div className="entity-card-header">
                  <strong>{outcome.label}</strong>
                  <span className="pill">{outcome.status}</span>
                </div>
                <p>Code: {outcome.code}</p>
              </article>
            ))}
          </div>
        </>
      ) : (
        <p>Market not found.</p>
      )}

      <AuthFeedback errorMessage={errorMessage} statusMessage={statusMessage} />
    </section>
  );
};
