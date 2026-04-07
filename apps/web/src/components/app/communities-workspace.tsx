"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { beyulApiFetch } from "@/lib/api/beyul-api";
import type { Community, CommunityCreateInput } from "@/lib/api/types";
import { normalizeSlug } from "@/lib/slug";
import { useAuth } from "@/components/auth/auth-provider";
import { AuthFeedback } from "@/components/auth/auth-feedback";
import { useAuthAction } from "@/components/auth/use-auth-action";

const defaultCommunityForm: CommunityCreateInput = {
  slug: "",
  name: "",
  description: "",
  visibility: "public",
  require_post_approval: true,
  require_market_approval: true
};

export const CommunitiesWorkspace = () => {
  const { getAccessToken, session } = useAuth();
  const [communities, setCommunities] = useState<Community[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [form, setForm] = useState(defaultCommunityForm);
  const { errorMessage, isSubmitting, runAction, statusMessage, setStatusMessage } = useAuthAction(
    "Load and create communities using the authenticated FastAPI endpoints."
  );

  useEffect(() => {
    let isMounted = true;

    const loadCommunities = async () => {
      if (!session) {
        if (isMounted) {
          setCommunities([]);
          setIsLoading(false);
        }
        return;
      }

      try {
        const accessToken = await getAccessToken();
        const nextCommunities = await beyulApiFetch<Community[]>("/api/v1/communities", {
          accessToken
        });

        if (isMounted) {
          setCommunities(nextCommunities);
          setStatusMessage(`Loaded ${nextCommunities.length} communities from FastAPI.`);
        }
      } catch (error) {
        if (isMounted) {
          setStatusMessage(error instanceof Error ? error.message : "Failed to load communities.");
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    void loadCommunities();

    return () => {
      isMounted = false;
    };
  }, [getAccessToken, session, setStatusMessage]);

  return (
    <>
      <section className="auth-section">
        <h2>Create community</h2>
        <p>Create public or private communities against the live backend using the current authenticated session.</p>

        <form
          className="auth-form"
          onSubmit={(event) => {
            event.preventDefault();
            void runAction(
              "Creating community...",
              async () => {
                const accessToken = await getAccessToken();
                const created = await beyulApiFetch<Community>("/api/v1/communities", {
                  method: "POST",
                  accessToken,
                  json: {
                    ...form,
                    slug: normalizeSlug(form.slug),
                    description: form.description || undefined
                  }
                });
                setCommunities((current) => [created, ...current]);
                setForm(defaultCommunityForm);
                return created;
              },
              {
                successMessage: (created) => `Created community ${created.slug}.`
              }
            );
          }}
        >
          <div className="field">
            <label htmlFor="community-name">Name</label>
            <input
              id="community-name"
              placeholder="Aussie Politics"
              value={form.name}
              onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
            />
          </div>
          <div className="field">
            <label htmlFor="community-slug">Slug</label>
            <input
              id="community-slug"
              placeholder="aussie-politics"
              value={form.slug}
              onChange={(event) =>
                setForm((current) => ({ ...current, slug: normalizeSlug(event.target.value) }))
              }
            />
          </div>
          <div className="field">
            <label htmlFor="community-description">Description</label>
            <input
              id="community-description"
              placeholder="Public event and policy markets."
              value={form.description}
              onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))}
            />
          </div>
          <div className="field">
            <label htmlFor="community-visibility">Visibility</label>
            <select
              id="community-visibility"
              className="select-field"
              value={form.visibility}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  visibility: event.target.value as CommunityCreateInput["visibility"]
                }))
              }
            >
              <option value="public">Public</option>
              <option value="private">Private</option>
            </select>
          </div>
          <div className="checkbox-stack">
            <label className="checkbox-field">
              <input
                checked={form.require_post_approval}
                type="checkbox"
                onChange={(event) =>
                  setForm((current) => ({ ...current, require_post_approval: event.target.checked }))
                }
              />
              Require post approval
            </label>
            <label className="checkbox-field">
              <input
                checked={form.require_market_approval}
                type="checkbox"
                onChange={(event) =>
                  setForm((current) => ({ ...current, require_market_approval: event.target.checked }))
                }
              />
              Require market approval
            </label>
          </div>
          <div className="button-row">
            <button className="button-primary" disabled={isSubmitting || !session} type="submit">
              Create community
            </button>
          </div>
        </form>

        <AuthFeedback errorMessage={errorMessage} statusMessage={statusMessage} />
      </section>

      <section className="auth-section">
        <h2>Community list</h2>
        <p>These rows are loaded from the FastAPI community list endpoint using your current bearer token.</p>

        {isLoading ? (
          <p>Loading communities...</p>
        ) : communities.length === 0 ? (
          <p>No communities found yet.</p>
        ) : (
          <div className="entity-list">
            {communities.map((community) => (
              <article className="entity-card" key={community.id}>
                <div className="entity-card-header">
                  <strong>{community.name}</strong>
                  <span className="pill">{community.visibility}</span>
                </div>
                <p>{community.description || "No description yet."}</p>
                <dl className="kv-list compact">
                  <div>
                    <dt>Slug</dt>
                    <dd>{community.slug}</dd>
                  </div>
                  <div>
                    <dt>Post approval</dt>
                    <dd>{community.require_post_approval ? "Required" : "Open"}</dd>
                  </div>
                  <div>
                    <dt>Market approval</dt>
                    <dd>{community.require_market_approval ? "Required" : "Open"}</dd>
                  </div>
                </dl>
                <div className="button-row">
                  <Link className="button-secondary hero-link" href={`/communities/${community.slug}`}>
                    Open community
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
