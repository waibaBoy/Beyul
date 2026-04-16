"use client";

import Image from "next/image";
import { useEffect, useState } from "react";
import { AuthFeedback } from "@/components/auth/auth-feedback";
import { useAuth } from "@/components/auth/auth-provider";
import { useAuthAction } from "@/components/auth/use-auth-action";
import { beyulApiFetch } from "@/lib/api/beyul-api";
import { buildTemplateContractPrefill } from "@/lib/markets/request-templates";
import { getSupabaseBrowserClient } from "@/lib/supabase/browser";
import type { MarketRequest, MarketRequestAnswer } from "@/lib/api/types";

type MarketRequestDetailWorkspaceProps = {
  requestId: string;
};

const contractAnswerFields = [
  {
    key: "category",
    label: "Category",
    placeholder: "Crypto",
    helpText: "Top-level discovery bucket for the market."
  },
  {
    key: "subcategory",
    label: "Subcategory",
    placeholder: "Bitcoin",
    helpText: "More specific grouping shown under the main category."
  },
  {
    key: "reference_label",
    label: "Reference label",
    placeholder: "BTC/USD price at open",
    helpText: "Short label for the contract reference shown on the market page."
  },
  {
    key: "reference_source_label",
    label: "Reference source",
    placeholder: "Chainlink Crypto Feeds",
    helpText: "Human-readable source label shown in the contract details."
  },
  {
    key: "reference_asset",
    label: "Reference asset",
    placeholder: "BTC/USD",
    helpText: "Underlying asset or instrument symbol."
  },
  {
    key: "reference_price",
    label: "Reference price",
    placeholder: "67567.69",
    helpText: "Opening or baseline reference value if the contract uses one."
  },
  {
    key: "price_to_beat",
    label: "Price to beat",
    placeholder: "67627.45",
    helpText: "Strike or target value the market is resolving against."
  },
  {
    key: "reference_timestamp",
    label: "Reference timestamp",
    placeholder: "2026-03-31T02:00:00Z",
    helpText: "ISO timestamp for the reference snapshot."
  },
  {
    key: "contract_notes",
    label: "Contract notes",
    placeholder: "This market resolves to Up if the closing BTC/USD value is at or above the opening value.",
    helpText: "Optional notes carried into the contract metadata."
  }
] as const;

type ContractAnswerKey = (typeof contractAnswerFields)[number]["key"];
type ContractAnswerForm = Record<ContractAnswerKey, string>;

const contractAnswerAliases: Record<ContractAnswerKey, string[]> = {
  category: ["category", "market_category"],
  subcategory: ["subcategory", "sub_category"],
  reference_label: ["reference_label", "settlement_source"],
  reference_source_label: ["reference_source_label", "settlement_source", "source_label"],
  reference_asset: ["reference_asset", "asset_symbol"],
  reference_price: ["reference_price", "opening_price", "reference_value"],
  price_to_beat: ["price_to_beat", "strike_price", "target_price"],
  reference_timestamp: ["reference_timestamp", "price_timestamp", "window_start_at"],
  contract_notes: ["contract_notes", "why_now", "resolution_notes", "market_notes"]
};

const defaultContractForm = contractAnswerFields.reduce((accumulator, field) => {
  accumulator[field.key] = "";
  return accumulator;
}, {} as ContractAnswerForm);

const ALLOWED_IMAGE_TYPES = new Set(["image/png", "image/jpeg", "image/webp", "image/gif"]);
const MAX_IMAGE_UPLOAD_BYTES = 5 * 1024 * 1024;

const mergeAnswer = (answers: MarketRequestAnswer[], saved: MarketRequestAnswer) => {
  const withoutCurrent = answers.filter((item) => item.question_key !== saved.question_key);
  return [...withoutCurrent, saved].sort((left, right) => left.question_key.localeCompare(right.question_key));
};

const buildContractForm = (
  marketRequest: MarketRequest | null,
  answers: MarketRequestAnswer[]
): ContractAnswerForm => {
  const templatePrefill = buildTemplateContractPrefill(marketRequest?.template_key, marketRequest?.template_config);
  return contractAnswerFields.reduce((accumulator, field) => {
    const aliasMatch = contractAnswerAliases[field.key]
      .map((alias) => answers.find((answer) => answer.question_key === alias)?.answer_text?.trim() ?? "")
      .find(Boolean);

    if (aliasMatch) {
      accumulator[field.key] = aliasMatch;
      return accumulator;
    }

    const templateValue = templatePrefill[field.key];
    if (templateValue) {
      accumulator[field.key] = templateValue;
      return accumulator;
    }

    if (field.key === "contract_notes" && marketRequest?.description) {
      accumulator[field.key] = marketRequest.description;
      return accumulator;
    }

    accumulator[field.key] = "";
    return accumulator;
  }, { ...defaultContractForm });
};

