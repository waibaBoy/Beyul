"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { beyulApiFetch } from "@/lib/api/beyul-api";
import type { Community, MarketRequest, MarketRequestCreateInput } from "@/lib/api/types";
import { useAuth } from "@/components/auth/auth-provider";
import { AuthFeedback } from "@/components/auth/auth-feedback";
import { useAuthAction } from "@/components/auth/use-auth-action";

const defaultRequestForm: MarketRequestCreateInput = {
  title: "",
  slug: "",
  question: "",
  description: "",
  market_access_mode: "public",
  requested_rail: "onchain",
  resolution_mode: "oracle",
  community_id: ""
};

export const MarketRequestsWorkspace = () => {
  const { getAccessToken, session } = useAuth();
  const [requests, setRequests] = useState<MarketRequest[]>([]);
  const [communities, setCommunities] = useState<Community[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [form, setForm] = useState(defaultRequestForm);
  const { errorMessage, isSubmitting, runAction, statusMessage, setStatusMessage } = useAuthAction(
    "Create and review your live market requests."
  );

  useEffect(() => {
    let isMounted = true;

    const loadData = async () => {
      if (!session) {
        if (isMounted) {
          setRequests([]);
          setCommunities([]);
          setIsLoading(false);
        }
        return;
      }

      try {
        const accessToken = await getAccessToken();
        const [nextRequests, nextCommunities] = await Promise.all([
          beyulApiFetch<MarketRequest[]>("/api/v1/market-requests/me", {
            accessToken
          }),
          beyulApiFetch<Community[]>("/api/v1/communities", {
            accessToken
          })
        ]);

        if (isMounted) {
          setRequests(nextRequests);
          setCommunities(nextCommunities);
          setStatusMessage(`Loaded ${nextRequests.length} market requests from FastAPI.`);
        }
      } catch (error) {
        if (isMounted) {
          setStatusMessage(error instanceof Error ? error.message : "Failed to load market requests.");
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    void loadData();

    return () => {
      isMounted = false;
    };
  }, [getAccessToken, session, setStatusMessage]);

  return (
    <>
      <section className="auth-section">
        <h2>Create market request</h2>
        <p>Submit the market intake details you already modeled in Postgres and FastAPI.</p>

        <form
          className="auth-form"
          onSubmit={(event) => {
            event.preventDefault();
            void runAction(
              "Creating market request...",
              async () => {
                const accessToken = await getAccessToken();
                const created = await beyulApiFetch<MarketRequest>("/api/v1/market-requests", {
                  method: "POST",
                  accessToken,
                  json: {
                    ...form,
                    slug: form.slug || undefined,
                    description: form.description || undefined,
                    community_id: form.community_id || undefined
                  }
                });
                setRequests((current) => [created, ...current]);
                setForm(defaultRequestForm);
                return created;
              },
              {
                successMessage: (created) => `Created market request ${created.slug ?? created.id}.`
              }
            );
          }}
        >
          <div className="field">
            <label htmlFor="request-title">Title</label>
            <input
              id="request-title"
              placeholder="Will BTC close above $100k this quarter?"
              value={form.title}
              onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))}
            />
          </div>
          <div className="field">
            <label htmlFor="request-slug">Slug</label>
            <input
              id="request-slug"
              placeholder="btc-above-100k-q4"
              value={form.slug}
              onChange={(event) => setForm((current) => ({ ...current, slug: event.target.value }))}
            />
          </div>
          <div className="field">
            <label htmlFor="request-question">Question</label>
            <input
              id="request-question"
              placeholder="Will BTC close above $100k by quarter end?"
              value={form.question}
              onChange={(event) => setForm((current) => ({ ...current, question: event.target.value }))}
            />
          </div>
          <div className="field">
            <label htmlFor="request-description">Description</label>
            <input
              id="request-description"
              placeholder="Settlement will use an official public source."
              value={form.description}
              onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))}
            />
          </div>
          <div className="field">
            <label htmlFor="request-community">Community</label>
            <select
              id="request-community"
              className="select-field"
              value={form.community_id}
              onChange={(event) => setForm((current) => ({ ...current, community_id: event.target.value }))}
            >
              <option value="">No community</option>
              {communities.map((community) => (
                <option key={community.id} value={community.id}>
                  {community.name}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="request-access-mode">Access mode</label>
            <select
              id="request-access-mode"
              className="select-field"
              value={form.market_access_mode}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  market_access_mode: event.target.value as MarketRequestCreateInput["market_access_mode"]
                }))
              }
            >
              <option value="public">Public</option>
              <option value="private_group">Private group</option>
            </select>
          </div>
          <div className="field">
            <label htmlFor="request-rail">Requested rail</label>
            <select
              id="request-rail"
              className="select-field"
              value={form.requested_rail}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  requested_rail: event.target.value as MarketRequestCreateInput["requested_rail"]
                }))
              }
            >
              <option value="onchain">Onchain</option>
              <option value="custodial">Custodial</option>
            </select>
          </div>
          <div className="field">
            <label htmlFor="request-resolution">Resolution mode</label>
            <select
              id="request-resolution"
              className="select-field"
              value={form.resolution_mode}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  resolution_mode: event.target.value as MarketRequestCreateInput["resolution_mode"]
                }))
              }
            >
              <option value="oracle">Oracle</option>
              <option value="api">API</option>
              <option value="council">Council</option>
            </select>
          </div>
          <div className="button-row">
            <button className="button-primary" disabled={isSubmitting || !session} type="submit">
              Create market request
            </button>
          </div>
        </form>

        <AuthFeedback errorMessage={errorMessage} statusMessage={statusMessage} />
      </section>

      <section className="auth-section">
        <h2>Your market requests</h2>
        <p>Each request here is loaded from the live `/api/v1/market-requests/me` endpoint.</p>

        {isLoading ? (
          <p>Loading market requests...</p>
        ) : requests.length === 0 ? (
          <p>No market requests found yet.</p>
        ) : (
          <div className="entity-list">
            {requests.map((request) => (
              <article className="entity-card" key={request.id}>
                <div className="entity-card-header">
                  <strong>{request.title}</strong>
                  <span className="pill">{request.status}</span>
                </div>
                <p>{request.question}</p>
                <dl className="kv-list compact">
                  <div>
                    <dt>Slug</dt>
                    <dd>{request.slug ?? "Not set"}</dd>
                  </div>
                  <div>
                    <dt>Rail</dt>
                    <dd>{request.requested_rail ?? "Unset"}</dd>
                  </div>
                  <div>
                    <dt>Access mode</dt>
                    <dd>{request.market_access_mode}</dd>
                  </div>
                  <div>
                    <dt>Resolution</dt>
                    <dd>{request.resolution_mode}</dd>
                  </div>
                </dl>
                <div className="button-row">
                  <Link className="button-secondary hero-link" href={`/market-requests/${request.id}`}>
                    Open detail
                  </Link>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </>
  );
};
