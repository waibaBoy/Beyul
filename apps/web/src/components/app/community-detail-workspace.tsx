"use client";

import { useEffect, useState } from "react";
import { AuthFeedback } from "@/components/auth/auth-feedback";
import { useAuth } from "@/components/auth/auth-provider";
import { useAuthAction } from "@/components/auth/use-auth-action";
import { beyulApiFetch } from "@/lib/api/beyul-api";
import type { Community, CommunityMember, Post } from "@/lib/api/types";

type CommunityDetailWorkspaceProps = {
  slug: string;
};

const defaultPostForm = {
  title: "",
  body: ""
};

export const CommunityDetailWorkspace = ({ slug }: CommunityDetailWorkspaceProps) => {
  const { getAccessToken, session } = useAuth();
  const [community, setCommunity] = useState<Community | null>(null);
  const [members, setMembers] = useState<CommunityMember[]>([]);
  const [posts, setPosts] = useState<Post[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [form, setForm] = useState(defaultPostForm);
  const { errorMessage, isSubmitting, runAction, setStatusMessage, statusMessage } = useAuthAction(
    "Load the community profile, members, and moderated posts."
  );

  useEffect(() => {
    let isMounted = true;

    const loadCommunity = async () => {
      if (!session) {
        if (isMounted) {
          setCommunity(null);
          setMembers([]);
          setPosts([]);
          setIsLoading(false);
        }
        return;
      }

      try {
        const accessToken = await getAccessToken();
        const [nextCommunity, nextMembers, nextPosts] = await Promise.all([
          beyulApiFetch<Community>(`/api/v1/communities/${slug}`, { accessToken }),
          beyulApiFetch<CommunityMember[]>(`/api/v1/communities/${slug}/members`, { accessToken }),
          beyulApiFetch<Post[]>(`/api/v1/communities/${slug}/posts`, { accessToken })
        ]);

        if (isMounted) {
          setCommunity(nextCommunity);
          setMembers(nextMembers);
          setPosts(nextPosts);
          setStatusMessage(`Loaded ${nextPosts.length} posts and ${nextMembers.length} members.`);
        }
      } catch (error) {
        if (isMounted) {
          setStatusMessage(error instanceof Error ? error.message : "Failed to load community details.");
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    void loadCommunity();

    return () => {
      isMounted = false;
    };
  }, [getAccessToken, session, setStatusMessage, slug]);

  return (
    <>
      <section className="auth-section">
        <h2>Community detail</h2>
        <p>Use this page as the social feed and moderation entry point for a single community.</p>

        {isLoading ? (
          <p>Loading community...</p>
        ) : community ? (
          <dl className="kv-list">
            <div>
              <dt>Name</dt>
              <dd>{community.name}</dd>
            </div>
            <div>
              <dt>Visibility</dt>
              <dd>{community.visibility}</dd>
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
        ) : (
          <p>Community not found or not accessible.</p>
        )}
      </section>

      <section className="auth-section">
        <h2>Create social post</h2>
        <p>
          New posts follow the live moderation rules. In approval-required communities they will enter
          the admin queue automatically.
        </p>

        <form
          className="auth-form"
          onSubmit={(event) => {
            event.preventDefault();
            void runAction(
              "Publishing post...",
              async () => {
                const accessToken = await getAccessToken();
                const created = await beyulApiFetch<Post>(`/api/v1/communities/${slug}/posts`, {
                  method: "POST",
                  accessToken,
                  json: {
                    title: form.title || undefined,
                    body: form.body
                  }
                });
                setPosts((current) => [created, ...current]);
                setForm(defaultPostForm);
                return created;
              },
              {
                successMessage: (created) => `Post created with ${created.status} status.`
              }
            );
          }}
        >
          <div className="field">
            <label htmlFor="post-title">Title</label>
            <input
              id="post-title"
              placeholder="Weekly market briefing"
              value={form.title}
              onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))}
            />
          </div>
          <div className="field">
            <label htmlFor="post-body">Body</label>
            <textarea
              id="post-body"
              placeholder="Summarise the event, source, or context before asking the community to trade on it."
              rows={5}
              value={form.body}
              onChange={(event) => setForm((current) => ({ ...current, body: event.target.value }))}
            />
          </div>
          <div className="button-row">
            <button className="button-primary" disabled={isSubmitting || !session || !community} type="submit">
              Publish post
            </button>
          </div>
        </form>

        <AuthFeedback errorMessage={errorMessage} statusMessage={statusMessage} />
      </section>

      <section className="auth-section">
        <h2>Members</h2>
        {isLoading ? (
          <p>Loading members...</p>
        ) : members.length === 0 ? (
          <p>No members found yet.</p>
        ) : (
          <div className="entity-list">
            {members.map((member) => (
              <article className="entity-card" key={member.id}>
                <div className="entity-card-header">
                  <strong>{member.display_name}</strong>
                  <span className="pill">{member.role}</span>
                </div>
                <p>@{member.username}</p>
              </article>
            ))}
          </div>
        )}
      </section>

      <section className="auth-section">
        <h2>Community feed</h2>
        {isLoading ? (
          <p>Loading posts...</p>
        ) : posts.length === 0 ? (
          <p>No posts in this community yet.</p>
        ) : (
          <div className="entity-list">
            {posts.map((post) => (
              <article className="entity-card" key={post.id}>
                <div className="entity-card-header">
                  <strong>{post.title || "Untitled post"}</strong>
                  <span className="pill">{post.status}</span>
                </div>
                <p>{post.body}</p>
                <dl className="kv-list compact">
                  <div>
                    <dt>Author</dt>
                    <dd>{post.author_display_name}</dd>
                  </div>
                  <div>
                    <dt>Submitted</dt>
                    <dd>{post.submitted_at ? new Date(post.submitted_at).toLocaleString() : "Not submitted"}</dd>
                  </div>
                  <div>
                    <dt>Review notes</dt>
                    <dd>{post.review_notes || "None"}</dd>
                  </div>
                </dl>
              </article>
            ))}
          </div>
        )}
      </section>
    </>
  );
};
