"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { beyulApiFetch } from "@/lib/api/beyul-api";
import type { Community, MarketRequest, MarketRequestCreateInput, MarketTemplateKey } from "@/lib/api/types";
import {
  getTemplateDraft,
  marketTemplateDefinitionByKey,
  marketTemplateDefinitions,
  validateTemplateBuilder,
  type TemplateBuilderInput
} from "@/lib/markets/request-templates";
import { normalizeSlug } from "@/lib/slug";
import { getSupabaseBrowserClient } from "@/lib/supabase/browser";
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

const defaultTemplateBuilder: TemplateBuilderInput = {
  templateKey: "price_above",
  subject: "",
  referenceAsset: "",
  thresholdValue: "",
  timeframeLabel: "",
  intervalLabel: "",
  category: "Crypto",
  subcategory: "",
  referenceSourceLabel: "Chainlink Crypto Feeds",
  referencePrice: "",
  referenceTimestamp: "",
  contractNotes: ""
};

const ALLOWED_IMAGE_TYPES = new Set(["image/png", "image/jpeg", "image/webp", "image/gif"]);
const MAX_IMAGE_UPLOAD_BYTES = 5 * 1024 * 1024;

export const MarketRequestsWorkspace = () => {
  const { getAccessToken, session } = useAuth();
  const [requests, setRequests] = useState<MarketRequest[]>([]);
  const [communities, setCommunities] = useState<Community[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [form, setForm] = useState(defaultRequestForm);
  const [templateBuilder, setTemplateBuilder] = useState<TemplateBuilderInput>(defaultTemplateBuilder);
  const [customizeCopy, setCustomizeCopy] = useState(false);
  const [showAdvancedReference, setShowAdvancedReference] = useState(false);
  const { errorMessage, isSubmitting, runAction, statusMessage, setStatusMessage } = useAuthAction(
    "Create and review your live market requests."
  );
  const [imageUploading, setImageUploading] = useState(false);
  const [multiOutcome, setMultiOutcome] = useState(false);
  const [customOutcomes, setCustomOutcomes] = useState<string[]>(["", ""]);
  const selectedTemplate = marketTemplateDefinitionByKey[templateBuilder.templateKey];
  const templateDraft = getTemplateDraft(templateBuilder);
  const templateValidation = validateTemplateBuilder(templateBuilder);
  const hasTemplateErrors = Object.keys(templateValidation.fieldErrors).length > 0;

  type QualityWarning = { code: string; severity: string; message: string };
  type DuplicateMatch = { source: string; slug: string | null; title: string; status: string; match_type: string; similarity?: number };
  const [qualityWarnings, setQualityWarnings] = useState<QualityWarning[]>([]);
  const [duplicateMatches, setDuplicateMatches] = useState<DuplicateMatch[]>([]);
  const [qualityBlocked, setQualityBlocked] = useState<string | null>(null);
  const qualityTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const runQualityCheck = useCallback(async (title: string, question: string) => {
    if (!title || title.length < 5 || !question || question.length < 5) {
      setQualityWarnings([]);
      setDuplicateMatches([]);
      setQualityBlocked(null);
      return;
    }
    try {
      const accessToken = await getAccessToken();
      if (!accessToken) return;
      const result = await beyulApiFetch<{
        blocked: boolean;
        block_reason: string | null;
        warnings: QualityWarning[];
        duplicate_matches: DuplicateMatch[];
      }>("/api/v1/market-requests/quality-check", {
        method: "POST",
        accessToken,
        json: {
          title,
          question,
          market_access_mode: form.market_access_mode || "public",
          resolution_mode: form.resolution_mode || "oracle",
        },
      });
      setQualityWarnings(result.warnings);
      setDuplicateMatches(result.duplicate_matches);
      setQualityBlocked(result.blocked ? result.block_reason : null);
    } catch {
      // silent
    }
  }, [getAccessToken, form.market_access_mode, form.resolution_mode]);

  useEffect(() => {
    if (qualityTimerRef.current) clearTimeout(qualityTimerRef.current);
    qualityTimerRef.current = setTimeout(() => {
      void runQualityCheck(form.title, form.question);
    }, 800);
    return () => { if (qualityTimerRef.current) clearTimeout(qualityTimerRef.current); };
  }, [form.title, form.question, runQualityCheck]);

  const handleImageUpload = async (file: File) => {
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
      const path = `${Date.now()}.${ext}`;
      const { data, error } = await supabase.storage.from("market-images").upload(path, file, { upsert: true });
      if (error || !data) throw error ?? new Error("Upload failed");
      const { data: urlData } = supabase.storage.from("market-images").getPublicUrl(data.path);
      setForm((current) => ({ ...current, image_url: urlData.publicUrl }));
    } catch {
      // silent — field stays empty
    } finally {
      setImageUploading(false);
    }
  };

  const applyTemplateDraft = (nextBuilder: TemplateBuilderInput) => {
    const draft = getTemplateDraft(nextBuilder);
    setForm((current) => ({
      ...current,
      title: draft.title,
      question: draft.question,
      description: draft.description,
      slug: draft.slug
    }));
  };

  const updateTemplateBuilder = <K extends keyof TemplateBuilderInput>(key: K, value: TemplateBuilderInput[K]) => {
    setTemplateBuilder((current) => {
      const nextBuilder = { ...current, [key]: value };
      if (key === "templateKey") {
        const template = marketTemplateDefinitionByKey[value as MarketTemplateKey];
        nextBuilder.category = template.defaultCategory;
      }
      applyTemplateDraft(nextBuilder);
      return nextBuilder;
    });
  };

  useEffect(() => {
    applyTemplateDraft(defaultTemplateBuilder);
  }, []);

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
        <p>Start from a market template so the request and contract metadata stay consistent from intake through publish.</p>

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
                    slug: form.slug ? normalizeSlug(form.slug) : undefined,
                    template_key: templateBuilder.templateKey,
                    template_config: templateDraft.templateConfig,
                    description: form.description || undefined,
                    community_id: form.community_id || undefined,
                    custom_outcomes: multiOutcome && customOutcomes.filter((o) => o.trim()).length >= 2
                      ? customOutcomes.filter((o) => o.trim())
                      : undefined
                  }
                });
                setRequests((current) => [created, ...current]);
                setForm(defaultRequestForm);
                setTemplateBuilder(defaultTemplateBuilder);
                setCustomizeCopy(false);
                setShowAdvancedReference(false);
                setMultiOutcome(false);
                setCustomOutcomes(["", ""]);
                applyTemplateDraft(defaultTemplateBuilder);
                return created;
              },
              {
                successMessage: (created) => `Created market request ${created.slug ?? created.id}.`
              }
            );
          }}
        >
          <div className="field">
            <label htmlFor="request-template">Market template</label>
            <select
              id="request-template"
              className="select-field"
              value={templateBuilder.templateKey}
              onChange={(event) => updateTemplateBuilder("templateKey", event.target.value as MarketTemplateKey)}
            >
              {marketTemplateDefinitions.map((template) => (
                <option key={template.key} value={template.key}>
                  {template.label}
                </option>
              ))}
            </select>
            <p>{selectedTemplate.description}</p>
          </div>
          <div className="field">
            <label htmlFor="request-subject">Subject</label>
            <input
              id="request-subject"
              placeholder="Ethereum"
              value={templateBuilder.subject}
              onChange={(event) => updateTemplateBuilder("subject", event.target.value)}
            />
            {templateValidation.fieldErrors.subject ? <p>{templateValidation.fieldErrors.subject}</p> : null}
          </div>
          <div className="field">
            <label htmlFor="request-reference-asset">Reference asset</label>
            <input
              id="request-reference-asset"
              placeholder="ETH/USD"
              value={templateBuilder.referenceAsset}
              onChange={(event) => updateTemplateBuilder("referenceAsset", event.target.value)}
            />
            {templateValidation.fieldErrors.referenceAsset ? <p>{templateValidation.fieldErrors.referenceAsset}</p> : null}
          </div>
          {selectedTemplate.needsThreshold ? (
            <div className="field">
              <label htmlFor="request-threshold">Target value</label>
              <input
                id="request-threshold"
                placeholder="6000"
                value={templateBuilder.thresholdValue}
                onChange={(event) => updateTemplateBuilder("thresholdValue", event.target.value)}
              />
              {templateValidation.fieldErrors.thresholdValue ? <p>{templateValidation.fieldErrors.thresholdValue}</p> : null}
            </div>
          ) : null}
          <div className="field">
            <label htmlFor="request-timeframe">Timeframe label</label>
            <input
              id="request-timeframe"
              placeholder="by June 30, 2026"
              value={templateBuilder.timeframeLabel}
              onChange={(event) => updateTemplateBuilder("timeframeLabel", event.target.value)}
            />
          </div>
          {selectedTemplate.needsInterval ? (
            <div className="field">
              <label htmlFor="request-interval">Interval label</label>
              <input
                id="request-interval"
                placeholder="5 minutes"
                value={templateBuilder.intervalLabel}
                onChange={(event) => updateTemplateBuilder("intervalLabel", event.target.value)}
              />
              {templateValidation.fieldErrors.intervalLabel ? <p>{templateValidation.fieldErrors.intervalLabel}</p> : null}
            </div>
          ) : null}
          <div className="field">
            <label htmlFor="request-category">Category</label>
            <input
              id="request-category"
              placeholder="Crypto"
              value={templateBuilder.category}
              onChange={(event) => updateTemplateBuilder("category", event.target.value)}
            />
            {templateValidation.fieldErrors.category ? <p>{templateValidation.fieldErrors.category}</p> : null}
          </div>
          <div className="field">
            <label htmlFor="request-subcategory">Subcategory</label>
            <input
              id="request-subcategory"
              placeholder="Ethereum"
              value={templateBuilder.subcategory}
              onChange={(event) => updateTemplateBuilder("subcategory", event.target.value)}
            />
          </div>
          <div className="field">
            <label htmlFor="request-source-label">Reference source label</label>
            <input
              id="request-source-label"
              placeholder="Chainlink Crypto Feeds"
              value={templateBuilder.referenceSourceLabel}
              onChange={(event) => updateTemplateBuilder("referenceSourceLabel", event.target.value)}
            />
          </div>
          <div className="field">
            <label>
              <input
                checked={showAdvancedReference}
                onChange={(event) => setShowAdvancedReference(event.target.checked)}
                type="checkbox"
              />{" "}
              Override provider-filled reference snapshot
            </label>
            <p>Leave this off to let publish-time reference snapshots fill the opening price and timestamp automatically.</p>
          </div>
          {showAdvancedReference ? (
            <>
              <div className="field">
                <label htmlFor="request-reference-price">Reference price</label>
                <input
                  id="request-reference-price"
                  placeholder="6000"
                  value={templateBuilder.referencePrice}
                  onChange={(event) => updateTemplateBuilder("referencePrice", event.target.value)}
                />
                {templateValidation.fieldErrors.referencePrice ? <p>{templateValidation.fieldErrors.referencePrice}</p> : null}
              </div>
              <div className="field">
                <label htmlFor="request-reference-timestamp">Reference timestamp</label>
                <input
                  id="request-reference-timestamp"
                  placeholder="2026-04-01T01:00:00Z"
                  value={templateBuilder.referenceTimestamp}
                  onChange={(event) => updateTemplateBuilder("referenceTimestamp", event.target.value)}
                />
                {templateValidation.fieldErrors.referenceTimestamp ? <p>{templateValidation.fieldErrors.referenceTimestamp}</p> : null}
              </div>
            </>
          ) : null}
          <div className="field">
            <label htmlFor="request-template-notes">Template notes</label>
            <textarea
              id="request-template-notes"
              rows={3}
              placeholder="Optional contract notes carried into the market details."
              value={templateBuilder.contractNotes}
              onChange={(event) => updateTemplateBuilder("contractNotes", event.target.value)}
            />
          </div>
          <article className="entity-card">
            <div className="entity-card-header">
              <strong>Generated market copy</strong>
              <span className="pill">{selectedTemplate.label}</span>
            </div>
            <dl className="kv-list compact">
              <div>
                <dt>Title</dt>
                <dd>{templateDraft.title}</dd>
              </div>
              <div>
                <dt>Slug</dt>
                <dd>{templateDraft.slug}</dd>
              </div>
              <div>
                <dt>Question</dt>
                <dd>{templateDraft.question}</dd>
              </div>
              <div>
                <dt>Description</dt>
                <dd>{templateDraft.description}</dd>
              </div>
            </dl>
          </article>
          <div className="field">
            <label>
              <input
                checked={customizeCopy}
                onChange={(event) => setCustomizeCopy(event.target.checked)}
                type="checkbox"
              />{" "}
              Customize generated title, slug, question, and description
            </label>
          </div>
          {customizeCopy ? (
            <>
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
                  onChange={(event) =>
                    setForm((current) => ({ ...current, slug: normalizeSlug(event.target.value) }))
                  }
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
            </>
          ) : null}
          <div className="field">
            <label htmlFor="request-image">Market image <span className="field-hint-inline">(optional)</span></label>
            <div className="image-upload-row">
              {form.image_url && (
                <img className="market-icon" src={form.image_url} alt="Preview" width={48} height={48} />
              )}
              <label className="image-upload-btn" htmlFor="request-image-file">
                {imageUploading ? "Uploading…" : form.image_url ? "Change image" : "Upload image"}
              </label>
              <input
                id="request-image-file"
                type="file"
                accept="image/png,image/jpeg,image/webp,image/gif"
                style={{ display: "none" }}
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) void handleImageUpload(file);
                }}
              />
              {form.image_url && (
                <button
                  type="button"
                  className="image-upload-clear"
                  onClick={() => setForm((current) => ({ ...current, image_url: undefined }))}
                >
                  Remove
                </button>
              )}
            </div>
            <p className="field-hint">PNG, JPG or WebP. Shown as a circle icon on market cards.</p>
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
          <div className="field">
            <label>
              <input
                checked={multiOutcome}
                onChange={(event) => {
                  setMultiOutcome(event.target.checked);
                  if (!event.target.checked) setCustomOutcomes(["", ""]);
                }}
                type="checkbox"
              />{" "}
              Multi-outcome market
            </label>
            <p className="field-hint">Enable to define custom outcome labels instead of the default Yes/No.</p>
          </div>
          {multiOutcome ? (
            <div className="field">
              <label>Outcome labels <span className="field-hint-inline">(minimum 2)</span></label>
              {customOutcomes.map((outcome, index) => (
                <div key={index} className="image-upload-row" style={{ marginBottom: 4 }}>
                  <input
                    placeholder={`Outcome ${index + 1}`}
                    value={outcome}
                    onChange={(event) => {
                      const next = [...customOutcomes];
                      next[index] = event.target.value;
                      setCustomOutcomes(next);
                    }}
                    style={{ flex: 1 }}
                  />
                  {customOutcomes.length > 2 ? (
                    <button
                      type="button"
                      className="image-upload-clear"
                      onClick={() => setCustomOutcomes(customOutcomes.filter((_, i) => i !== index))}
                    >
                      Remove
                    </button>
                  ) : null}
                </div>
              ))}
              <button
                type="button"
                className="button-secondary"
                style={{ marginTop: 4 }}
                onClick={() => setCustomOutcomes([...customOutcomes, ""])}
              >
                Add outcome
              </button>
            </div>
          ) : null}

          {qualityBlocked ? (
            <div className="mq-quality-block">
              <strong>Blocked:</strong> {qualityBlocked}
            </div>
          ) : null}

          {qualityWarnings.length > 0 ? (
            <div className="mq-quality-warnings">
              {qualityWarnings.map((w, i) => (
                <div key={`${w.code}-${i}`} className={`mq-quality-item mq-quality-${w.severity}`}>
                  <span className="mq-quality-badge">{w.severity === "error" ? "✕" : "⚠"}</span>
                  {w.message}
                </div>
              ))}
            </div>
          ) : null}

          {duplicateMatches.length > 0 ? (
            <div className="mq-duplicates">
              <strong>Possible duplicates found:</strong>
              <ul>
                {duplicateMatches.map((m, i) => (
                  <li key={`${m.slug}-${i}`}>
                    <Link href={m.source === "market" ? `/markets/${m.slug}` : `/market-requests`}>
                      {m.title}
                    </Link>
                    <span className="mq-dup-meta"> ({m.match_type.replace("_", " ")}{m.similarity ? ` ${Math.round(m.similarity * 100)}%` : ""} — {m.status})</span>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          <div className="button-row">
            <button
              className="button-primary"
              disabled={isSubmitting || !session || hasTemplateErrors || !!qualityBlocked || qualityWarnings.some((w) => w.severity === "error") || (multiOutcome && customOutcomes.filter((o) => o.trim()).length < 2)}
              type="submit"
            >
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
