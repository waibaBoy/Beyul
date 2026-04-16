"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { AuthFeedback } from "@/components/auth/auth-feedback";
import { AdvancedOrderForm } from "@/components/app/advanced-order-form";
import { InteractiveChart } from "@/components/app/interactive-chart";
import { MarketIcon } from "@/components/app/market-icon";
import { useAuth } from "@/components/auth/auth-provider";
import { useAuthAction } from "@/components/auth/use-auth-action";
import { beyulApiFetch } from "@/lib/api/beyul-api";
import {
  buildCumulativeDepth,
  buildHistoryChartSeries,
  getOutcomeMicroStats,
  getTicketExecutionPreview
} from "@/lib/markets/microstructure";
import type {
  BackendUser,
  Market,
  MarketDispute,
  MarketDisputeCreateInput,
  MarketDisputeEvidenceCreateInput,
  MarketDisputeReviewInput,
  MarketDetailBootstrap,
  MarketHolders,
  MarketHistory,
  MarketHistoryRangeKey,
  MarketOracleFinalizeInput,
  MarketOrder,
  MarketOrderCreateInput,
  MarketResolutionState,
  MarketResolution,
  MarketSettlementRequestInput,
  MarketTradingShell,
  PortfolioSummary
} from "@/lib/api/types";
import { useMarketLiveEvents } from "@/lib/realtime/use-market-live-events";

type MarketDetailWorkspaceProps = {
  slug: string;
};

const formatPrice = (value: string | null) => (value ? `${Math.round(Number(value) * 100)}c` : "No price yet");
const formatContractValue = (value: string | null) => {
  if (!value) {
    return "Not set";
  }
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return value;
  }
  if (Math.abs(numeric) <= 1) {
    return `${Math.round(numeric * 100)}c`;
  }
  return numeric.toLocaleString(undefined, {
    maximumFractionDigits: 4
  });
};
const formatNumber = (value: string | null) => (value ? Number(value).toLocaleString() : "0");
const formatTradeTime = (value: string) =>
  new Date(value).toLocaleTimeString([], {
    hour: "numeric",
    minute: "2-digit",
    second: "2-digit"
  });
const formatMarketTime = (value: string) =>
  new Date(value).toLocaleString([], {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit"
  });
const formatCountdown = (value: string | null) => {
  if (!value) {
    return "Not scheduled";
  }
  const diffMs = new Date(value).getTime() - Date.now();
  if (!Number.isFinite(diffMs)) {
    return "Not scheduled";
  }
  if (diffMs <= 0) {
    return "Closed";
  }
  const totalMinutes = Math.floor(diffMs / 60000);
  const days = Math.floor(totalMinutes / (60 * 24));
  const hours = Math.floor((totalMinutes % (60 * 24)) / 60);
  const minutes = totalMinutes % 60;
  if (days > 0) {
    return `${days}d ${hours}h`;
  }
  if (hours > 0) {
    return `${hours}h ${minutes}m`;
  }
  return `${minutes}m`;
};
const formatExposureLabel = (quantity: string, outcomeLabel: string) => {
  const numericQuantity = Number(quantity);
  if (numericQuantity > 0) {
    return `Long ${outcomeLabel}`;
  }
  if (numericQuantity < 0) {
    return `Short ${outcomeLabel}`;
  }
  return `${outcomeLabel} history`;
};
const formatOrderLabel = (side: "buy" | "sell", outcomeLabel: string) =>
  side === "buy" ? `Buy ${outcomeLabel}` : `Sell ${outcomeLabel} (complementary exposure)`;
const evidenceTypeOptions = [
  { value: "source_link", label: "Source link" },
  { value: "archive_snapshot", label: "Archive snapshot" },
  { value: "screenshot", label: "Screenshot" },
  { value: "transaction", label: "Transaction" },
  { value: "market_rule", label: "Rule reference" },
  { value: "commentary", label: "Commentary" },
  { value: "other", label: "Other" }
] as const;
const formatEvidenceTypeLabel = (value: string) =>
  evidenceTypeOptions.find((option) => option.value === value)?.label ??
  value
    .split("_")
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(" ");
const formatResolutionEventLabel = (eventType: string) =>
  eventType
    .split("_")
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(" ");
const buildDefaultEvidenceDraft = (): MarketDisputeEvidenceCreateInput => ({
  evidence_type: "source_link",
  url: "",
  description: "",
  payload: {}
});
const buildDefaultDisputeReviewDraft = (): MarketDisputeReviewInput => ({
  status: "dismissed",
  review_notes: ""
});
const buildDefaultFinalizeDraft = (): MarketOracleFinalizeInput => ({
  winning_outcome_id: "",
  candidate_id: "",
  source_reference_url: "",
  notes: ""
});
type EvidenceType = MarketDisputeEvidenceCreateInput["evidence_type"];
const evidenceTypeRequiresUrl = (value: string) =>
  ["source_link", "archive_snapshot", "screenshot", "transaction"].includes(value);
const evidenceTypeRequiresDescription = (value: string) =>
  ["market_rule", "commentary"].includes(value);
const historyRangeOptions: MarketHistoryRangeKey[] = ["1M", "5M", "30M", "1H", "1D", "1W"];
const formatHistoryInterval = (intervalSeconds: number) => {
  if (intervalSeconds < 60) {
    return `${intervalSeconds}s candles`;
  }
  if (intervalSeconds < 3600) {
    return `${Math.round(intervalSeconds / 60)}m candles`;
  }
  if (intervalSeconds < 86400) {
    return `${Math.round(intervalSeconds / 3600)}h candles`;
  }
  return `${Math.round(intervalSeconds / 86400)}d candles`;
};
const parseResponseBody = (rawBody: string): unknown => {
  try {
    return JSON.parse(rawBody);
  } catch {
    return rawBody;
  }
};
const getApiErrorDetail = (body: unknown): string | null => {
  if (typeof body === "string") {
    return body;
  }
  if (!body || typeof body !== "object" || !("detail" in body)) {
    return null;
  }
  const detail = body.detail;
  return typeof detail === "string" ? detail : null;
};
const getOrderConflictHint = (message: string, marketStatus: string | undefined) => {
  if (!message) {
    return "";
  }
  if (message.includes("Insufficient available balance")) {
    return "Fund the account first, or reduce size. Sell orders still reserve complementary collateral in binary markets.";
  }
  if (message.includes("Order price must be between 0 and 1")) {
    return "Use decimal probability pricing like 0.55 instead of whole-number cents like 55.";
  }
  if (message.includes("Order quantity must be greater than zero")) {
    return "Enter a positive quantity greater than zero.";
  }
  if (message.includes("Limit orders require a price")) {
    return "Enter a limit price before submitting the order.";
  }
  if (message.includes("Orders are only accepted while the market is gathering liquidity or open for trading")) {
    return `This market is currently ${marketStatus ?? "not tradable"}. Orders are only allowed in pending_liquidity or open status.`;
  }
  if (message.includes("Market orders are not enabled until the matching engine is live")) {
    return "This environment accepts resting limit orders only. Use order type limit with a price between 0 and 1.";
  }
  return "";
};
const isDevelopmentBuild = process.env.NODE_ENV !== "production";

