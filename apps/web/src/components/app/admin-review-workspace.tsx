"use client";

import { useEffect, useState } from "react";
import { AuthFeedback } from "@/components/auth/auth-feedback";
import { useAuth } from "@/components/auth/auth-provider";
import { useAuthAction } from "@/components/auth/use-auth-action";
import { beyulApiFetch } from "@/lib/api/beyul-api";
import type {
  BackendUser,
  Market,
  MarketRequest,
  OracleApproval,
  OracleLiveReadiness,
  Post,
  ReviewQueue
} from "@/lib/api/types";

export const AdminReviewWorkspace = () => {
  const { getAccessToken, session } = useAuth();
  const [backendUser, setBackendUser] = useState<BackendUser | null>(null);
  const [queue, setQueue] = useState<ReviewQueue>({ pending_posts: [], pending_market_requests: [] });
  const [oracleReadiness, setOracleReadiness] = useState<OracleLiveReadiness | null>(null);
  const [approvalAmount, setApprovalAmount] = useState("");
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [isLoading, setIsLoading] = useState(true);
  const { errorMessage, isSubmitting, runAction, setStatusMessage, statusMessage } = useAuthAction(
    "Load the central admin review queue for posts and market requests."
  );

  const loadAdminQueue = async () => {
    if (!session) {
      setBackendUser(null);
      setQueue({ pending_posts: [], pending_market_requests: [] });
      setOracleReadiness(null);
      return;
    }

    const accessToken = await getAccessToken();
    const nextUser = await beyulApiFetch<BackendUser>("/api/v1/auth/me", { accessToken });
    if (!nextUser.is_admin) {
      setBackendUser(nextUser);
      setQueue({ pending_posts: [], pending_market_requests: [] });
      setOracleReadiness(null);
      setStatusMessage("This account is authenticated but does not have admin review access.");
      return;
    }

    const [nextQueue, nextReadiness] = await Promise.all([
      beyulApiFetch<ReviewQueue>("/api/v1/admin/review-queue", { accessToken }),
      beyulApiFetch<OracleLiveReadiness>("/api/v1/admin/oracle/live-readiness", { accessToken })
    ]);
    setBackendUser(nextUser);
    setQueue(nextQueue);
    setOracleReadiness(nextReadiness);
    setApprovalAmount(nextReadiness.required_bond_wei);
    setStatusMessage(
      `Loaded ${nextQueue.pending_posts.length} pending posts and ${nextQueue.pending_market_requests.length} pending market requests.`
    );
  };

  useEffect(() => {
    let isMounted = true;

    void (async () => {
      try {
        await loadAdminQueue();
      } catch (error) {
        if (isMounted) {
          setStatusMessage(error instanceof Error ? error.message : "Failed to load the admin review queue.");
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    })();

    return () => {
      isMounted = false;
    };
  }, [getAccessToken, session, setStatusMessage]);

  return (
    <>
      <section className="auth-section">
        <h2>Admin status</h2>
        {isLoading ? (
          <p>Checking admin access...</p>
        ) : backendUser ? (
          <>
            <dl className="kv-list">
              <div>
                <dt>Username</dt>
                <dd>{backendUser.username}</dd>
              </div>
              <div>
                <dt>Admin access</dt>
                <dd>{backendUser.is_admin ? "Granted" : "Denied"}</dd>
              </div>
            </dl>
            {backendUser.is_admin ? (
              <div className="button-row">
                <button
                  className="button-secondary"
                  disabled={isSubmitting}
                  type="button"
                  onClick={() =>
                    void runAction(
                      "Refreshing admin queue...",
                      async () => {
                        await loadAdminQueue();
                        return true;
                      },
                      {
                        successMessage: "Admin queue refreshed."
                      }
                    )
                  }
                >
                  Refresh queue
                </button>
              </div>
            ) : null}
          </>
        ) : (
          <p>Sign in to access the review queue.</p>
        )}
      </section>

      <section className="auth-section">
        <h2>Pending social posts</h2>
        {isLoading ? (
          <p>Loading pending posts...</p>
        ) : !backendUser?.is_admin ? (
          <p>Only admin accounts can review posts.</p>
        ) : queue.pending_posts.length === 0 ? (
          <p>No pending posts right now.</p>
        ) : (
          <div className="entity-list">
            {queue.pending_posts.map((post) => (
              <article className="entity-card" key={post.id}>
                <div className="entity-card-header">
                  <strong>{post.title || "Untitled post"}</strong>
                  <span className="pill">{post.community_name}</span>
                </div>
                <p>{post.body}</p>
                <div className="field">
                  <label htmlFor={`post-note-${post.id}`}>Review notes</label>
                  <textarea
                    id={`post-note-${post.id}`}
                    rows={3}
                    value={notes[post.id] || ""}
                    onChange={(event) => setNotes((current) => ({ ...current, [post.id]: event.target.value }))}
                  />
                </div>
                <div className="button-row">
                  <button
                    className="button-primary"
                    disabled={isSubmitting}
                    type="button"
                    onClick={() =>
                      void runAction(
                        "Approving post...",
                        async () => {
                          const accessToken = await getAccessToken();
                          const approved = await beyulApiFetch<Post>(`/api/v1/posts/${post.id}/approve`, {
                            method: "POST",
                            accessToken,
                            json: { review_notes: notes[post.id] || undefined }
                          });
                          setQueue((current) => ({
                            ...current,
                            pending_posts: current.pending_posts.filter((item) => item.id !== post.id)
                          }));
                          return approved;
                        },
                        {
                          successMessage: "Post approved."
                        }
                      )
                    }
                  >
                    Approve
                  </button>
                  <button
                    className="button-secondary"
                    disabled={isSubmitting}
                    type="button"
                    onClick={() =>
                      void runAction(
                        "Rejecting post...",
                        async () => {
                          const accessToken = await getAccessToken();
                          const rejected = await beyulApiFetch<Post>(`/api/v1/posts/${post.id}/reject`, {
                            method: "POST",
                            accessToken,
                            json: { review_notes: notes[post.id] || undefined }
                          });
                          setQueue((current) => ({
                            ...current,
                            pending_posts: current.pending_posts.filter((item) => item.id !== post.id)
                          }));
                          return rejected;
                        },
                        {
                          successMessage: "Post rejected."
                        }
                      )
                    }
                  >
                    Reject
                  </button>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>

      <section className="auth-section">
        <h2>Oracle live readiness</h2>
        {isLoading ? (
          <p>Checking signer and allowance state...</p>
        ) : !backendUser?.is_admin ? (
          <p>Only admin accounts can inspect oracle wallet readiness.</p>
        ) : oracleReadiness ? (
          <>
            <dl className="kv-list compact">
              <div>
                <dt>Provider</dt>
                <dd>{oracleReadiness.provider}</dd>
              </div>
              <div>
                <dt>Execution mode</dt>
                <dd>{oracleReadiness.execution_mode}</dd>
              </div>
              <div>
                <dt>RPC chain</dt>
                <dd>{oracleReadiness.rpc_chain_id ?? "Not connected"}</dd>
              </div>
              <div>
                <dt>Signer</dt>
                <dd>{oracleReadiness.signer_address ?? "Not configured"}</dd>
              </div>
              <div>
                <dt>Token balance</dt>
                <dd>{oracleReadiness.token_balance_wei ?? "Unknown"}</dd>
              </div>
              <div>
                <dt>Allowance</dt>
                <dd>{oracleReadiness.allowance_wei ?? "Unknown"}</dd>
              </div>
              <div>
                <dt>Required bond</dt>
                <dd>{oracleReadiness.required_bond_wei}</dd>
              </div>
              <div>
                <dt>Ready</dt>
                <dd>{oracleReadiness.ready_for_live_submission ? "Yes" : "No"}</dd>
              </div>
            </dl>
            {oracleReadiness.issues.length > 0 ? (
              <div className="entity-list">
                {oracleReadiness.issues.map((issue) => (
                  <article className="entity-card" key={issue}>
                    <p>{issue}</p>
                  </article>
                ))}
              </div>
            ) : (
              <p>Signer, RPC, balance, and allowance checks passed for the current configuration.</p>
            )}
            <div className="field">
              <label htmlFor="oracle-approval-amount">Approval amount (wei)</label>
              <input
                id="oracle-approval-amount"
                value={approvalAmount}
                onChange={(event) => setApprovalAmount(event.target.value)}
              />
            </div>
            <div className="button-row">
              <button
                className="button-secondary"
                disabled={isSubmitting}
                type="button"
                onClick={() =>
                  void runAction(
                    "Refreshing oracle readiness...",
                    async () => {
                      await loadAdminQueue();
                      return true;
                    },
                    {
                      successMessage: "Oracle readiness refreshed."
                    }
                  )
                }
              >
                Refresh oracle readiness
              </button>
              <button
                className="button-primary"
                disabled={
                  isSubmitting ||
                  oracleReadiness.execution_mode !== "live" ||
                  !approvalAmount.trim()
                }
                type="button"
                onClick={() =>
                  void runAction(
                    "Submitting ERC-20 approval transaction...",
                    async () => {
                      const accessToken = await getAccessToken();
                      const approval = await beyulApiFetch<OracleApproval>("/api/v1/admin/oracle/approve-bond", {
                        method: "POST",
                        accessToken,
                        json: {
                          amount_wei: approvalAmount.trim()
                        }
                      });
                      await loadAdminQueue();
                      return approval;
                    },
                    {
                      successMessage: "Approval transaction submitted."
                    }
                  )
                }
              >
                Approve oracle bond
              </button>
            </div>
          </>
        ) : (
          <p>Oracle readiness data is unavailable right now.</p>
        )}
      </section>

      <section className="auth-section">
        <h2>Pending market requests</h2>
        {isLoading ? (
          <p>Loading pending market requests...</p>
        ) : !backendUser?.is_admin ? (
          <p>Only admin accounts can review market requests.</p>
        ) : queue.pending_market_requests.length === 0 ? (
          <p>No submitted market requests waiting for review.</p>
        ) : (
          <div className="entity-list">
            {queue.pending_market_requests.map((request) => (
              <article className="entity-card" key={request.id}>
                <div className="entity-card-header">
                  <strong>{request.title}</strong>
                  <span className="pill">{request.status}</span>
                </div>
                <p>{request.question}</p>
                <dl className="kv-list compact">
                  <div>
                    <dt>Resolution</dt>
                    <dd>{request.resolution_mode}</dd>
                  </div>
                  <div>
                    <dt>Requester</dt>
                    <dd>{request.requester_display_name}</dd>
                  </div>
                </dl>
                <div className="field">
                  <label htmlFor={`request-note-${request.id}`}>Review notes</label>
                  <textarea
                    id={`request-note-${request.id}`}
                    rows={3}
                    value={notes[request.id] || ""}
                    onChange={(event) => setNotes((current) => ({ ...current, [request.id]: event.target.value }))}
                  />
                </div>
                <div className="button-row">
                  {request.status === "submitted" ? (
                    <button
                      className="button-primary"
                      disabled={isSubmitting}
                      type="button"
                      onClick={() =>
                        void runAction(
                          "Approving market request...",
                          async () => {
                            const accessToken = await getAccessToken();
                            const approved = await beyulApiFetch<MarketRequest>(`/api/v1/market-requests/${request.id}/approve`, {
                              method: "POST",
                              accessToken,
                              json: { review_notes: notes[request.id] || undefined }
                            });
                            setQueue((current) => ({
                              ...current,
                              pending_market_requests: current.pending_market_requests.map((item) =>
                                item.id === request.id ? approved : item
                              )
                            }));
                            return approved;
                          },
                          {
                            successMessage: "Market request approved and kept ready for publish."
                          }
                        )
                      }
                    >
                      Approve
                    </button>
                  ) : null}
                  <button
                    className="button-primary"
                    disabled={isSubmitting}
                    type="button"
                    onClick={() =>
                      void runAction(
                        "Publishing market request...",
                        async () => {
                          const accessToken = await getAccessToken();
                          const published = await beyulApiFetch<Market>(`/api/v1/admin/market-requests/${request.id}/publish`, {
                            method: "POST",
                            accessToken,
                            json: { review_notes: notes[request.id] || undefined }
                          });
                          setQueue((current) => ({
                            ...current,
                            pending_market_requests: current.pending_market_requests.filter((item) => item.id !== request.id)
                          }));
                          return published;
                        },
                        {
                          successMessage: "Market request published into a canonical market."
                        }
                      )
                    }
                  >
                    {request.status === "approved" ? "Publish market" : "Approve + publish"}
                  </button>
                  <button
                    className="button-secondary"
                    disabled={isSubmitting}
                    type="button"
                    onClick={() =>
                      void runAction(
                        "Rejecting market request...",
                        async () => {
                          const accessToken = await getAccessToken();
                          const rejected = await beyulApiFetch<MarketRequest>(`/api/v1/market-requests/${request.id}/reject`, {
                            method: "POST",
                            accessToken,
                            json: { review_notes: notes[request.id] || undefined }
                          });
                          setQueue((current) => ({
                            ...current,
                            pending_market_requests: current.pending_market_requests.filter((item) => item.id !== request.id)
                          }));
                          return rejected;
                        },
                        {
                          successMessage: "Market request rejected."
                        }
                      )
                    }
                  >
                    Reject
                  </button>
                </div>
              </article>
            ))}
          </div>
        )}

        <AuthFeedback errorMessage={errorMessage} statusMessage={statusMessage} />
      </section>
    </>
  );
};
