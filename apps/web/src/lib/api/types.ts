export type BackendUser = {
  id: string;
  username: string;
  display_name: string;
  is_admin: boolean;
};

export type Community = {
  id: string;
  slug: string;
  name: string;
  description: string | null;
  visibility: "public" | "private";
  require_post_approval: boolean;
  require_market_approval: boolean;
};

export type CommunityMember = {
  id: string;
  profile_id: string;
  username: string;
  display_name: string;
  role: string;
};

export type CommunityCreateInput = {
  slug: string;
  name: string;
  description?: string;
  visibility: "public" | "private";
  require_post_approval: boolean;
  require_market_approval: boolean;
};

export type MarketRequest = {
  id: string;
  requester_id: string;
  requester_username: string | null;
  requester_display_name: string;
  community_id: string | null;
  community_slug: string | null;
  community_name: string | null;
  title: string;
  slug: string | null;
  question: string;
  description: string | null;
  template_key: string | null;
  template_config: MarketTemplateConfig | null;
  market_access_mode: "public" | "private_group";
  requested_rail: "custodial" | "onchain" | null;
  resolution_mode: "oracle" | "api" | "council";
  settlement_reference_url: string | null;
  status: string;
  review_notes: string | null;
  submitted_at: string | null;
  reviewed_at: string | null;
  created_at: string;
  updated_at: string;
};

export type MarketRequestCreateInput = {
  title: string;
  slug?: string;
  question: string;
  description?: string;
  template_key?: MarketTemplateKey;
  template_config?: MarketTemplateConfig;
  market_access_mode: "public" | "private_group";
  requested_rail?: "custodial" | "onchain";
  resolution_mode: "oracle" | "api" | "council";
  community_id?: string;
  settlement_source_id?: string;
  settlement_reference_url?: string;
};

export type MarketTemplateKey = "price_above" | "price_below" | "up_down_interval" | "event_outcome";

export type MarketTemplateConfig = {
  category?: string;
  subcategory?: string;
  subject?: string;
  reference_asset?: string;
  threshold_value?: string;
  timeframe_label?: string;
  interval_label?: string;
  reference_source_label?: string;
  reference_price?: string;
  reference_timestamp?: string;
  reference_label?: string;
  contract_notes?: string;
};

export type MarketRequestAnswer = {
  question_key: string;
  question_label: string;
  answer_text: string | null;
  answer_json: Record<string, unknown> | null;
};

export type Post = {
  id: string;
  community_id: string;
  community_slug: string;
  community_name: string;
  author_id: string;
  author_username: string | null;
  author_display_name: string;
  title: string | null;
  body: string;
  status: string;
  submitted_at: string | null;
  reviewed_at: string | null;
  reviewed_by: string | null;
  review_notes: string | null;
  created_at: string;
  updated_at: string;
};

export type PostCreateInput = {
  title?: string;
  body: string;
};

export type ReviewQueue = {
  pending_posts: Post[];
  pending_market_requests: MarketRequest[];
};

export type OracleLiveReadiness = {
  provider: string;
  execution_mode: string;
  network: string | null;
  chain_id: number;
  rpc_chain_id: number | null;
  signer_address: string | null;
  oracle_contract_address: string | null;
  currency_address: string | null;
  native_balance_wei: string | null;
  token_balance_wei: string | null;
  allowance_wei: string | null;
  required_bond_wei: string;
  reward_wei: string;
  liveness_minutes: number;
  approval_required: boolean;
  ready_for_live_submission: boolean;
  issues: string[];
  tx_preview: Record<string, unknown>;
};

export type OracleApprovalInput = {
  amount_wei?: string;
};

export type OracleApproval = {
  provider: string;
  execution_mode: string;
  status: string;
  chain_id: number;
  signer_address: string | null;
  spender_address: string | null;
  currency_address: string | null;
  amount_wei: string;
  allowance_before_wei: string;
  tx_hash: string | null;
  submission_status: string;
  nonce: number | null;
  gas_limit: number | null;
  gas_price_wei: string | null;
};

export type PortfolioBalance = {
  asset_code: string;
  rail_mode: string;
  account_code: string;
  settled_balance: string;
  reserved_balance: string;
  available_balance: string;
};