export const MarketDetailWorkspace = ({ slug }: MarketDetailWorkspaceProps) => {
  const { getAccessToken, session } = useAuth();
  const [backendUser, setBackendUser] = useState<BackendUser | null>(null);
  const [shell, setShell] = useState<MarketTradingShell | null>(null);
  const [history, setHistory] = useState<MarketHistory | null>(null);
  const [holders, setHolders] = useState<MarketHolders | null>(null);
  const [resolutionState, setResolutionState] = useState<MarketResolutionState | null>(null);
  const [historyRange, setHistoryRange] = useState<MarketHistoryRangeKey>("1H");
  const [myOrders, setMyOrders] = useState<MarketOrder[]>([]);
  const [portfolio, setPortfolio] = useState<PortfolioSummary | null>(null);
  const [orderErrorHint, setOrderErrorHint] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isHistoryLoading, setIsHistoryLoading] = useState(false);
  const [isHoldersLoading, setIsHoldersLoading] = useState(false);
  const [isOrdersLoading, setIsOrdersLoading] = useState(false);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [selectedOutcomeId, setSelectedOutcomeId] = useState("");
  const [side, setSide] = useState<"buy" | "sell">("buy");
  const [orderEntryMode, setOrderEntryMode] = useState<"market" | "limit">("market");
  const [chartMode, setChartMode] = useState<"candles" | "line">("candles");
  const [amount, setAmount] = useState("25");
  const [quantity, setQuantity] = useState("25");
  const [price, setPrice] = useState("0.55");
  const [settlementRequestForm, setSettlementRequestForm] = useState<MarketSettlementRequestInput>({
    source_reference_url: "",
    notes: ""
  });
  const [disputeForm, setDisputeForm] = useState<MarketDisputeCreateInput>({
    title: "",
    reason: ""
  });
  const [evidenceDrafts, setEvidenceDrafts] = useState<Record<string, MarketDisputeEvidenceCreateInput>>({});
  const [disputeReviewDrafts, setDisputeReviewDrafts] = useState<Record<string, MarketDisputeReviewInput>>({});
  const [finalizeDraft, setFinalizeDraft] = useState<MarketOracleFinalizeInput>(buildDefaultFinalizeDraft);
  const { errorMessage, isSubmitting, runAction, setStatusMessage, statusMessage } = useAuthAction(
    "Load the market trading shell, then route signed-in orders through FastAPI."
  );
  const realtimeRefreshTimerRef = useRef<number | null>(null);
  const bootstrapSlugRef = useRef<string | null>(null);
  const [historyRefreshKey, setHistoryRefreshKey] = useState(0);

  const selectedQuote = useMemo(
    () => shell?.quotes.find((quote) => quote.outcome_id === selectedOutcomeId) ?? shell?.quotes[0] ?? null,
    [selectedOutcomeId, shell]
  );
  const selectedOrderBook = useMemo(
    () => shell?.order_books.find((book) => book.outcome_id === selectedOutcomeId) ?? shell?.order_books[0] ?? null,
    [selectedOutcomeId, shell]
  );

  const selectedOutcomeLabel = selectedQuote?.outcome_label ?? "Outcome";
  const canPlaceOrders = shell ? ["pending_liquidity", "open"].includes(shell.market.status) : false;
  const showDevOracleHarness = Boolean(backendUser?.is_admin && isDevelopmentBuild);
  const orderPreview = useMemo(
    () =>
      getTicketExecutionPreview({
        side,
        quantity,
        price,
        orderBook: selectedOrderBook
      }),
    [price, quantity, selectedOrderBook, side]
  );
  const winningOutcome = shell?.market.outcomes.find((outcome) => outcome.status === "winning") ?? null;
  const settlementSummary =
    shell?.market.status === "settled"
      ? winningOutcome
        ? `${winningOutcome.label} settled as the winning outcome. Active orders should be cancelled and collateral released into final payouts.`
        : "This market is settled. Final payouts have been posted."
      : null;
  const selectedStats = useMemo(() => getOutcomeMicroStats(selectedQuote, selectedOrderBook), [selectedOrderBook, selectedQuote]);
  const autoPrice = useMemo(() => {
    if (side === "buy") return selectedStats.best_ask ?? selectedStats.last_price ?? "0.5";
    return selectedStats.best_bid ?? selectedStats.last_price ?? "0.5";
  }, [side, selectedStats]);
  const autoShares = useMemo(() => {
    const p = Number(autoPrice);
    const a = Number(amount);
    if (!p || !a) return 0;
    return a / p;
  }, [amount, autoPrice]);
  const autoPayout = autoShares; // each share pays $1 if the outcome wins
  const hasLiquidity = useMemo(
    () => (side === "buy" ? !!selectedStats.best_ask : !!selectedStats.best_bid),
    [side, selectedStats]
  );
  const cumulativeBids = useMemo(
    () => buildCumulativeDepth(selectedOrderBook?.bids ?? []),
    [selectedOrderBook]
  );
  const cumulativeAsks = useMemo(
    () => buildCumulativeDepth(selectedOrderBook?.asks ?? []),
    [selectedOrderBook]
  );
  const maxBidDepth = useMemo(
    () => Math.max(0, ...cumulativeBids.map((level) => Number(level.cumulative_quantity))),
    [cumulativeBids]
  );
  const maxAskDepth = useMemo(
    () => Math.max(0, ...cumulativeAsks.map((level) => Number(level.cumulative_quantity))),
    [cumulativeAsks]
  );
  const resolutionSourceHost = useMemo(() => {
    const sourceUrl = shell?.market.settlement_reference_url;
    if (!sourceUrl) {
      return null;
    }
    try {
      return new URL(sourceUrl).hostname.replace(/^www\./, "");
    } catch {
      return sourceUrl;
    }
  }, [shell?.market.settlement_reference_url]);
  const closeCountdown = useMemo(
    () => formatCountdown(shell?.market.timing.trading_closes_at ?? null),
    [shell?.market.timing.trading_closes_at]
  );
  const resolutionCountdown = useMemo(
    () => formatCountdown(resolutionState?.finalizes_at ?? null),
    [resolutionState?.finalizes_at]
  );
  const resolutionSourceDisplay = useMemo(() => {
    return (
      resolutionState?.source_reference_url ||
      shell?.market.settlement_reference_url ||
      shell?.market.reference_context?.reference_source_label ||
      shell?.market.settlement_source?.base_url ||
      shell?.market.settlement_source?.name ||
      "Pending source reference"
    );
  }, [
    resolutionState?.source_reference_url,
    shell?.market.reference_context?.reference_source_label,
    shell?.market.settlement_reference_url,
    shell?.market.settlement_source?.base_url,
    shell?.market.settlement_source?.name
  ]);
  const contractSourceDisplay = useMemo(() => {
    return (
      shell?.market.reference_context?.reference_source_label ||
      shell?.market.settlement_reference_label ||
      shell?.market.settlement_source?.name ||
      resolutionSourceHost ||
      "Configured source"
    );
  }, [
    shell?.market.reference_context?.reference_source_label,
    shell?.market.settlement_reference_label,
    shell?.market.settlement_source?.name,
    resolutionSourceHost
  ]);
  const latestResolutionCandidate = resolutionState?.candidates[0] ?? null;
  const resolutionReviewState =
    typeof resolutionState?.current_payload?.dispute_review_state === "string"
      ? resolutionState.current_payload.dispute_review_state
      : resolutionState?.disputes[0]?.status ?? null;
  const reviewableDisputes = resolutionState?.disputes.filter((dispute) => ["open", "under_review"].includes(dispute.status)) ?? [];

  useEffect(() => {
    setOrderErrorHint("");
  }, [price, quantity, selectedOutcomeId, side]);
  const latestDisputeReference =
    typeof resolutionState?.current_payload?.latest_dispute_id === "string"
      ? resolutionState.current_payload.latest_dispute_id
      : resolutionState?.disputes[0]?.id ?? null;
  const oracleAdapterDisplay =
    (typeof latestResolutionCandidate?.payload.provider === "string" && latestResolutionCandidate.payload.provider) ||
    (typeof resolutionState?.current_payload?.provider === "string" && resolutionState.current_payload.provider) ||
    (resolutionState?.current_status === "pending_oracle" ? "mock_oracle" : "Pending");
  const oracleAssertionReference =
    (typeof latestResolutionCandidate?.payload.assertion_id === "string" && latestResolutionCandidate.payload.assertion_id) ||
    (typeof resolutionState?.current_payload?.assertion_id === "string" && resolutionState.current_payload.assertion_id) ||
    resolutionState?.candidate_id ||
    "Pending";
  const oracleChainId =
    typeof resolutionState?.current_payload?.chain_id === "number"
      ? resolutionState.current_payload.chain_id
      : typeof latestResolutionCandidate?.payload.chain_id === "number"
        ? latestResolutionCandidate.payload.chain_id
        : null;
  const oracleBondWei =
    (typeof resolutionState?.current_payload?.bond_wei === "string" && resolutionState.current_payload.bond_wei) ||
    (typeof latestResolutionCandidate?.payload.bond_wei === "string" && latestResolutionCandidate.payload.bond_wei) ||
    null;
  const oracleRewardWei =
    (typeof resolutionState?.current_payload?.reward_wei === "string" && resolutionState.current_payload.reward_wei) ||
    (typeof latestResolutionCandidate?.payload.reward_wei === "string" && latestResolutionCandidate.payload.reward_wei) ||
    null;
  const oracleLivenessDisplay =
    typeof resolutionState?.current_payload?.liveness_minutes === "number"
      ? `${resolutionState.current_payload.liveness_minutes} minutes`
      : typeof latestResolutionCandidate?.payload.liveness_minutes === "number"
        ? `${latestResolutionCandidate.payload.liveness_minutes} minutes`
        : resolutionCountdown;
  const oracleSubmissionStatus =
    (typeof resolutionState?.current_payload?.submission_status === "string" &&
      resolutionState.current_payload.submission_status) ||
    (typeof latestResolutionCandidate?.payload.submission_status === "string" &&
      latestResolutionCandidate.payload.submission_status) ||
    "Pending";
  const oracleTxHash =
    (typeof resolutionState?.current_payload?.tx_hash === "string" && resolutionState.current_payload.tx_hash) ||
    (typeof latestResolutionCandidate?.payload.tx_hash === "string" && latestResolutionCandidate.payload.tx_hash) ||
    "Not submitted";
  const oracleAssertionIdentifier =
    (typeof resolutionState?.current_payload?.assertion_identifier === "string" &&
      resolutionState.current_payload.assertion_identifier) ||
    (typeof latestResolutionCandidate?.payload.assertion_identifier === "string" &&
      latestResolutionCandidate.payload.assertion_identifier) ||
    "Not set";
  const canRequestSettlement = Boolean(session && shell && !["awaiting_resolution", "settled", "cancelled"].includes(shell.market.status));
  const canDisputeResolution = Boolean(session && shell && ["awaiting_resolution", "disputed"].includes(shell.market.status));
  const chartSeries = useMemo(
    () => buildHistoryChartSeries(history),
    [history]
  );
  const candleWidth = useMemo(() => Math.max(8, Math.min(18, 320 / Math.max(chartSeries.points.length, 1))), [chartSeries.points.length]);
  const immediateFillPercent = useMemo(() => {
    const immediate = Number(orderPreview.immediate_quantity);
    const requested = Number(quantity);
    if (!Number.isFinite(immediate) || !Number.isFinite(requested) || requested <= 0) {
      return 0;
    }
    return Math.max(0, Math.min(100, (immediate / requested) * 100));
  }, [orderPreview.immediate_quantity, quantity]);

  useEffect(() => {
    if (!shell) {
      return;
    }
    setSettlementRequestForm((current) => {
      if (current.source_reference_url) {
        return current;
      }
      const nextSource =
        shell.market.settlement_reference_url ||
        shell.market.settlement_source?.base_url ||
        "";
      if (!nextSource) {
        return current;
      }
      return {
        ...current,
        source_reference_url: nextSource
      };
    });
  }, [shell]);

  useEffect(() => {
    let isMounted = true;
    const slugChanged = bootstrapSlugRef.current !== slug;
    bootstrapSlugRef.current = slug;

    if (slugChanged) {
      setIsLoading(true);
    }
    setIsHoldersLoading(true);
    setIsOrdersLoading(Boolean(session));

    const run = async () => {
      try {
        const accessToken = session ? await getAccessToken() : null;
        const bootstrap = await beyulApiFetch<MarketDetailBootstrap>(`/api/v1/markets/${slug}/bootstrap`, {
          accessToken
        });
        const nextShell = bootstrap.shell;
        if (!isMounted) {
          return;
        }
        setShell(nextShell);
        setSelectedOutcomeId((current) => current || nextShell.quotes[0]?.outcome_id || nextShell.market.outcomes[0]?.id || "");
        setStatusMessage(`Loaded trading shell for ${nextShell.market.slug}.`);
        setHolders(bootstrap.holders);
        setResolutionState(bootstrap.resolution_state);
        setBackendUser(bootstrap.backend_user);
        setPortfolio(bootstrap.portfolio);
        setMyOrders(bootstrap.my_orders ?? []);
      } catch (error) {
        if (isMounted) {
          setStatusMessage(error instanceof Error ? error.message : "Failed to load market trading shell.");
          setShell(null);
        }
        if (isMounted) {
          setHolders(null);
          setResolutionState(null);
          setBackendUser(null);
          setPortfolio(null);
          setMyOrders([]);
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
          setIsHoldersLoading(false);
          setIsOrdersLoading(false);
        }
      }
    };

    void run();

    return () => {
      isMounted = false;
    };
  }, [getAccessToken, session, setStatusMessage, slug]);

  useEffect(() => {
    let isMounted = true;

    const loadHistory = async () => {
      if (!shell || !selectedOutcomeId) {
        if (isMounted) {
          setHistory(null);
          setHistoryError(null);
          setIsHistoryLoading(false);
        }
        return;
      }

      setIsHistoryLoading(true);
      try {
        const params = new URLSearchParams({
          outcome_id: selectedOutcomeId,
          range: historyRange
        });
        const nextHistory = await beyulApiFetch<MarketHistory>(`/api/v1/markets/${slug}/history?${params.toString()}`);
        if (isMounted) {
          setHistory(nextHistory);
          setHistoryError(null);
        }
      } catch (error) {
        if (isMounted) {
          setHistory(null);
          setHistoryError(error instanceof Error ? error.message : "Failed to load market history.");
        }
      } finally {
        if (isMounted) {
          setIsHistoryLoading(false);
        }
      }
    };

    void loadHistory();

    return () => {
      isMounted = false;
    };
  }, [historyRange, historyRefreshKey, selectedOutcomeId, shell, slug]);

  useEffect(() => {
    if (!shell) {
      return;
    }
    setFinalizeDraft((current) => ({
      winning_outcome_id: current.winning_outcome_id || shell.market.outcomes[0]?.id || "",
      candidate_id: current.candidate_id || resolutionState?.candidate_id || "",
      source_reference_url:
        current.source_reference_url || resolutionState?.source_reference_url || shell.market.settlement_reference_url || "",
      notes: current.notes || ""
    }));
  }, [resolutionState?.candidate_id, resolutionState?.source_reference_url, shell]);

  const refreshShellAndOrders = async () => {
    const [nextShell, accessToken] = await Promise.all([
      beyulApiFetch<MarketTradingShell>(`/api/v1/markets/${slug}/trading-shell`),
      getAccessToken()
    ]);
    setShell(nextShell);
    setHistoryRefreshKey((current) => current + 1);
    const holdersPromise = beyulApiFetch<MarketHolders>(`/api/v1/markets/${slug}/holders?limit=12`).catch(() => null);
    const resolutionPromise = beyulApiFetch<MarketResolutionState>(`/api/v1/markets/${slug}/resolution`).catch(() => null);
    if (accessToken) {
      const [nextOrders, nextPortfolio, nextHolders, nextResolutionState] = await Promise.all([
        beyulApiFetch<MarketOrder[]>(`/api/v1/markets/${slug}/orders/me`, { accessToken }),
        beyulApiFetch<PortfolioSummary>("/api/v1/portfolio/me", { accessToken }),
        holdersPromise,
        resolutionPromise
      ]);
      setMyOrders(nextOrders);
      setPortfolio(nextPortfolio);
      setHolders(nextHolders);
      setResolutionState(nextResolutionState);
      return;
    }
    setHolders(await holdersPromise);
    setResolutionState(await resolutionPromise);
  };

  useEffect(() => {
    return () => {
      if (realtimeRefreshTimerRef.current !== null) {
        window.clearTimeout(realtimeRefreshTimerRef.current);
      }
    };
  }, []);

  const scheduleRealtimeRefresh = () => {
    if (realtimeRefreshTimerRef.current !== null) {
      return;
    }

    realtimeRefreshTimerRef.current = window.setTimeout(() => {
      realtimeRefreshTimerRef.current = null;
      void refreshShellAndOrders().catch((error) => {
        setStatusMessage(error instanceof Error ? error.message : "Failed to refresh market after live event.");
      });
    }, 200);
  };

  const { connectionState } = useMarketLiveEvents({
    marketId: shell?.market.id ?? null,
    enabled: Boolean(shell),
    onEvent: (event) => {
      if (event.event_type === "subscribed") {
        return;
      }
      scheduleRealtimeRefresh();
    }
  });

  const marketPositions = portfolio?.positions.filter((position) => position.market_id === shell?.market.id) ?? [];
  const marketBalances = portfolio?.balances ?? [];

  const updateMarketStatus = async (status: Market["status"]) => {
    const accessToken = await getAccessToken();
    const updatedMarket = await beyulApiFetch<Market>(`/api/v1/markets/${slug}/status`, {
      method: "POST",
      accessToken,
      json: { status }
    });
    setShell((current) => (current ? { ...current, market: updatedMarket } : current));
    return updatedMarket;
  };

  const postDevOracleAction = async <T,>(path: string, payload: unknown): Promise<T> => {
    const accessToken = await getAccessToken();
    if (!accessToken) {
      throw new Error("Sign in to use dev oracle controls.");
    }
    const response = await fetch(path, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${accessToken}`
      },
      body: JSON.stringify(payload),
      cache: "no-store"
    });
    const rawBody = await response.text();
    const body = rawBody ? parseResponseBody(rawBody) : null;
    if (!response.ok) {
      throw new Error(getApiErrorDetail(body) || response.statusText || "Dev oracle action failed.");
    }
    return body as T;
  };

  const priceChartSection = (
    <section className="auth-section market-chart-section">
      <h2>Price chart</h2>
      {isHistoryLoading && !history ? (
        <p>Loading chart...</p>
      ) : historyError ? (
        <p>{historyError}</p>
      ) : chartSeries.points.length === 0 ? (
        <p>No trade history yet for the selected outcome.</p>
      ) : (
        <>
          <div className="chart-shell">
            <div className="chart-header">
              <div className="chart-heading">
                <strong>{selectedOutcomeLabel}</strong>
                <span className="pill">
                  {chartSeries.latest_probability ? `${Math.round(Number(chartSeries.latest_probability))}% implied` : "No probability"}
                </span>
                {history ? <span className="pill">{formatHistoryInterval(history.interval_seconds)}</span> : null}
              </div>
              <div className="range-switcher" role="tablist" aria-label="Market history range">
                {historyRangeOptions.map((option) => (
                  <button
                    aria-selected={option === historyRange}
                    className={`range-pill ${option === historyRange ? "is-active" : ""}`}
                    key={option}
                    onClick={() => setHistoryRange(option)}
                    type="button"
                  >
                    {option}
                  </button>
                ))}
              </div>
            </div>
            <div className="chart-mode-toggle" role="tablist" aria-label="Chart display mode">
              <button
                type="button"
                role="tab"
                aria-selected={chartMode === "candles"}
                className={`chart-mode-pill ${chartMode === "candles" ? "is-active" : ""}`}
                onClick={() => setChartMode("candles")}
              >
                Candles
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={chartMode === "line"}
                className={`chart-mode-pill ${chartMode === "line" ? "is-active" : ""}`}
                onClick={() => setChartMode("line")}
              >
                Line
              </button>
            </div>
            <div className="chart-panel">
              <span className="chart-label">{chartMode === "candles" ? "Candle buckets" : "Probability history"}</span>
              <InteractiveChart series={chartSeries} history={history} mode={chartMode} candleWidth={candleWidth} />
            </div>
            <div className="chart-panel">
              <span className="chart-label">Volume bars</span>
              <svg className="chart-svg" viewBox="0 0 360 120" role="img" aria-label="Volume bars">
                {chartSeries.points.map((point) => (
                  <rect
                    className="volume-bar"
                    key={`volume-${point.bucket_key}`}
                    x={Math.max(0, point.x - candleWidth / 2)}
                    y={120 - point.volume_height}
                    width={candleWidth}
                    height={point.volume_height}
                    rx="4"
                  />
                ))}
              </svg>
            </div>
          </div>
          <div className="metric-grid compact-metrics">
            <article className="metric-card">
              <span>Latest implied probability</span>
              <strong>{chartSeries.latest_probability ? `${Math.round(Number(chartSeries.latest_probability))}%` : "N/A"}</strong>
            </article>
            <article className="metric-card">
              <span>Latest close</span>
              <strong>{chartSeries.latest_close ? formatPrice(chartSeries.latest_close) : "N/A"}</strong>
            </article>
            <article className="metric-card">
              <span>Window high / low</span>
              <strong>
                {chartSeries.high_price && chartSeries.low_price
                  ? `${formatPrice(chartSeries.high_price)} / ${formatPrice(chartSeries.low_price)}`
                  : "N/A"}
              </strong>
            </article>
            <article className="metric-card">
              <span>Window volume</span>
              <strong>{formatNumber(chartSeries.total_volume)}</strong>
            </article>
            <article className="metric-card">
              <span>Buckets charted</span>
              <strong>{chartSeries.points.length}</strong>
            </article>
          </div>
        </>
      )}
    </section>
  );

  if (!isLoading && !shell) {
    return (
      <div className="market-detail-layout">
        <div className="market-detail-main">
          <section className="auth-section">
            <div className="entity-card">
              <div className="entity-card-header">
                <strong>Market not found</strong>
                <span className="pill">Unavailable</span>
              </div>
              <p>This market could not be loaded. The slug may be stale, the market may have been removed, or the backend returned no trading shell for it.</p>
              <dl className="kv-list compact">
                <div>
                  <dt>Requested slug</dt>
                  <dd>{slug}</dd>
                </div>
              </dl>
              <div className="button-row">
                <Link className="button-primary hero-link" href="/markets">
                  Back to markets
                </Link>
              </div>
            </div>
            <AuthFeedback errorMessage={errorMessage} statusMessage={statusMessage} />
          </section>
        </div>
        <div className="market-detail-sidebar" />
      </div>
    );
  }

  return (
    <div className="market-detail-layout">
      <div className="market-detail-main">
      <section className="auth-section market-shell-section">
        {isLoading ? (
          <p>Loading market...</p>
        ) : shell ? (
          <>
            <div className="market-header-top">
              <div className="market-summary-meta">
                <span className={`market-status-badge market-status-${shell.market.status.replace(/_/g, "-")}`}>
                  {shell.market.status === "open" ? "● Live" : shell.market.status.replace(/_/g, " ")}
                </span>
                {shell.market.community_name ? (
                  <span className="market-meta-chip">{shell.market.community_name}</span>
                ) : null}
                <span className="market-meta-chip">{shell.market.rail_mode}</span>
                <span className="market-meta-chip">{connectionState}</span>
              </div>
              {backendUser?.is_admin ? (
                <div className="button-row market-admin-actions">
                  {shell.market.status === "pending_liquidity" ? (
                    <button
                      className="button-primary"
                      disabled={isSubmitting}
                      type="button"
                      onClick={() =>
                        void runAction("Opening market for trading...", () => updateMarketStatus("open"), {
                          successMessage: "Market is now open for trading."
                        })
                      }
                    >
                      Open trading
                    </button>
                  ) : null}
                  {shell.market.status === "open" ? (
                    <button
                      className="button-secondary"
                      disabled={isSubmitting}
                      type="button"
                      onClick={() =>
                        void runAction("Pausing market...", () => updateMarketStatus("trading_paused"), {
                          successMessage: "Market trading is paused."
                        })
                      }
                    >
                      Pause
                    </button>
                  ) : null}
                  {shell.market.status === "trading_paused" ? (
                    <button
                      className="button-primary"
                      disabled={isSubmitting}
                      type="button"
                      onClick={() =>
                        void runAction("Re-opening market...", () => updateMarketStatus("open"), {
                          successMessage: "Market re-opened."
                        })
                      }
                    >
                      Resume
                    </button>
                  ) : null}
                  {shell.market.status !== "cancelled" ? (
                    <button
                      className="button-secondary"
                      disabled={isSubmitting || !["pending_liquidity", "open", "trading_paused"].includes(shell.market.status)}
                      type="button"
                      onClick={() =>
                        void runAction("Cancelling market...", () => updateMarketStatus("cancelled"), {
                          successMessage: "Market cancelled."
                        })
                      }
                    >
                      Cancel
                    </button>
                  ) : null}
                </div>
              ) : null}
            </div>

            <div className="market-header-identity">
              <MarketIcon market={shell.market} size={56} />
              <h2 className="market-hero-title">{shell.market.title}</h2>
            </div>
            <p className="market-shell-question">{shell.market.question}</p>

            <dl className="market-shell-kv">
              <div>
                <dt>Last</dt>
                <dd>{formatPrice(selectedStats.last_price)}</dd>
              </div>
              <div>
                <dt>Best bid</dt>
                <dd>{formatPrice(selectedStats.best_bid)}</dd>
              </div>
              <div>
                <dt>Best ask</dt>
                <dd>{formatPrice(selectedStats.best_ask)}</dd>
              </div>
              <div>
                <dt>Trades</dt>
                <dd>{shell.market.total_trades_count}</dd>
              </div>
              <div>
                <dt>Closes</dt>
                <dd>{closeCountdown}</dd>
              </div>
              {shell.market.reference_context?.price_to_beat ? (
                <div>
                  <dt>Price to beat</dt>
                  <dd>{formatContractValue(shell.market.reference_context.price_to_beat)}</dd>
                </div>
              ) : null}
              {resolutionSourceHost ? (
                <div>
                  <dt>Source</dt>
                  <dd>{resolutionSourceHost}</dd>
                </div>
              ) : null}
            </dl>

            <details className="market-rules-details">
              <summary className="market-rules-summary">Resolution rules</summary>
              <div className="market-rules-block">
                <p>{shell.market.rules_text}</p>
              </div>
            </details>
          </>
        ) : (
          <p>Market not found.</p>
        )}
      </section>

      {resolutionState?.current_status ? (
        <section className="auth-section market-resolution-progress">
          <h2>Resolution progress</h2>
          <div className="entity-list">
            <article className="entity-card">
              <div className="entity-card-header">
                <strong>Current oracle state</strong>
                <span className="pill">{resolutionState.current_status}</span>
              </div>
              <dl className="kv-list compact">
                <div>
                  <dt>Candidate ID</dt>
                  <dd>{resolutionState.candidate_id || "Not assigned"}</dd>
                </div>
                <div>
                  <dt>Finalizes</dt>
                  <dd>
                    {resolutionState.finalizes_at ? formatMarketTime(resolutionState.finalizes_at) : "Not scheduled"}
                  </dd>
                </div>
                <div>
                  <dt>Countdown</dt>
                  <dd>{resolutionCountdown}</dd>
                </div>
                <div>
                  <dt>Source</dt>
                  <dd>{resolutionSourceDisplay}</dd>
                </div>
                <div>
                  <dt>Dispute window</dt>
                  <dd>
                    {shell?.market.timing.dispute_window_ends_at
                      ? formatMarketTime(shell.market.timing.dispute_window_ends_at)
                      : "Not scheduled"}
                  </dd>
                </div>
                <div>
                  <dt>Resolution due</dt>
                  <dd>
                    {shell?.market.timing.resolution_due_at
                      ? formatMarketTime(shell.market.timing.resolution_due_at)
                      : "Not scheduled"}
                  </dd>
                </div>
              </dl>
              <div className="resolution-stage-list" aria-label="Resolution progress stages">
                <div className="resolution-stage is-complete">
                  <strong>1</strong>
                  <span>Requested</span>
                </div>
                <div
                  className={`resolution-stage ${
                    resolutionState.current_status === "pending_oracle"
                      ? "is-active"
                      : ["disputed", "finalized"].includes(resolutionState.current_status)
                        ? "is-complete"
                        : ""
                  }`}
                >
                  <strong>2</strong>
                  <span>Oracle window</span>
                </div>
                <div
                  className={`resolution-stage ${
                    resolutionState.current_status === "disputed"
                      ? "is-active"
                      : resolutionState.current_status === "finalized" && latestDisputeReference
                        ? "is-complete"
                        : ""
                  }`}
                >
                  <strong>3</strong>
                  <span>Dispute review</span>
                </div>
                <div className={`resolution-stage ${resolutionState.current_status === "finalized" ? "is-complete" : ""}`}>
                  <strong>4</strong>
                  <span>Finalized</span>
                </div>
              </div>
            </article>
            <article className="entity-card">
              <div className="entity-card-header">
                <strong>Oracle metadata</strong>
                <span className="pill">{oracleAdapterDisplay}</span>
              </div>
              <dl className="kv-list compact">
                <div>
                  <dt>Assertion reference</dt>
                  <dd>{oracleAssertionReference}</dd>
                </div>
                <div>
                  <dt>Latest dispute</dt>
                  <dd>{latestDisputeReference || "No disputes"}</dd>
                </div>
                <div>
                  <dt>Review state</dt>
                  <dd>{resolutionReviewState || "No active review"}</dd>
                </div>
                <div>
                  <dt>Payload status</dt>
                  <dd>
                    {typeof resolutionState.current_payload.status === "string"
                      ? resolutionState.current_payload.status
                      : resolutionState.current_status || "Unavailable"}
                  </dd>
                </div>
                <div>
                  <dt>Chain ID</dt>
                  <dd>{oracleChainId ?? "Pending"}</dd>
                </div>
                <div>
                  <dt>Bond</dt>
                  <dd>{oracleBondWei ?? "Pending"}</dd>
                </div>
                <div>
                  <dt>Reward</dt>
                  <dd>{oracleRewardWei ?? "Pending"}</dd>
                </div>
                <div>
                  <dt>Liveness</dt>
                  <dd>{oracleLivenessDisplay}</dd>
                </div>
                <div>
                  <dt>Submission status</dt>
                  <dd>{oracleSubmissionStatus}</dd>
                </div>
                <div>
                  <dt>Assertion identifier</dt>
                  <dd>{oracleAssertionIdentifier}</dd>
                </div>
                <div>
                  <dt>Tx hash</dt>
                  <dd>{oracleTxHash}</dd>
                </div>
              </dl>
            </article>
            {resolutionState.candidates.map((candidate) => (
              <article className="entity-card" key={candidate.id}>
                <div className="entity-card-header">
                  <strong>Resolution candidate</strong>
                  <span className="pill">{candidate.status}</span>
                </div>
                <dl className="kv-list compact">
                  <div>
                    <dt>Candidate ID</dt>
                    <dd>{candidate.id}</dd>
                  </div>
                  <div>
                    <dt>Proposed at</dt>
                    <dd>{formatMarketTime(candidate.proposed_at)}</dd>
                  </div>
                  <div>
                    <dt>Requested source</dt>
                    <dd>{candidate.source_reference_url || resolutionSourceDisplay}</dd>
                  </div>
                  <div>
                    <dt>Proposal notes</dt>
                    <dd>{candidate.source_reference_text || "None"}</dd>
                  </div>
                  <div>
                    <dt>Oracle adapter</dt>
                    <dd>{typeof candidate.payload.provider === "string" ? candidate.payload.provider : oracleAdapterDisplay}</dd>
                  </div>
                  <div>
                    <dt>Assertion reference</dt>
                    <dd>{typeof candidate.payload.assertion_id === "string" ? candidate.payload.assertion_id : candidate.id}</dd>
                  </div>
                </dl>
              </article>
            ))}
            {resolutionState.disputes.map((dispute) => (
              <article className="entity-card" key={dispute.id}>
                <div className="entity-card-header">
                  <strong>Dispute</strong>
                  <span className="pill">{dispute.status}</span>
                </div>
                <dl className="kv-list compact">
                  <div>
                    <dt>Title</dt>
                    <dd>{dispute.title}</dd>
                  </div>
                  <div>
                    <dt>Opened</dt>
                    <dd>{formatMarketTime(dispute.opened_at)}</dd>
                  </div>
                  <div>
                    <dt>Reason</dt>
                    <dd>{dispute.reason}</dd>
                  </div>
                  <div>
                    <dt>Closed</dt>
                    <dd>{dispute.closed_at ? formatMarketTime(dispute.closed_at) : "Still active"}</dd>
                  </div>
                  <div>
                    <dt>Review notes</dt>
                    <dd>{dispute.review_notes || "Pending review"}</dd>
                  </div>
                </dl>
                <div className="dispute-evidence-block">
                  <div className="entity-card-header">
                    <strong>Evidence</strong>
                    <span className="pill">{dispute.evidence.length}</span>
                  </div>
                  {dispute.evidence.length === 0 ? (
                    <p>No evidence attached yet.</p>
                  ) : (
                    <div className="dispute-evidence-list">
                      {dispute.evidence.map((evidence) => (
                        <article className="dispute-evidence-item" key={evidence.id}>
                          <div className="entity-card-header">
                            <strong>{formatEvidenceTypeLabel(evidence.evidence_type)}</strong>
                            <span className="pill">{formatMarketTime(evidence.created_at)}</span>
                          </div>
                          {evidence.description ? <p>{evidence.description}</p> : null}
                          {evidence.url ? (
                            <a className="inline-link" href={evidence.url} rel="noreferrer" target="_blank">
                              {evidence.url}
                            </a>
                          ) : null}
                          {Object.keys(evidence.payload ?? {}).length ? (
                            <pre className="inline-json">{JSON.stringify(evidence.payload, null, 2)}</pre>
                          ) : null}
                        </article>
                      ))}
                    </div>
                  )}
                  {session && ["open", "under_review"].includes(dispute.status) ? (
                    <form
                      className="auth-form compact-form"
                      onSubmit={(event) => {
                        event.preventDefault();
                        const draft = evidenceDrafts[dispute.id] ?? buildDefaultEvidenceDraft();
                        void runAction(
                          "Attaching dispute evidence...",
                          async () => {
                            const accessToken = await getAccessToken();
                            await beyulApiFetch(`/api/v1/markets/${slug}/disputes/${dispute.id}/evidence`, {
                              method: "POST",
                              accessToken,
                              json: {
                                evidence_type: draft.evidence_type,
                                url: draft.url,
                                description: draft.description,
                                payload: draft.payload ?? {}
                              }
                            });
                            await refreshShellAndOrders();
                            setEvidenceDrafts((current) => ({
                              ...current,
                              [dispute.id]: buildDefaultEvidenceDraft()
                            }));
                            return true;
                          },
                          {
                            successMessage: "Evidence attached to the dispute."
                          }
                        );
                      }}
                    >
                      {(() => {
                        const draft = evidenceDrafts[dispute.id] ?? buildDefaultEvidenceDraft();
                        const trimmedUrl = draft.url?.trim() ?? "";
                        const trimmedDescription = draft.description?.trim() ?? "";
                        const evidenceType = draft.evidence_type;
                        const isEvidenceValid =
                          evidenceType.trim().length > 0 &&
                          (!evidenceTypeRequiresUrl(evidenceType) || trimmedUrl.length > 0) &&
                          (!evidenceTypeRequiresDescription(evidenceType) || trimmedDescription.length > 0) &&
                          (trimmedUrl.length > 0 || trimmedDescription.length > 0);
                        return (
                          <>
                      <div className="field">
                        <label htmlFor={`evidence-type-${dispute.id}`}>Evidence type</label>
                        <select
                          id={`evidence-type-${dispute.id}`}
                          value={evidenceDrafts[dispute.id]?.evidence_type ?? "source_link"}
                          onChange={(event) =>
                            setEvidenceDrafts((current) => ({
                              ...current,
                              [dispute.id]: {
                                evidence_type: event.target.value as EvidenceType,
                                url: current[dispute.id]?.url ?? "",
                                description: current[dispute.id]?.description ?? "",
                                payload: current[dispute.id]?.payload ?? {}
                              }
                            }))
                          }
                        >
                          {evidenceTypeOptions.map((option) => (
                            <option key={option.value} value={option.value}>
                              {option.label}
                            </option>
                          ))}
                        </select>
                      </div>
                      <div className="field">
                        <label htmlFor={`evidence-url-${dispute.id}`}>Evidence URL</label>
                        <input
                          id={`evidence-url-${dispute.id}`}
                          placeholder="https://..."
                          value={evidenceDrafts[dispute.id]?.url ?? ""}
                          onChange={(event) =>
                            setEvidenceDrafts((current) => ({
                              ...current,
                              [dispute.id]: {
                                evidence_type: current[dispute.id]?.evidence_type ?? "source_link",
                                url: event.target.value,
                                description: current[dispute.id]?.description ?? "",
                                payload: current[dispute.id]?.payload ?? {}
                              }
                            }))
                          }
                        />
                      </div>
                      <div className="field">
                        <label htmlFor={`evidence-description-${dispute.id}`}>Description</label>
                        <textarea
                          id={`evidence-description-${dispute.id}`}
                          rows={2}
                          placeholder="Why this evidence matters for the dispute."
                          value={evidenceDrafts[dispute.id]?.description ?? ""}
                          onChange={(event) =>
                            setEvidenceDrafts((current) => ({
                              ...current,
                              [dispute.id]: {
                                evidence_type: current[dispute.id]?.evidence_type ?? "source_link",
                                url: current[dispute.id]?.url ?? "",
                                description: event.target.value,
                                payload: current[dispute.id]?.payload ?? {}
                              }
                            }))
                          }
                        />
                      </div>
                      {evidenceTypeRequiresUrl(evidenceType) ? (
                        <p className="field-hint">This evidence type requires a URL.</p>
                      ) : null}
                      {evidenceTypeRequiresDescription(evidenceType) ? (
                        <p className="field-hint">This evidence type requires a description.</p>
                      ) : null}
                      <div className="button-row">
                        <button
                          className="button-secondary"
                          disabled={isSubmitting || !isEvidenceValid}
                          type="submit"
                        >
                          Attach evidence
                        </button>
                      </div>
                          </>
                        );
                      })()}
                    </form>
                  ) : null}
                </div>
              </article>
            ))}
            {resolutionState.history.length ? (
              <article className="entity-card resolution-history-card">
                <div className="entity-card-header">
                  <strong>Resolution history</strong>
                  <span className="pill">{resolutionState.history.length}</span>
                </div>
                <div className="resolution-history-list">
                  {resolutionState.history.map((event) => (
                    <article className="resolution-history-item" key={event.id}>
                      <div className="entity-card-header">
                        <strong>{event.title}</strong>
                        <span className="pill">{event.status}</span>
                      </div>
                      <dl className="kv-list compact">
                        <div>
                          <dt>Event</dt>
                          <dd>{formatResolutionEventLabel(event.event_type)}</dd>
                        </div>
                        <div>
                          <dt>Occurred</dt>
                          <dd>{formatMarketTime(event.occurred_at)}</dd>
                        </div>
                        <div>
                          <dt>Reference</dt>
                          <dd>{event.reference_id || "None"}</dd>
                        </div>
                        {Object.keys(event.details ?? {}).length ? (
                          <div>
                            <dt>Details</dt>
                            <dd>
                              <pre className="inline-json">{JSON.stringify(event.details, null, 2)}</pre>
                            </dd>
                          </div>
                        ) : null}
                      </dl>
                    </article>
                  ))}
                </div>
              </article>
            ) : null}
          </div>
        </section>
      ) : null}

      {priceChartSection}

      {(canDisputeResolution || (resolutionState?.disputes.length ?? 0) > 0) && shell?.market.status !== "settled" ? (
        <section className="auth-section market-dispute-section">
          <h2>Disputes</h2>
          {!session ? (
            <p>Sign in to challenge a pending oracle candidate.</p>
          ) : resolutionState?.disputes.length ? (
            <p>
              There {resolutionState.disputes.length === 1 ? "is" : "are"} currently {resolutionState.disputes.length} open
              or historical dispute{resolutionState.disputes.length === 1 ? "" : "s"} on this market.
            </p>
          ) : (
            <p>No disputes have been raised on this market yet.</p>
          )}
          {!session ? (
            <div className="button-row">
              <Link className="button-primary hero-link" href="/auth/sign-in">
                Sign in to dispute
              </Link>
            </div>
          ) : canDisputeResolution ? (
            <form
              className="auth-form"
              onSubmit={(event) => {
                event.preventDefault();
                void runAction(
                  "Raising dispute...",
                  async () => {
                    const accessToken = await getAccessToken();
                    await beyulApiFetch(`/api/v1/markets/${slug}/disputes`, {
                      method: "POST",
                      accessToken,
                      json: disputeForm
                    });
                    await refreshShellAndOrders();
                    setDisputeForm({ title: "", reason: "" });
                    return true;
                  },
                  {
                    successMessage: "Dispute raised. The market is now in a disputed state."
                  }
                );
              }}
            >
              <div className="field">
                <label htmlFor="dispute-title">Dispute title</label>
                <input
                  id="dispute-title"
                  placeholder="Source mismatch"
                  value={disputeForm.title}
                  onChange={(event) => setDisputeForm((current) => ({ ...current, title: event.target.value }))}
                />
              </div>
              <div className="field">
                <label htmlFor="dispute-reason">Dispute reason</label>
                <textarea
                  id="dispute-reason"
                  rows={3}
                  placeholder="Explain why the pending oracle candidate should be challenged."
                  value={disputeForm.reason}
                  onChange={(event) => setDisputeForm((current) => ({ ...current, reason: event.target.value }))}
                />
              </div>
              <p>Disputes are for challenging the active resolution candidate, not for directly selecting the winner.</p>
              <div className="button-row">
                <button
                  className="button-secondary"
                  disabled={isSubmitting || !disputeForm.title.trim() || !disputeForm.reason.trim()}
                  type="submit"
                >
                  Raise dispute
                </button>
              </div>
            </form>
          ) : (
            <p>Disputes can only be raised while the market is awaiting oracle resolution or already under dispute.</p>
          )}
        </section>
      ) : null}

      {settlementSummary ? (
        <section className="auth-section market-settlement-summary">
          <div className="entity-card-header">
            <h2>Settled</h2>
            <span className="pill pill-settled">Resolved</span>
          </div>
          <p>{settlementSummary}</p>
          <div className="metric-grid compact-metrics">
            <article className="metric-card">
              <span>Winning outcome</span>
              <strong>{winningOutcome?.label || "Unavailable"}</strong>
            </article>
            <article className="metric-card">
              <span>Settlement value</span>
              <strong>{winningOutcome?.settlement_value ?? "1"}</strong>
            </article>
          </div>
        </section>
      ) : null}

      <section className="auth-section market-outcomes-section">
        {isLoading ? (
          <p>Loading...</p>
        ) : shell ? (
          <div className="market-outcome-strip">
            {shell.quotes.map((quote) => (
              <button
                className={`outcome-btn ${quote.outcome_id === selectedOutcomeId ? "is-active" : ""}`}
                key={quote.outcome_id}
                type="button"
                onClick={() => {
                  setSelectedOutcomeId(quote.outcome_id);
                  if (quote.best_ask) setPrice(quote.best_ask);
                  else if (quote.best_bid) setPrice(quote.best_bid);
                }}
              >
                <span className="outcome-btn-label">{quote.outcome_label}</span>
                <span className="outcome-btn-price">{formatPrice(quote.last_price)}</span>
                <span className="outcome-btn-meta">
                  B {formatPrice(quote.best_bid)} · A {formatPrice(quote.best_ask)} · Vol {formatNumber(quote.traded_volume)}
                </span>
              </button>
            ))}
          </div>
        ) : (
          <p>No market pricing is available yet.</p>
        )}
      </section>

      <div className="market-board-grid">
      <div className="book-panel market-book-section">
        <div className="book-col-head">
          <span>Order book{selectedOrderBook ? ` · ${selectedOrderBook.outcome_label}` : ""}</span>
          <span>Size</span>
          <span>Total</span>
        </div>
        {!selectedOrderBook ? (
          <p className="book-empty">Select an outcome to see the depth ladder.</p>
        ) : (
          <>
            {cumulativeAsks.length === 0 ? (
              <p className="book-empty">No resting ask liquidity.</p>
            ) : (
              <>
                {[...cumulativeAsks].reverse().map((level) => {
                  const pct = maxAskDepth > 0 ? (Number(level.cumulative_quantity) / maxAskDepth) * 100 : 0;
                  return (
                    <div className="book-row ask-row" key={`ask-${level.price}`}>
                      <div className="book-fill ask-fill" style={{ width: `${pct}%` }} />
                      <span className="book-price ask-price">{formatPrice(level.price)}</span>
                      <span>{formatNumber(level.quantity)}</span>
                      <span>{formatNumber(level.cumulative_quantity)}</span>
                    </div>
                  );
                })}
              </>
            )}
            <div className="book-spread-row">
              <span>Spread</span>
              <span>
                {selectedStats.best_ask && selectedStats.best_bid
                  ? `${Math.round((Number(selectedStats.best_ask) - Number(selectedStats.best_bid)) * 100)}¢`
                  : "—"}
              </span>
            </div>
            {cumulativeBids.length === 0 ? (
              <p className="book-empty">No resting bid liquidity.</p>
            ) : (
              <>
                {cumulativeBids.map((level) => {
                  const pct = maxBidDepth > 0 ? (Number(level.cumulative_quantity) / maxBidDepth) * 100 : 0;
                  return (
                    <div className="book-row bid-row" key={`bid-${level.price}`}>
                      <div className="book-fill bid-fill" style={{ width: `${pct}%` }} />
                      <span className="book-price bid-price">{formatPrice(level.price)}</span>
                      <span>{formatNumber(level.quantity)}</span>
                      <span>{formatNumber(level.cumulative_quantity)}</span>
                    </div>
                  );
                })}
              </>
            )}
          </>
        )}
      </div>

      <div className="market-stats-panel market-stats-section">
        {!selectedQuote ? (
          <p className="book-empty">Select an outcome above to see stats.</p>
        ) : (
          <>
            <div className="price-rail">
              <div className="price-rail-track" />
              {selectedStats.best_bid ? (
                <div className="price-rail-marker bid-marker" style={{ left: `${Number(selectedStats.best_bid) * 100}%` }}>
                  <span>Bid</span>
                </div>
              ) : null}
              {selectedStats.mid_price ? (
                <div className="price-rail-marker mid-marker" style={{ left: `${Number(selectedStats.mid_price) * 100}%` }}>
                  <span>Mid</span>
                </div>
              ) : null}
              {selectedStats.best_ask ? (
                <div className="price-rail-marker ask-marker" style={{ left: `${Number(selectedStats.best_ask) * 100}%` }}>
                  <span>Ask</span>
                </div>
              ) : null}
            </div>
            <div className="metric-grid compact-metrics">
              <article className="metric-card">
                <span>Last</span>
                <strong>{formatPrice(selectedStats.last_price)}</strong>
              </article>
              <article className="metric-card">
                <span>Best bid</span>
                <strong>{formatPrice(selectedStats.best_bid)}</strong>
              </article>
              <article className="metric-card">
                <span>Best ask</span>
                <strong>{formatPrice(selectedStats.best_ask)}</strong>
              </article>
              <article className="metric-card">
                <span>Spread</span>
                <strong>{selectedStats.spread ? formatPrice(selectedStats.spread) : "—"}</strong>
              </article>
              <article className="metric-card">
                <span>Mid-price</span>
                <strong>{selectedStats.mid_price ? formatPrice(selectedStats.mid_price) : "—"}</strong>
              </article>
              <article className="metric-card">
                <span>Depth</span>
                <strong>{formatNumber(selectedStats.displayed_depth)}</strong>
              </article>
            </div>
          </>
        )}
      </div>
      </div>

      <div className="market-lower-grid">
      <div className="trade-tape market-tape-section">
        <div className="trade-tape-head">
          <span>Trade tape</span>
          <span>Price</span>
          <span>Size</span>
          <span>Gross</span>
          <span>Time</span>
        </div>
        {!shell || shell.recent_trades.length === 0 ? (
          <p className="book-empty">{!shell ? "Loading..." : "No trades yet."}</p>
        ) : (
          shell.recent_trades.map((trade) => (
            <article className="trade-tape-row" key={trade.id}>
              <strong>{trade.outcome_label}</strong>
              <span>{formatPrice(trade.price)}</span>
              <span>{formatNumber(trade.quantity)}</span>
              <span>{formatNumber(trade.gross_notional)}</span>
              <span>{formatTradeTime(trade.executed_at)}</span>
            </article>
          ))
        )}
      </div>

      <section className="auth-section market-orders-section">
        <h2>Your orders</h2>
        {isOrdersLoading ? (
          <p>Loading your order history...</p>
        ) : !session ? (
          <p>Sign in to load your open and historical orders on this market.</p>
        ) : myOrders.length === 0 ? (
          <p>No orders placed on this market yet.</p>
        ) : (
          <div className="entity-list orders-list">
            {myOrders.map((order) => (
              <article className="entity-card order-card" key={order.id}>
                <div className="entity-card-header">
                  <strong>{formatOrderLabel(order.side, order.outcome_label)}</strong>
                  <span className="pill">{order.status}</span>
                </div>
                <dl className="kv-list compact">
                  <div>
                    <dt>Price</dt>
                    <dd>{formatPrice(order.price)}</dd>
                  </div>
                  <div>
                    <dt>Quantity</dt>
                    <dd>{formatNumber(order.quantity)}</dd>
                  </div>
                  <div>
                    <dt>Remaining</dt>
                    <dd>{formatNumber(order.remaining_quantity)}</dd>
                  </div>
                  <div>
                    <dt>Ticket ID</dt>
                    <dd>{order.client_order_id || "web"}</dd>
                  </div>
                  <div>
                    <dt>Collateral</dt>
                    <dd>{order.max_total_cost ? formatNumber(order.max_total_cost) : "N/A"}</dd>
                  </div>
                </dl>
                {["open", "partially_filled", "pending_acceptance"].includes(order.status) ? (
                  <div className="button-row">
                    <button
                      className="button-secondary"
                      disabled={isSubmitting}
                      type="button"
                      onClick={() =>
                        void runAction(
                          "Cancelling order...",
                          async () => {
                            const accessToken = await getAccessToken();
                            const cancelledOrder = await beyulApiFetch<MarketOrder>(
                              `/api/v1/markets/${slug}/orders/${order.id}`,
                              {
                                method: "DELETE",
                                accessToken
                              }
                            );
                            await refreshShellAndOrders();
                            return cancelledOrder;
                          },
                          {
                            successMessage: "Order cancelled."
                          }
                        )
                      }
                    >
                      Cancel order
                    </button>
                  </div>
                ) : null}
              </article>
            ))}
          </div>
        )}
      </section>
      </div>

      <AuthFeedback errorMessage={errorMessage} statusMessage={statusMessage} />
      </div>

      <aside className="market-detail-sidebar">
      <section className="auth-section market-ticket-section">

        {/* ── Buy / Sell toggle ── */}
        <div className="simple-ticket-tabs">
          <button
            className={side === "buy" ? "is-active buy" : "buy"}
            type="button"
            onClick={() => setSide("buy")}
          >Buy</button>
          <button
            className={side === "sell" ? "is-active sell" : "sell"}
            type="button"
            onClick={() => setSide("sell")}
          >Sell</button>
        </div>

        {/* ── Outcome selector ── */}
        <div className="market-outcome-strip">
          {(shell?.quotes ?? []).map((quote) => {
            const isActive = quote.outcome_id === (selectedQuote?.outcome_id ?? shell?.quotes[0]?.outcome_id);
            const p = side === "buy"
              ? (getOutcomeMicroStats(quote, shell?.order_books.find(b => b.outcome_id === quote.outcome_id) ?? null).best_ask ?? quote.last_price)
              : (getOutcomeMicroStats(quote, shell?.order_books.find(b => b.outcome_id === quote.outcome_id) ?? null).best_bid ?? quote.last_price);
            const pct = p ? Math.round(Number(p) * 100) : null;
            return (
              <button
                key={quote.outcome_id}
                className={`outcome-btn ${isActive ? "is-active" : ""}`}
                type="button"
                onClick={() => setSelectedOutcomeId(quote.outcome_id)}
              >
                <span className="outcome-btn-label">{quote.outcome_label}</span>
                <span className="outcome-btn-price">{pct !== null ? `${pct}¢` : "—"}</span>
              </button>
            );
          })}
        </div>

        {!session ? (
          <div className="simple-ticket-unauth">
            <p>Sign in to trade on this market.</p>
            <a className="button-primary simple-ticket-cta" href="/auth/sign-in">Sign in to trade</a>
          </div>
        ) : !canPlaceOrders ? (
          <div className="simple-ticket-unauth">
            <p>Orders are disabled while the market is <strong>{shell?.market.status}</strong>.</p>
          </div>
        ) : (
          <>
            <div className="ticket-order-mode">
              <span className="ticket-order-mode-label">Order type</span>
              <div className="ticket-order-mode-controls">
                <button
                  type="button"
                  className={`ticket-order-mode-pill ${orderEntryMode === "market" ? "is-active" : ""}`}
                  onClick={() => setOrderEntryMode("market")}
                >
                  Market
                </button>
                <button
                  type="button"
                  className={`ticket-order-mode-pill ${orderEntryMode === "limit" ? "is-active" : ""}`}
                  onClick={() => setOrderEntryMode("limit")}
                >
                  Limit
                </button>
              </div>
            </div>

            {orderEntryMode === "market" ? (
              <>
                <div className="field">
                  <label htmlFor="simple-amount">Amount</label>
                  <div className="amount-input-wrap">
                    <span>$</span>
                    <input
                      id="simple-amount"
                      inputMode="decimal"
                      placeholder="25"
                      value={amount}
                      onChange={(e) => setAmount(e.target.value)}
                    />
                  </div>
                </div>
                <div className="simple-ticket-preview">
                  <div>
                    <span>Shares you get</span>
                    <strong>{autoShares > 0 ? autoShares.toFixed(2) : "—"}</strong>
                  </div>
                  <div>
                    <span>Price per share</span>
                    <strong>{autoPrice ? `${Math.round(Number(autoPrice) * 100)}¢` : "—"}</strong>
                  </div>
                  <div>
                    <span>Payout if {selectedOutcomeLabel}</span>
                    <strong>{autoPayout > 0 ? `$${autoPayout.toFixed(2)}` : "—"}</strong>
                  </div>
                </div>
                {!hasLiquidity ? (
                  <p className="field-hint">
                    No liquidity for market execution right now.
                    {" "}
                    <button type="button" className="inline-link-button" onClick={() => setOrderEntryMode("limit")}>
                      Switch to limit order
                    </button>
                    .
                  </p>
                ) : null}
                <button
                  className="button-primary simple-ticket-cta"
                  type="button"
                  disabled={isSubmitting || !selectedQuote || !hasLiquidity || autoShares < 0.01}
                  onClick={() => {
                    if (!session || !selectedQuote) return;
                    void runAction(
                      `${side === "buy" ? "Buying" : "Selling"} ${selectedOutcomeLabel}...`,
                      async () => {
                        try {
                          setOrderErrorHint("");
                          const accessToken = await getAccessToken();
                          const payload: MarketOrderCreateInput = {
                            outcome_id: selectedQuote.outcome_id,
                            side,
                            order_type: "limit",
                            quantity: autoShares.toFixed(4),
                            price: autoPrice
                          };
                          const createdOrder = await beyulApiFetch<MarketOrder>(`/api/v1/markets/${slug}/orders`, {
                            method: "POST",
                            accessToken,
                            json: payload
                          });
                          await refreshShellAndOrders();
                          return createdOrder;
                        } catch (error) {
                          const message = error instanceof Error ? error.message : "Order submission failed.";
                          setOrderErrorHint(getOrderConflictHint(message, shell?.market.status));
                          throw error;
                        }
                      },
                      {
                        successMessage: (order) =>
                          `${order.side === "buy" ? "Bought" : "Sold"} ${order.quantity} ${order.outcome_label} at ${formatPrice(order.price)}.`
                      }
                    );
                  }}
                >
                  {side === "buy" ? `Buy ${selectedOutcomeLabel}` : `Sell ${selectedOutcomeLabel}`}
                  {autoPrice ? ` · ${Math.round(Number(autoPrice) * 100)}¢` : ""}
                </button>
              </>
            ) : (
              <form
                className="auth-form"
                onSubmit={(event) => {
                  event.preventDefault();
                  if (!session || !selectedQuote) return;
                  void runAction(
                    `Submitting ${side} limit order for ${selectedOutcomeLabel}...`,
                    async () => {
                      try {
                        setOrderErrorHint("");
                        const accessToken = await getAccessToken();
                        const payload: MarketOrderCreateInput = {
                          outcome_id: selectedQuote.outcome_id,
                          side,
                          order_type: "limit",
                          quantity,
                          price
                        };
                        const createdOrder = await beyulApiFetch<MarketOrder>(`/api/v1/markets/${slug}/orders`, {
                          method: "POST",
                          accessToken,
                          json: payload
                        });
                        await refreshShellAndOrders();
                        return createdOrder;
                      } catch (error) {
                        const message = error instanceof Error ? error.message : "Order submission failed.";
                        setOrderErrorHint(getOrderConflictHint(message, shell?.market.status));
                        throw error;
                      }
                    },
                    {
                      successMessage: (order) =>
                        `Order accepted: ${order.side.toUpperCase()} ${order.quantity} ${order.outcome_label} at ${formatPrice(order.price)}.`
                    }
                  );
                }}
              >
                <div className="ticket-grid">
                  <div className="field">
                    <label htmlFor="adv-outcome">Outcome</label>
                    <select
                      className="select-field"
                      id="adv-outcome"
                      value={selectedOutcomeId}
                      onChange={(event) => setSelectedOutcomeId(event.target.value)}
                    >
                      {(shell?.quotes ?? []).map((quote) => (
                        <option key={quote.outcome_id} value={quote.outcome_id}>
                          {quote.outcome_label}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="field">
                    <label htmlFor="adv-side">Side</label>
                    <select
                      className="select-field"
                      id="adv-side"
                      value={side}
                      onChange={(event) => setSide(event.target.value as "buy" | "sell")}
                    >
                      <option value="buy">Buy</option>
                      <option value="sell">Sell</option>
                    </select>
                  </div>
                  <div className="field">
                    <label htmlFor="adv-quantity">Quantity (shares)</label>
                    <input
                      id="adv-quantity"
                      inputMode="decimal"
                      placeholder="25"
                      value={quantity}
                      onChange={(event) => setQuantity(event.target.value)}
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="adv-price">Limit price</label>
                    <input
                      id="adv-price"
                      inputMode="decimal"
                      placeholder="0.55"
                      value={price}
                      onChange={(event) => setPrice(event.target.value)}
                    />
                  </div>
                </div>
                <div className="execution-preview-bar" aria-label="Execution preview">
                  <div className="execution-preview-fill" style={{ width: `${immediateFillPercent}%` }} />
                </div>
                <p className="ticket-explainer">
                  {immediateFillPercent > 0
                    ? `${Math.round(immediateFillPercent)}% would fill immediately.`
                    : "This order rests on the book at this price."}
                </p>
                <div className="button-row">
                  <button
                    className="button-primary"
                    disabled={isSubmitting || !session || !selectedQuote || !canPlaceOrders}
                    type="submit"
                  >
                    Place limit order
                  </button>
                </div>
              </form>
            )}
            {orderErrorHint ? <p className="field-hint">{orderErrorHint}</p> : null}
          </>
        )}
      </section>

      {shell ? (
        <AdvancedOrderForm
          marketSlug={slug}
          outcomeId={selectedQuote?.outcome_id || shell.quotes[0]?.outcome_id || ""}
          outcomeName={selectedQuote?.outcome_label || shell.quotes[0]?.outcome_label || ""}
          currentPrice={selectedQuote?.last_price ? Number(selectedQuote.last_price) : undefined}
        />
      ) : null}

      <section className="auth-section market-exposure-section">
        <h2>Your position</h2>
        {!session ? (
          <p>Sign in to see your balance and positions.</p>
        ) : marketBalances.length === 0 && marketPositions.length === 0 ? (
          <p>No funded balance or open position on this market yet.</p>
        ) : (
          <>
            {marketBalances.length > 0 ? (
              <div className="entity-list">
                {marketBalances.map((balance) => (
                  <article className="entity-card exposure-card" key={balance.account_code}>
                    <div className="entity-card-header">
                      <strong>{balance.asset_code}</strong>
                      <span className="pill">{balance.rail_mode}</span>
                    </div>
                    <dl className="kv-list compact">
                      <div>
                        <dt>Available</dt>
                        <dd>{formatNumber(balance.available_balance)}</dd>
                      </div>
                      <div>
                        <dt>Reserved</dt>
                        <dd>{formatNumber(balance.reserved_balance)}</dd>
                      </div>
                    </dl>
                  </article>
                ))}
              </div>
            ) : null}
            {marketPositions.length > 0 ? (
              <div className="entity-list">
                {marketPositions.map((position) => (
                  <article className="entity-card exposure-card" key={`${position.market_id}-${position.outcome_id}`}>
                    <div className="entity-card-header">
                      <strong>{formatExposureLabel(position.quantity, position.outcome_label)}</strong>
                      <span className="pill">{position.market_status}</span>
                    </div>
                    <dl className="kv-list compact">
                      <div>
                        <dt>Quantity</dt>
                        <dd>{formatNumber(position.quantity)}</dd>
                      </div>
                      <div>
                        <dt>Avg entry</dt>
                        <dd>{position.average_entry_price ? formatPrice(position.average_entry_price) : "N/A"}</dd>
                      </div>
                      <div>
                        <dt>Realized PnL</dt>
                        <dd>{formatNumber(position.realized_pnl)}</dd>
                      </div>
                      <div>
                        <dt>Unrealized PnL</dt>
                        <dd>{formatNumber(position.unrealized_pnl)}</dd>
                      </div>
                    </dl>
                  </article>
                ))}
              </div>
            ) : null}
          </>
        )}
      </section>

      <section className="auth-section market-contract-section">
        <h2>Contract details</h2>
        {shell ? (
          <dl className="kv-list compact">
            <div>
              <dt>Contract type</dt>
              <dd>{shell.market.reference_context?.contract_type || "Binary market"}</dd>
            </div>
            <div>
              <dt>Category</dt>
              <dd>{shell.market.reference_context?.subcategory || shell.market.reference_context?.category || "General"}</dd>
            </div>
            <div>
              <dt>Market opened</dt>
              <dd>{formatMarketTime(shell.market.created_at)}</dd>
            </div>
            <div>
              <dt>Trading closes</dt>
              <dd>
                {shell.market.timing.trading_closes_at ? formatMarketTime(shell.market.timing.trading_closes_at) : "Not scheduled"}
              </dd>
            </div>
            <div>
              <dt>Countdown</dt>
              <dd>{closeCountdown}</dd>
            </div>
            <div>
              <dt>Resolution mode</dt>
              <dd>{shell.market.resolution_mode}</dd>
            </div>
            <div>
              <dt>Source</dt>
              <dd>
                {shell.market.settlement_reference_url ? (
                  <a href={shell.market.settlement_reference_url} rel="noreferrer" target="_blank">
                    {contractSourceDisplay}
                  </a>
                ) : (
                  contractSourceDisplay
                )}
              </dd>
            </div>
            <div>
              <dt>Oracle</dt>
              <dd>{shell.market.settlement_source?.name || "Configured source"}</dd>
            </div>
            <div>
              <dt>Reference source</dt>
              <dd>{contractSourceDisplay}</dd>
            </div>
            <div>
              <dt>Reference label</dt>
              <dd>{shell.market.reference_context?.reference_label || "Not set"}</dd>
            </div>
            <div>
              <dt>Reference asset</dt>
              <dd>{shell.market.reference_context?.reference_asset || "Not set"}</dd>
            </div>
            <div>
              <dt>Reference timestamp</dt>
              <dd>
                {shell.market.reference_context?.reference_timestamp
                  ? formatMarketTime(shell.market.reference_context.reference_timestamp)
                  : "Not set"}
              </dd>
            </div>
            <div>
              <dt>Access</dt>
              <dd>{shell.market.market_access_mode}</dd>
            </div>
            <div>
              <dt>Min participants</dt>
              <dd>{shell.market.min_participants}</dd>
            </div>
            <div>
              <dt>Min seed</dt>
              <dd>{formatNumber(shell.market.min_seed_amount)}</dd>
            </div>
            <div>
              <dt>Min liquidity</dt>
              <dd>{shell.market.min_liquidity_amount ? formatNumber(shell.market.min_liquidity_amount) : "0"}</dd>
            </div>
            <div>
              <dt>Platform fee</dt>
              <dd>{shell.market.platform_fee_bps ?? 0} bps ({((shell.market.platform_fee_bps ?? 0) / 100).toFixed(1)}%)</dd>
            </div>
            <div>
              <dt>Creator fee</dt>
              <dd>{shell.market.creator_fee_bps ?? 0} bps ({((shell.market.creator_fee_bps ?? 0) / 100).toFixed(1)}%)</dd>
            </div>
            <div>
              <dt>Creator rewards</dt>
              <dd>
                <a href="/creators" className="market-creator-reward-link">View tier schedule →</a>
              </dd>
            </div>
          </dl>
        ) : (
          <p>Load the market to inspect contract details.</p>
        )}
      </section>

      <section className="auth-section market-holders-section">
        <h2>Top holders</h2>
        {isHoldersLoading && !holders ? (
          <p>Loading holder leaderboard...</p>
        ) : !holders ? (
          <p>Holder leaderboard is unavailable right now.</p>
        ) : (
          <div className="holders-group-grid">
            {holders.groups.map((group) => (
              <article className="entity-card holder-group-card" key={group.outcome_id}>
                <div className="entity-card-header">
                  <strong>{group.outcome_label} holders</strong>
                  <span className="pill">{group.holders.length}</span>
                </div>
                {group.holders.length === 0 ? (
                  <p>No holders yet.</p>
                ) : (
                  <div className="trade-tape holder-table">
                    <div className="trade-tape-head holder-table-head">
                      <span>Trader</span>
                      <span>Shares</span>
                      <span>Avg</span>
                    </div>
                    {group.holders.map((holder) => (
                      <article className="trade-tape-row holder-table-row" key={`${group.outcome_id}-${holder.profile_id}`}>
                        <strong>{holder.username || holder.display_name}</strong>
                        <span>{formatNumber(holder.quantity)}</span>
                        <span>{holder.average_entry_price ? formatPrice(holder.average_entry_price) : "N/A"}</span>
                      </article>
                    ))}
                  </div>
                )}
              </article>
            ))}
          </div>
        )}
      </section>

      <section className="auth-section market-settlement-section">
        <h2>Settlement</h2>
        {!session ? (
          <p>Sign in to request oracle settlement once the market is ready for resolution.</p>
        ) : shell?.market.status === "awaiting_resolution" ? (
          <p>
            Oracle settlement has been requested. This market now waits for a neutral oracle callback to finalize the
            winning outcome.
          </p>
        ) : shell?.market.status === "settled" ? (
          <p>This market is already settled.</p>
        ) : (
          <form
            className="auth-form"
            onSubmit={(event) => {
              event.preventDefault();
              void runAction(
                "Requesting oracle settlement...",
                async () => {
                  const accessToken = await getAccessToken();
                  const resolution = await beyulApiFetch<MarketResolution>(`/api/v1/markets/${slug}/settlement-requests`, {
                    method: "POST",
                    accessToken,
                    json: settlementRequestForm
                  });
                  await refreshShellAndOrders();
                  return resolution;
                },
                {
                  successMessage: "Oracle settlement requested. The market is now awaiting neutral finalization."
                }
              );
            }}
          >
            <div className="field">
              <label htmlFor="settle-source">Source reference URL</label>
              <input
                id="settle-source"
                value={settlementRequestForm.source_reference_url || ""}
                onChange={(event) =>
                  setSettlementRequestForm((current) => ({ ...current, source_reference_url: event.target.value }))
                }
              />
            </div>
            <div className="field">
              <label htmlFor="settle-notes">Request notes</label>
              <textarea
                id="settle-notes"
                rows={3}
                value={settlementRequestForm.notes || ""}
                onChange={(event) => setSettlementRequestForm((current) => ({ ...current, notes: event.target.value }))}
              />
            </div>
            <p>This requests oracle resolution. No admin or trader can pick the winner directly from this screen.</p>
            <div className="button-row">
              <button className="button-primary" disabled={isSubmitting || !canRequestSettlement} type="submit">
                Request oracle settlement
              </button>
            </div>
          </form>
        )}
        {showDevOracleHarness ? (
          <div className="market-dev-oracle-stack">
            <article className="entity-card market-dev-oracle-card">
              <div className="entity-card-header">
                <strong>Dev oracle controls</strong>
                <span className="pill">development only</span>
              </div>
              <p>
                These controls proxy through the Next server and verify admin identity before calling the secret-backed
                oracle review and finalization routes.
              </p>
              <div className="button-row">
                <button
                  className="button-secondary"
                  disabled={isSubmitting || !resolutionState?.current_resolution_id}
                  type="button"
                  onClick={() =>
                    void runAction(
                      "Reconciling onchain oracle status...",
                      async () => {
                        const nextResolutionState = await postDevOracleAction<MarketResolutionState>(
                          `/api/dev/oracle/markets/${slug}/reconcile`,
                          {}
                        );
                        await refreshShellAndOrders();
                        return nextResolutionState;
                      },
                      {
                        successMessage: "Oracle resolution state reconciled from the current onchain transaction status."
                      }
                    )
                  }
                >
                  Reconcile oracle status
                </button>
              </div>
            </article>
            <div className="market-dev-oracle-grid">
              <article className="entity-card market-dev-oracle-card">
                <div className="entity-card-header">
                  <strong>Review disputes</strong>
                  <span className="pill">{reviewableDisputes.length}</span>
                </div>
                {reviewableDisputes.length === 0 ? (
                  <p>No open disputes are waiting for oracle review.</p>
                ) : (
                  <div className="entity-list">
                    {reviewableDisputes.map((dispute) => {
                      const reviewDraft = disputeReviewDrafts[dispute.id] ?? buildDefaultDisputeReviewDraft();
                      return (
                        <article className="entity-card" key={`review-${dispute.id}`}>
                          <div className="entity-card-header">
                            <strong>{dispute.title}</strong>
                            <span className="pill">{dispute.status}</span>
                          </div>
                          <form
                            className="auth-form compact-form"
                            onSubmit={(event) => {
                              event.preventDefault();
                              void runAction(
                        "Reviewing dispute through dev oracle controls...",
                        async () => {
                                  const reviewedDispute = await postDevOracleAction<MarketDispute>(
                                    `/api/dev/oracle/markets/${slug}/disputes/${dispute.id}/review`,
                                    reviewDraft
                                  );
                                  await refreshShellAndOrders();
                                  return reviewedDispute;
                                },
                                {
                                  successMessage: `Dispute moved to ${reviewDraft.status}.`
                                }
                              );
                            }}
                          >
                            <div className="field">
                              <label htmlFor={`dev-review-status-${dispute.id}`}>Review status</label>
                              <select
                                id={`dev-review-status-${dispute.id}`}
                                value={reviewDraft.status}
                                onChange={(event) =>
                                  setDisputeReviewDrafts((current) => ({
                                    ...current,
                                    [dispute.id]: {
                                      status: event.target.value as MarketDisputeReviewInput["status"],
                                      review_notes: current[dispute.id]?.review_notes ?? ""
                                    }
                                  }))
                                }
                              >
                                <option value="under_review">Under review</option>
                                <option value="dismissed">Dismissed</option>
                                <option value="upheld">Upheld</option>
                                <option value="withdrawn">Withdrawn</option>
                              </select>
                            </div>
                            <div className="field">
                              <label htmlFor={`dev-review-notes-${dispute.id}`}>Review notes</label>
                              <textarea
                                id={`dev-review-notes-${dispute.id}`}
                                rows={3}
                                placeholder="Explain the oracle review decision."
                                value={reviewDraft.review_notes ?? ""}
                                onChange={(event) =>
                                  setDisputeReviewDrafts((current) => ({
                                    ...current,
                                    [dispute.id]: {
                                      status: current[dispute.id]?.status ?? "dismissed",
                                      review_notes: event.target.value
                                    }
                                  }))
                                }
                              />
                            </div>
                            <div className="button-row">
                              <button className="button-secondary" disabled={isSubmitting} type="submit">
                                Submit review
                              </button>
                            </div>
                          </form>
                        </article>
                      );
                    })}
                  </div>
                )}
              </article>
              <article className="entity-card market-dev-oracle-card">
                <div className="entity-card-header">
                  <strong>Finalize market</strong>
                  <span className="pill">{resolutionState?.current_status || "idle"}</span>
                </div>
                {!resolutionState?.current_resolution_id ? (
                  <p>Request oracle settlement first. Finalization is only available once a resolution candidate exists.</p>
                ) : (
                  <form
                    className="auth-form compact-form"
                    onSubmit={(event) => {
                      event.preventDefault();
                      void runAction(
                        "Finalizing market through dev oracle controls...",
                        async () => {
                          const finalizedPayload: MarketOracleFinalizeInput = {
                            ...finalizeDraft,
                            candidate_id: finalizeDraft.candidate_id?.trim() || undefined,
                            source_reference_url: finalizeDraft.source_reference_url?.trim() || undefined,
                            notes: finalizeDraft.notes?.trim() || undefined
                          };
                          const finalizedResolution = await postDevOracleAction<MarketResolution>(
                            `/api/dev/oracle/markets/${slug}/finalize`,
                            finalizedPayload
                          );
                          await refreshShellAndOrders();
                          return finalizedResolution;
                        },
                        {
                          successMessage: "Market finalized through the dev oracle harness."
                        }
                      );
                    }}
                  >
                    <div className="field">
                      <label htmlFor="dev-finalize-outcome">Winning outcome</label>
                      <select
                        id="dev-finalize-outcome"
                        value={finalizeDraft.winning_outcome_id}
                        onChange={(event) =>
                          setFinalizeDraft((current) => ({
                            ...current,
                            winning_outcome_id: event.target.value
                          }))
                        }
                      >
                        {(shell?.market.outcomes ?? []).map((outcome) => (
                          <option key={outcome.id} value={outcome.id}>
                            {outcome.label}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div className="field">
                      <label htmlFor="dev-finalize-candidate">Candidate ID</label>
                      <input
                        id="dev-finalize-candidate"
                        placeholder="Leave blank to finalize the latest active resolution."
                        value={finalizeDraft.candidate_id || ""}
                        onChange={(event) =>
                          setFinalizeDraft((current) => ({
                            ...current,
                            candidate_id: event.target.value
                          }))
                        }
                      />
                    </div>
                    <div className="field">
                      <label htmlFor="dev-finalize-source">Source reference URL</label>
                      <input
                        id="dev-finalize-source"
                        placeholder="https://..."
                        value={finalizeDraft.source_reference_url || ""}
                        onChange={(event) =>
                          setFinalizeDraft((current) => ({
                            ...current,
                            source_reference_url: event.target.value
                          }))
                        }
                      />
                    </div>
                    <div className="field">
                      <label htmlFor="dev-finalize-notes">Finalize notes</label>
                      <textarea
                        id="dev-finalize-notes"
                        rows={3}
                        placeholder="Explain the mock oracle finalization."
                        value={finalizeDraft.notes || ""}
                        onChange={(event) =>
                          setFinalizeDraft((current) => ({
                            ...current,
                            notes: event.target.value
                          }))
                        }
                      />
                    </div>
                    <div className="button-row">
                      <button
                        className="button-primary"
                        disabled={isSubmitting || !finalizeDraft.winning_outcome_id}
                        type="submit"
                      >
                        Finalize market
                      </button>
                    </div>
                  </form>
                )}
              </article>
            </div>
          </div>
        ) : null}
      </section>

      </aside>
    </div>
  );
};
