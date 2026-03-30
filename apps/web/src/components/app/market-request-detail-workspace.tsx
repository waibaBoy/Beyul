"use client";

import { useEffect, useState } from "react";
import { AuthFeedback } from "@/components/auth/auth-feedback";
import { useAuth } from "@/components/auth/auth-provider";
import { useAuthAction } from "@/components/auth/use-auth-action";
import { beyulApiFetch } from "@/lib/api/beyul-api";
import type { MarketRequest, MarketRequestAnswer } from "@/lib/api/types";

type MarketRequestDetailWorkspaceProps = {
  requestId: string;
};

const defaultAnswerForm = {
  questionKey: "",
  questionLabel: "",
  answerText: ""
};

export const MarketRequestDetailWorkspace = ({ requestId }: MarketRequestDetailWorkspaceProps) => {
  const { getAccessToken, session } = useAuth();
  const [marketRequest, setMarketRequest] = useState<MarketRequest | null>(null);
  const [answers, setAnswers] = useState<MarketRequestAnswer[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [form, setForm] = useState(defaultAnswerForm);
  const isDraft = marketRequest?.status === "draft";
  const { errorMessage, isSubmitting, runAction, setStatusMessage, statusMessage } = useAuthAction(
    "Load the request detail, intake answers, and submission state."
  );

  useEffect(() => {
    let isMounted = true;

    const loadRequest = async () => {
      if (!session) {
        if (isMounted) {
          setMarketRequest(null);
          setAnswers([]);
          setIsLoading(false);
        }
        return;
      }

      try {
        const accessToken = await getAccessToken();
        const [nextRequest, nextAnswers] = await Promise.all([
          beyulApiFetch<MarketRequest>(`/api/v1/market-requests/${requestId}`, { accessToken }),
          beyulApiFetch<MarketRequestAnswer[]>(`/api/v1/market-requests/${requestId}/answers`, { accessToken })
        ]);

        if (isMounted) {
          setMarketRequest(nextRequest);
          setAnswers(nextAnswers);
          setStatusMessage(`Loaded ${nextAnswers.length} answers for this request.`);
        }
      } catch (error) {
        if (isMounted) {
          setStatusMessage(error instanceof Error ? error.message : "Failed to load market request detail.");
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    void loadRequest();

    return () => {
      isMounted = false;
    };
  }, [getAccessToken, requestId, session, setStatusMessage]);

  return (
    <>
      <section className="auth-section">
        <h2>Market request detail</h2>

        {isLoading ? (
          <p>Loading request...</p>
        ) : marketRequest ? (
          <dl className="kv-list">
            <div>
              <dt>Title</dt>
              <dd>{marketRequest.title}</dd>
            </div>
            <div>
              <dt>Status</dt>
              <dd>{marketRequest.status}</dd>
            </div>
            <div>
              <dt>Community</dt>
              <dd>{marketRequest.community_name || "Standalone"}</dd>
            </div>
            <div>
              <dt>Resolution</dt>
              <dd>{marketRequest.resolution_mode}</dd>
            </div>
            <div>
              <dt>Review notes</dt>
              <dd>{marketRequest.review_notes || "None"}</dd>
            </div>
          </dl>
        ) : (
          <p>Market request not found or not accessible.</p>
        )}
      </section>

      <section className="auth-section">
        <h2>Answer intake questions</h2>
        <p>Keep answers in draft until the request is ready for moderation.</p>

        <form
          className="auth-form"
          onSubmit={(event) => {
            event.preventDefault();
            void runAction(
              "Saving market intake answer...",
              async () => {
                const accessToken = await getAccessToken();
                const saved = await beyulApiFetch<MarketRequestAnswer>(
                  `/api/v1/market-requests/${requestId}/answers/${encodeURIComponent(form.questionKey)}`,
                  {
                    method: "PUT",
                    accessToken,
                    json: {
                      question_label: form.questionLabel,
                      answer_text: form.answerText || undefined
                    }
                  }
                );
                setAnswers((current) => {
                  const withoutCurrent = current.filter((item) => item.question_key !== saved.question_key);
                  return [...withoutCurrent, saved].sort((left, right) => left.question_key.localeCompare(right.question_key));
                });
                setForm(defaultAnswerForm);
                return saved;
              },
              {
                successMessage: (saved) => `Saved answer for ${saved.question_label}.`
              }
            );
          }}
        >
          <div className="field">
            <label htmlFor="answer-key">Question key</label>
            <input
              id="answer-key"
              placeholder="settlement_source"
              value={form.questionKey}
              onChange={(event) => setForm((current) => ({ ...current, questionKey: event.target.value }))}
            />
          </div>
          <div className="field">
            <label htmlFor="answer-label">Question label</label>
            <input
              id="answer-label"
              placeholder="Settlement source"
              value={form.questionLabel}
              onChange={(event) => setForm((current) => ({ ...current, questionLabel: event.target.value }))}
            />
          </div>
          <div className="field">
            <label htmlFor="answer-text">Answer text</label>
            <textarea
              id="answer-text"
              placeholder="Use the official source and explain the exact resolution trigger."
              rows={5}
              value={form.answerText}
              onChange={(event) => setForm((current) => ({ ...current, answerText: event.target.value }))}
            />
          </div>
          <div className="button-row">
            <button className="button-primary" disabled={isSubmitting || !session || !isDraft} type="submit">
              Save answer
            </button>
            <button
              className="button-secondary"
              disabled={isSubmitting || !session || !isDraft || !marketRequest}
              type="button"
              onClick={() =>
                void runAction(
                  "Submitting market request for review...",
                  async () => {
                    const accessToken = await getAccessToken();
                    const submitted = await beyulApiFetch<MarketRequest>(`/api/v1/market-requests/${requestId}/submit`, {
                      method: "POST",
                      accessToken
                    });
                    setMarketRequest(submitted);
                    return submitted;
                  },
                  {
                    successMessage: "Market request submitted to the admin review queue."
                  }
                )
              }
            >
              Submit for review
            </button>
          </div>
        </form>

        <AuthFeedback errorMessage={errorMessage} statusMessage={statusMessage} />
      </section>

      <section className="auth-section">
        <h2>Saved answers</h2>
        {isLoading ? (
          <p>Loading answers...</p>
        ) : answers.length === 0 ? (
          <p>No intake answers saved yet.</p>
        ) : (
          <div className="entity-list">
            {answers.map((answer) => (
              <article className="entity-card" key={answer.question_key}>
                <div className="entity-card-header">
                  <strong>{answer.question_label}</strong>
                  <span className="pill">{answer.question_key}</span>
                </div>
                <p>{answer.answer_text || "Structured JSON-only answer."}</p>
              </article>
            ))}
          </div>
        )}
      </section>
    </>
  );
};