export type PortfolioPosition = {
  market_id: string;
  market_slug: string;
  market_title: string;
  market_status: string;
  outcome_id: string;
  outcome_label: string;
  quantity: string;
  average_entry_price: string | null;
  net_cost: string;
  realized_pnl: string;
  unrealized_pnl: string;
  last_trade_at: string | null;
};

export type PortfolioSummary = {
  balances: PortfolioBalance[];
  positions: PortfolioPosition[];
  open_orders: MarketOrder[];
  recent_trades: MarketTrade[];
};

export type AdminFundBalanceInput = {
  profile_id: string;
  asset_code: string;
  rail_mode: string;
  amount: string;
  description?: string;
};

export type MarketSettlementRequestInput = {
  source_reference_url?: string;
  notes?: string;
};

export type MarketOracleFinalizeInput = {
  winning_outcome_id: string;
  candidate_id?: string;
  source_reference_url?: string;
  notes?: string;
};

export type MarketResolution = {
  id: string;
  market_id: string;
  winning_outcome_id: string | null;
  candidate_id: string | null;
  status: string;
  resolution_mode: string;
  settlement_source_id: string | null;
  source_reference_url: string | null;
  finalizes_at: string | null;
  resolved_at: string;
};

export type MarketResolutionCandidate = {
  id: string;
  market_id: string;
  proposed_outcome_id: string | null;
  proposed_by: string | null;
  settlement_source_id: string | null;
  status: string;
  source_reference_url: string | null;
  source_reference_text: string | null;
  payload: Record<string, unknown>;
  proposed_at: string;
  reviewed_at: string | null;
  reviewed_by: string | null;
};

export type MarketResolutionEvent = {
  id: string;
  event_type: string;
  title: string;
  status: string;
  occurred_at: string;
  actor_id: string | null;
  reference_id: string | null;
  details: Record<string, unknown>;
};

export type MarketResolutionState = {
  market_id: string;
  market_slug: string;
  current_resolution_id: string | null;
  current_status: string | null;
  current_payload: Record<string, unknown>;
  candidate_id: string | null;
  winning_outcome_id: string | null;
  source_reference_url: string | null;
  finalizes_at: string | null;
  resolved_at: string | null;
  candidates: MarketResolutionCandidate[];
  disputes: MarketDispute[];
  history: MarketResolutionEvent[];
};

export type MarketDispute = {
  id: string;
  market_id: string;
  resolution_id: string | null;
  raised_by: string;
  status: string;
  title: string;
  reason: string;
  fee_amount: string;
  opened_at: string;
  closed_at: string | null;
  reviewed_by: string | null;
  review_notes: string | null;
  created_at: string;
  updated_at: string;
  evidence: MarketDisputeEvidence[];
};

export type MarketDisputeCreateInput = {
  title: string;
  reason: string;
};

export type MarketDisputeEvidence = {
  id: string;
  dispute_id: string;
  submitted_by: string;
  evidence_type: string;
  url: string | null;
  description: string | null;
  payload: Record<string, unknown>;
  created_at: string;
};

export type MarketDisputeEvidenceCreateInput = {
  evidence_type: "source_link" | "archive_snapshot" | "screenshot" | "transaction" | "market_rule" | "commentary" | "other";
  url?: string;
  description?: string;
  payload?: Record<string, unknown>;
};

export type MarketDisputeReviewInput = {
  status: "under_review" | "upheld" | "dismissed" | "withdrawn";
  review_notes?: string;
};

export type MarketOutcome = {
  id: string;
  code: string;
  label: string;
  outcome_index: number;
  status: string;
  settlement_value: string | null;
};

export type MarketSettlementSource = {
  id: string;
  code: string;
  name: string;
  resolution_mode: string;
  base_url: string | null;
};

export type MarketContractTimes = {
  trading_opens_at: string | null;
  trading_closes_at: string | null;
  resolution_due_at: string | null;
  dispute_window_ends_at: string | null;
  activated_at: string | null;
  cancelled_at: string | null;
  settled_at: string | null;
};