export const MarketRequestDetailWorkspace = ({ requestId }: MarketRequestDetailWorkspaceProps) => {
  const { getAccessToken, session } = useAuth();
  const [marketRequest, setMarketRequest] = useState<MarketRequest | null>(null);
  const [answers, setAnswers] = useState<MarketRequestAnswer[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [contractForm, setContractForm] = useState<ContractAnswerForm>(defaultContractForm);
  const [imageUploading, setImageUploading] = useState(false);
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
          setContractForm(buildContractForm(nextRequest, nextAnswers));
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

  const handleImageUpload = async (file: File) => {
    if (!marketRequest || !isDraft) return;
    if (!ALLOWED_IMAGE_TYPES.has(file.type)) {
      setStatusMessage("Unsupported image type. Use PNG, JPEG, WEBP, or GIF.");
      return;
    }
    if (file.size > MAX_IMAGE_UPLOAD_BYTES) {
      setStatusMessage("Image is too large. Maximum size is 5MB.");
      return;
    }
    setImageUploading(true);
    try {
      const supabase = getSupabaseBrowserClient();
      const ext = file.name.split(".").pop() ?? "png";
      const path = `${Date.now()}-${requestId}.${ext}`;
      const { data, error } = await supabase.storage.from("market-images").upload(path, file, { upsert: true });
      if (error || !data) throw error ?? new Error("Upload failed");
      const { data: urlData } = supabase.storage.from("market-images").getPublicUrl(data.path);

      const accessToken = await getAccessToken();
      const updated = await beyulApiFetch<MarketRequest>(`/api/v1/market-requests/${requestId}`, {
        method: "PUT",
        accessToken,
        json: { image_url: urlData.publicUrl }
      });
      setMarketRequest(updated);
      setStatusMessage("Market image updated.");
    } catch (error) {
      setStatusMessage(error instanceof Error ? error.message : "Failed to upload market image.");
    } finally {
      setImageUploading(false);
    }
  };

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
            <div>
              <dt>Template</dt>
              <dd>{marketRequest.template_key || "Manual"}</dd>
            </div>
          </dl>
        ) : (
          <p>Market request not found or not accessible.</p>
        )}

        {marketRequest ? (
          <div className="field">
            <label htmlFor="detail-request-image-file">Market image <span className="field-hint-inline">(optional)</span></label>
            <div className="image-upload-row">
              {marketRequest.image_url ? (
                <Image className="market-icon" src={marketRequest.image_url} alt="Market image preview" width={48} height={48} unoptimized />
              ) : null}
              <label className="image-upload-btn" htmlFor="detail-request-image-file">
                {imageUploading ? "Uploading..." : marketRequest.image_url ? "Change image" : "Upload image"}
              </label>
              <input
                id="detail-request-image-file"
                type="file"
                accept="image/png,image/jpeg,image/webp,image/gif"
                style={{ display: "none" }}
                disabled={!isDraft || !session || imageUploading}
                onChange={(event) => {
                  const file = event.currentTarget.files?.[0];
                  if (file) void handleImageUpload(file);
                  event.currentTarget.value = "";
                }}
              />
              {marketRequest.image_url ? (
                <button
                  type="button"
                  className="image-upload-clear"
                  disabled={!isDraft || !session || imageUploading}
                  onClick={() =>
                    void runAction(
                      "Removing market image...",
                      async () => {
                        const accessToken = await getAccessToken();
                        const updated = await beyulApiFetch<MarketRequest>(`/api/v1/market-requests/${requestId}`, {
                          method: "PUT",
                          accessToken,
                          json: { image_url: null }
                        });
                        setMarketRequest(updated);
                        return updated;
                      },
                      { successMessage: "Market image removed." }
                    )
                  }
                >
                  Remove
                </button>
              ) : null}
            </div>
          </div>
        ) : null}
      </section>

      <section className="auth-section">
        <h2>Contract intake</h2>
        <p>Fill the structured contract fields that drive the market header, contract details, and price-to-beat presentation after publish.</p>
        {answers.length === 0 && marketRequest?.description ? (
          <p>The request has no saved contract-answer rows yet, so the form is prefilled from the base request where possible.</p>
        ) : null}

        <form
          className="auth-form"
          onSubmit={(event) => {
            event.preventDefault();
            void runAction(
              "Saving market intake answer...",
              async () => {
                const accessToken = await getAccessToken();
                let nextAnswers = [...answers];
                for (const field of contractAnswerFields) {
                  const answerText = contractForm[field.key].trim();
                  if (!answerText) {
                    continue;
                  }
                  const saved = await beyulApiFetch<MarketRequestAnswer>(
                    `/api/v1/market-requests/${requestId}/answers/${encodeURIComponent(field.key)}`,
                    {
                      method: "PUT",
                      accessToken,
                      json: {
                        question_label: field.label,
                        answer_text: answerText
                      }
                    }
                  );
                  nextAnswers = mergeAnswer(nextAnswers, saved);
                }
                setAnswers(nextAnswers);
                return nextAnswers.length;
              },
              {
                successMessage: (savedCount) =>
                  savedCount > 0
                    ? `Saved ${savedCount} contract field${savedCount === 1 ? "" : "s"}.`
                    : "Nothing to save yet. Add at least one contract field."
              }
            );
          }}
        >
          <div className="entity-list">
            {contractAnswerFields.map((field) => (
              <article className="entity-card" key={field.key}>
                <div className="entity-card-header">
                  <strong>{field.label}</strong>
                  <span className="pill">{field.key}</span>
                </div>
                <p>{field.helpText}</p>
                {field.key === "contract_notes" ? (
                  <div className="field">
                    <label htmlFor={field.key}>{field.label}</label>
                    <textarea
                      id={field.key}
                      placeholder={field.placeholder}
                      rows={4}
                      value={contractForm[field.key]}
                      onChange={(event) =>
                        setContractForm((current) => ({
                          ...current,
                          [field.key]: event.target.value
                        }))
                      }
                    />
                  </div>
                ) : (
                  <div className="field">
                    <label htmlFor={field.key}>{field.label}</label>
                    <input
                      id={field.key}
                      placeholder={field.placeholder}
                      value={contractForm[field.key]}
                      onChange={(event) =>
                        setContractForm((current) => ({
                          ...current,
                          [field.key]: event.target.value
                        }))
                      }
                    />
                  </div>
                )}
              </article>
            ))}
          </div>
          <div className="button-row">
            <button className="button-primary" disabled={isSubmitting || !session || !isDraft} type="submit">
              Save contract fields
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