export type MarketReferenceContext = {
  contract_type: string | null;
  category: string | null;
  subcategory: string | null;
  reference_label: string | null;
  reference_source_label: string | null;
  reference_asset: string | null;
  reference_symbol: string | null;
  reference_price: string | null;
  price_to_beat: string | null;
  reference_timestamp: string | null;
  notes: string | null;
};

export type MarketHolderEntry = {
  profile_id: string;
  username: string | null;
  display_name: string;
  outcome_id: string;
  outcome_label: string;
  quantity: string;
  average_entry_price: string | null;
  realized_pnl: string;
  unrealized_pnl: string;
};

export type MarketHolderGroup = {
  outcome_id: string;
  outcome_label: string;
  holders: MarketHolderEntry[];
};

export type MarketHolders = {
  market_id: string;
  market_slug: string;
  groups: MarketHolderGroup[];
  last_updated_at: string;
};

export type MarketQuote = {
  outcome_id: string;
  outcome_code: string;
  outcome_label: string;
  last_price: string | null;
  best_bid: string | null;
  best_ask: string | null;
  traded_volume: string;
  resting_bid_quantity: string;
  resting_ask_quantity: string;
};

export type MarketDepthLevel = {
  price: string;
  quantity: string;
  order_count: number;
};

export type MarketOrderBook = {
  outcome_id: string;
  outcome_label: string;
  bids: MarketDepthLevel[];
  asks: MarketDepthLevel[];
};

export type MarketTrade = {
  id: string;
  outcome_id: string;
  outcome_label: string;
  price: string;
  quantity: string;
  gross_notional: string;
  executed_at: string;
};

export type MarketOrder = {
  id: string;
  market_id: string;
  outcome_id: string;
  outcome_label: string;
  side: "buy" | "sell";
  order_type: "limit" | "market";
  status: string;
  quantity: string;
  price: string | null;
  matched_quantity: string;
  remaining_quantity: string;
  max_total_cost: string | null;
  source: string;
  client_order_id: string | null;
  rejection_reason: string | null;
  created_at: string;
  updated_at: string;
};

export type MarketTradingShell = {
  market: Market;
  quotes: MarketQuote[];
  order_books: MarketOrderBook[];
  recent_trades: MarketTrade[];
};

export type MarketHistoryRangeKey = "1M" | "5M" | "30M" | "1H" | "1D" | "1W";

export type MarketHistoryBucket = {
  bucket_start: string;
  bucket_end: string;
  open_price: string | null;
  high_price: string | null;
  low_price: string | null;
  close_price: string | null;
  volume: string;
  trade_count: number;
};

export type MarketHistory = {
  market_id: string;
  market_slug: string;
  outcome_id: string;
  outcome_label: string;
  range_key: MarketHistoryRangeKey;
  interval_seconds: number;
  window_start: string;
  window_end: string;
  buckets: MarketHistoryBucket[];
};

export type MarketOrderCreateInput = {
  outcome_id: string;
  side: "buy" | "sell";
  order_type: "limit" | "market";
  quantity: string;
  price?: string;
  client_order_id?: string;
};

export type Market = {
  id: string;
  slug: string;
  title: string;
  question: string;
  description: string | null;
  status: string;
  market_access_mode: string;
  rail_mode: string;
  resolution_mode: string;
  rules_text: string;
  community_id: string | null;
  community_slug: string | null;
  community_name: string | null;
  created_from_request_id: string | null;
  creator_id: string;
  settlement_source_id: string;
  settlement_reference_url: string | null;
  settlement_reference_label: string | null;
  settlement_source: MarketSettlementSource | null;
  timing: MarketContractTimes;
  reference_context: MarketReferenceContext | null;
  min_seed_amount: string;
  min_liquidity_amount: string | null;
  min_participants: number;
  creator_fee_bps: number | null;
  platform_fee_bps: number | null;
  traded_volume: string;
  total_volume: string;
  last_price: string | null;
  total_trades_count: number;
  created_at: string;
  updated_at: string;
  outcomes: MarketOutcome[];
};

export type MarketLiveEvent = {
  event_type: "subscribed" | "order_updated" | "trade_executed" | "book_updated";
  market_id: string;
  payload: unknown;
  published_at: string;
};

export type MarketLiveConnectionState = "idle" | "connecting" | "reconnecting" | "connected" | "disconnected";
