from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    Numeric,
    String,
    Table,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ENUM, JSONB, UUID


metadata = MetaData(schema="public")

community_visibility_enum = ENUM(
    "public",
    "private",
    name="community_visibility",
    schema="public",
    create_type=False,
)

community_role_enum = ENUM(
    "member",
    "moderator",
    "admin",
    "owner",
    name="community_role",
    schema="public",
    create_type=False,
)

market_access_mode_enum = ENUM(
    "public",
    "private_group",
    name="market_access_mode",
    schema="public",
    create_type=False,
)

rail_type_enum = ENUM(
    "custodial",
    "onchain",
    name="rail_type",
    schema="public",
    create_type=False,
)

market_resolution_mode_enum = ENUM(
    "oracle",
    "api",
    "council",
    name="market_resolution_mode",
    schema="public",
    create_type=False,
)

resolution_candidate_status_enum = ENUM(
    "proposed",
    "confirmed",
    "rejected",
    "superseded",
    name="resolution_candidate_status",
    schema="public",
    create_type=False,
)

dispute_status_enum = ENUM(
    "open",
    "under_review",
    "upheld",
    "dismissed",
    "withdrawn",
    name="dispute_status",
    schema="public",
    create_type=False,
)

market_request_status_enum = ENUM(
    "draft",
    "submitted",
    "approved",
    "rejected",
    "converted",
    name="market_request_status",
    schema="public",
    create_type=False,
)

order_side_enum = ENUM(
    "buy",
    "sell",
    name="order_side",
    schema="public",
    create_type=False,
)

order_type_enum = ENUM(
    "market",
    "limit",
    name="order_type",
    schema="public",
    create_type=False,
)

order_status_enum = ENUM(
    "pending_acceptance",
    "open",
    "partially_filled",
    "filled",
    "cancelled",
    "rejected",
    "expired",
    name="order_status",
    schema="public",
    create_type=False,
)

asset_kind_enum = ENUM(
    "fiat",
    "stablecoin",
    "crypto",
    name="asset_kind",
    schema="public",
    create_type=False,
)

market_status_enum = ENUM(
    "draft",
    "pending_review",
    "pending_liquidity",
    "open",
    "trading_paused",
    "awaiting_resolution",
    "disputed",
    "settled",
    "cancelled",
    name="market_status",
    schema="public",
    create_type=False,
)

outcome_status_enum = ENUM(
    "active",
    "winning",
    "losing",
    "voided",
    name="outcome_status",
    schema="public",
    create_type=False,
)

post_status_enum = ENUM(
    "draft",
    "pending_review",
    "approved",
    "rejected",
    name="post_status",
    schema="public",
    create_type=False,
)

ledger_owner_type_enum = ENUM(
    "platform",
    "user",
    "market",
    "fee_pool",
    "treasury",
    name="ledger_owner_type",
    schema="public",
    create_type=False,
)

ledger_transaction_type_enum = ENUM(
    "deposit",
    "withdrawal",
    "bet_lock",
    "trade_settlement",
    "refund",
    "payout",
    "platform_fee",
    "dispute_fee",
    "adjustment",
    name="ledger_transaction_type",
    schema="public",
    create_type=False,
)

ledger_entry_direction_enum = ENUM(
    "debit",
    "credit",
    name="ledger_entry_direction",
    schema="public",
    create_type=False,
)

assets = Table(
    "assets",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("code", Text, nullable=False),
    Column("name", Text, nullable=False),
    Column("kind", asset_kind_enum, nullable=False),
    Column("decimals", Integer, nullable=False),
    Column("metadata", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)

settlement_sources = Table(
    "settlement_sources",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("code", String, nullable=False),
    Column("name", Text, nullable=False),
    Column("resolution_mode", market_resolution_mode_enum, nullable=False),
    Column("base_url", Text),
)

profiles = Table(
    "profiles",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("username", String),
    Column("display_name", Text, nullable=False),
    Column("bio", Text),
    Column("avatar_url", Text),
    Column("phone_e164", Text),
    Column("country_code", Text),
    Column("is_admin", Boolean, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)

legal_acceptances = Table(
    "legal_acceptances",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("profile_id", UUID(as_uuid=True), ForeignKey("public.profiles.id", ondelete="CASCADE"), nullable=False),
    Column("acceptance_type", Text, nullable=False),
    Column("document_version", Text, nullable=False),
    Column("accepted_at", DateTime(timezone=True), nullable=False),
    Column("source", Text, nullable=False),
    Column("client_asserted_at", DateTime(timezone=True)),
    Column("created_at", DateTime(timezone=True), nullable=False),
    UniqueConstraint(
        "profile_id",
        "acceptance_type",
        "document_version",
        name="legal_acceptances_profile_type_version_key",
    ),
)

user_wallets = Table(
    "user_wallets",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("profile_id", UUID(as_uuid=True), ForeignKey("public.profiles.id"), nullable=False),
    Column("chain_name", Text, nullable=False),
    Column("wallet_address", Text, nullable=False),
    Column("is_primary", Boolean, nullable=False),
    Column("verified_at", DateTime(timezone=True)),
    Column("metadata", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    UniqueConstraint("chain_name", "wallet_address", name="user_wallets_chain_name_wallet_address_key"),
)

communities = Table(
    "communities",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("slug", String, nullable=False),
    Column("name", Text, nullable=False),
    Column("description", Text),
    Column("visibility", community_visibility_enum, nullable=False),
    Column("require_post_approval", Boolean, nullable=False),
    Column("require_market_approval", Boolean, nullable=False),
    Column("created_by", UUID(as_uuid=True), ForeignKey("public.profiles.id"), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)

community_members = Table(
    "community_members",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("community_id", UUID(as_uuid=True), ForeignKey("public.communities.id"), nullable=False),
    Column("profile_id", UUID(as_uuid=True), ForeignKey("public.profiles.id"), nullable=False),
    Column("role", community_role_enum, nullable=False),
    Column("joined_at", DateTime(timezone=True), nullable=False),
)

posts = Table(
    "posts",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("community_id", UUID(as_uuid=True), ForeignKey("public.communities.id"), nullable=False),
    Column("author_id", UUID(as_uuid=True), ForeignKey("public.profiles.id"), nullable=False),
    Column("title", Text),
    Column("body", Text, nullable=False),
    Column("status", post_status_enum, nullable=False),
    Column("submitted_at", DateTime(timezone=True)),
    Column("reviewed_at", DateTime(timezone=True)),
    Column("reviewed_by", UUID(as_uuid=True), ForeignKey("public.profiles.id")),
    Column("review_notes", Text),
    Column("metadata", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)

market_creation_requests = Table(
    "market_creation_requests",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("requester_id", UUID(as_uuid=True), ForeignKey("public.profiles.id"), nullable=False),
    Column("community_id", UUID(as_uuid=True), ForeignKey("public.communities.id")),
    Column("title", Text, nullable=False),
    Column("slug", String),
    Column("question", Text, nullable=False),
    Column("description", Text),
    Column("image_url", Text),
    Column("market_access_mode", market_access_mode_enum, nullable=False),
    Column("requested_rail", rail_type_enum),
    Column("settlement_source_id", UUID(as_uuid=True)),
    Column("settlement_reference_url", Text),
    Column("resolution_mode", market_resolution_mode_enum, nullable=False),
    Column("expires_at", DateTime(timezone=True)),
    Column("event_starts_at", DateTime(timezone=True)),
    Column("min_seed_amount", Numeric(20, 8)),
    Column("min_participants", Integer),
    Column("status", market_request_status_enum, nullable=False),
    Column("submitted_at", DateTime(timezone=True)),
    Column("reviewed_at", DateTime(timezone=True)),
    Column("reviewed_by", UUID(as_uuid=True)),
    Column("review_notes", Text),
    Column("metadata", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)

market_creation_request_answers = Table(
    "market_creation_request_answers",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column(
        "market_request_id",
        UUID(as_uuid=True),
        ForeignKey("public.market_creation_requests.id"),
        nullable=False,
    ),
    Column("question_key", Text, nullable=False),
    Column("question_label", Text, nullable=False),
    Column("answer_text", Text),
    Column("answer_json", JSONB),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

markets = Table(
    "markets",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("community_id", UUID(as_uuid=True), ForeignKey("public.communities.id")),
    Column("created_from_request_id", UUID(as_uuid=True), ForeignKey("public.market_creation_requests.id")),
    Column("creator_id", UUID(as_uuid=True), ForeignKey("public.profiles.id"), nullable=False),
    Column("settlement_source_id", UUID(as_uuid=True), ForeignKey("public.settlement_sources.id"), nullable=False),
    Column("slug", String, nullable=False),
    Column("title", Text, nullable=False),
    Column("question", Text, nullable=False),
    Column("description", Text),
    Column("image_url", Text),
    Column("rules_text", Text, nullable=False),
    Column("market_access_mode", market_access_mode_enum, nullable=False),
    Column("rail_mode", rail_type_enum, nullable=False),
    Column("status", market_status_enum, nullable=False),
    Column("resolution_mode", market_resolution_mode_enum, nullable=False),
    Column("settlement_reference_url", Text),
    Column("settlement_reference_label", Text),
    Column("trading_opens_at", DateTime(timezone=True)),
    Column("trading_closes_at", DateTime(timezone=True)),
    Column("resolution_due_at", DateTime(timezone=True)),
    Column("dispute_window_ends_at", DateTime(timezone=True)),
    Column("activated_at", DateTime(timezone=True)),
    Column("cancelled_at", DateTime(timezone=True)),
    Column("settled_at", DateTime(timezone=True)),
    Column("min_seed_amount", Numeric(20, 8), nullable=False),
    Column("min_liquidity_amount", Numeric(20, 8), nullable=False),
    Column("min_participants", Integer, nullable=False),
    Column("creator_fee_bps", Integer, nullable=False),
    Column("platform_fee_bps", Integer, nullable=False),
    Column("total_volume", Numeric(20, 8), nullable=False),
    Column("total_trades_count", Integer, nullable=False),
    Column("metadata", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)

market_outcomes = Table(
    "market_outcomes",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("market_id", UUID(as_uuid=True), ForeignKey("public.markets.id"), nullable=False),
    Column("code", Text, nullable=False),
    Column("label", Text, nullable=False),
    Column("outcome_index", Integer, nullable=False),
    Column("status", outcome_status_enum, nullable=False),
    Column("settlement_value", Numeric(20, 8)),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)

orders = Table(
    "orders",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("market_id", UUID(as_uuid=True), ForeignKey("public.markets.id"), nullable=False),
    Column("outcome_id", UUID(as_uuid=True), ForeignKey("public.market_outcomes.id"), nullable=False),
    Column("profile_id", UUID(as_uuid=True), ForeignKey("public.profiles.id"), nullable=False),
    Column("asset_id", UUID(as_uuid=True), ForeignKey("public.assets.id"), nullable=False),
    Column("rail_mode", rail_type_enum, nullable=False),
    Column("side", order_side_enum, nullable=False),
    Column("order_type", order_type_enum, nullable=False),
    Column("status", order_status_enum, nullable=False),
    Column("quantity", Numeric(20, 8), nullable=False),
    Column("price", Numeric(20, 8)),
    Column("matched_quantity", Numeric(20, 8), nullable=False),
    Column("remaining_quantity", Numeric(20, 8), nullable=False),
    Column("max_total_cost", Numeric(20, 8)),
    Column("source", Text, nullable=False),
    Column("engine_order_id", Text),
    Column("client_order_id", Text),
    Column("expires_at", DateTime(timezone=True)),
    Column("accepted_at", DateTime(timezone=True)),
    Column("cancelled_at", DateTime(timezone=True)),
    Column("rejection_reason", Text),
    Column("metadata", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)

trades = Table(
    "trades",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("market_id", UUID(as_uuid=True), ForeignKey("public.markets.id"), nullable=False),
    Column("outcome_id", UUID(as_uuid=True), ForeignKey("public.market_outcomes.id"), nullable=False),
    Column("asset_id", UUID(as_uuid=True), ForeignKey("public.assets.id"), nullable=False),
    Column("rail_mode", rail_type_enum, nullable=False),
    Column("maker_order_id", UUID(as_uuid=True), ForeignKey("public.orders.id"), nullable=False),
    Column("taker_order_id", UUID(as_uuid=True), ForeignKey("public.orders.id"), nullable=False),
    Column("maker_profile_id", UUID(as_uuid=True), ForeignKey("public.profiles.id"), nullable=False),
    Column("taker_profile_id", UUID(as_uuid=True), ForeignKey("public.profiles.id"), nullable=False),
    Column("quantity", Numeric(20, 8), nullable=False),
    Column("price", Numeric(20, 8), nullable=False),
    Column("gross_notional", Numeric(20, 8), nullable=False),
    Column("platform_fee_amount", Numeric(20, 8), nullable=False),
    Column("creator_fee_amount", Numeric(20, 8), nullable=False),
    Column("engine_trade_id", Text),
    Column("executed_at", DateTime(timezone=True), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

positions = Table(
    "positions",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("market_id", UUID(as_uuid=True), ForeignKey("public.markets.id"), nullable=False),
    Column("outcome_id", UUID(as_uuid=True), ForeignKey("public.market_outcomes.id"), nullable=False),
    Column("profile_id", UUID(as_uuid=True), ForeignKey("public.profiles.id"), nullable=False),
    Column("asset_id", UUID(as_uuid=True), ForeignKey("public.assets.id"), nullable=False),
    Column("rail_mode", rail_type_enum, nullable=False),
    Column("quantity", Numeric(20, 8), nullable=False),
    Column("average_entry_price", Numeric(20, 8)),
    Column("net_cost", Numeric(20, 8), nullable=False),
    Column("realized_pnl", Numeric(20, 8), nullable=False),
    Column("unrealized_pnl", Numeric(20, 8), nullable=False),
    Column("last_trade_at", DateTime(timezone=True)),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)

market_resolutions = Table(
    "market_resolutions",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("market_id", UUID(as_uuid=True), ForeignKey("public.markets.id"), nullable=False),
    Column("winning_outcome_id", UUID(as_uuid=True), ForeignKey("public.market_outcomes.id")),
    Column("candidate_id", UUID(as_uuid=True)),
    Column("resolved_by", UUID(as_uuid=True), ForeignKey("public.profiles.id")),
    Column("resolution_mode", market_resolution_mode_enum, nullable=False),
    Column("settlement_source_id", UUID(as_uuid=True), ForeignKey("public.settlement_sources.id")),
    Column("source_reference_url", Text),
    Column("final_payload", JSONB, nullable=False),
    Column("finalizes_at", DateTime(timezone=True)),
    Column("resolved_at", DateTime(timezone=True), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

market_resolution_candidates = Table(
    "market_resolution_candidates",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("market_id", UUID(as_uuid=True), ForeignKey("public.markets.id"), nullable=False),
    Column("proposed_outcome_id", UUID(as_uuid=True), ForeignKey("public.market_outcomes.id")),
    Column("proposed_by", UUID(as_uuid=True), ForeignKey("public.profiles.id")),
    Column("settlement_source_id", UUID(as_uuid=True), ForeignKey("public.settlement_sources.id")),
    Column("status", resolution_candidate_status_enum, nullable=False),
    Column("source_reference_url", Text),
    Column("source_reference_text", Text),
    Column("payload", JSONB, nullable=False),
    Column("proposed_at", DateTime(timezone=True), nullable=False),
    Column("reviewed_at", DateTime(timezone=True)),
    Column("reviewed_by", UUID(as_uuid=True), ForeignKey("public.profiles.id")),
)

disputes = Table(
    "disputes",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("market_id", UUID(as_uuid=True), ForeignKey("public.markets.id"), nullable=False),
    Column("resolution_id", UUID(as_uuid=True), ForeignKey("public.market_resolutions.id")),
    Column("raised_by", UUID(as_uuid=True), ForeignKey("public.profiles.id"), nullable=False),
    Column("status", dispute_status_enum, nullable=False),
    Column("title", Text, nullable=False),
    Column("reason", Text, nullable=False),
    Column("fee_amount", Numeric(20, 8), nullable=False),
    Column("opened_at", DateTime(timezone=True), nullable=False),
    Column("closed_at", DateTime(timezone=True)),
    Column("reviewed_by", UUID(as_uuid=True), ForeignKey("public.profiles.id")),
    Column("review_notes", Text),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)

dispute_evidence = Table(
    "dispute_evidence",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("dispute_id", UUID(as_uuid=True), ForeignKey("public.disputes.id"), nullable=False),
    Column("submitted_by", UUID(as_uuid=True), ForeignKey("public.profiles.id"), nullable=False),
    Column("evidence_type", Text, nullable=False),
    Column("url", Text),
    Column("description", Text),
    Column("payload", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

ledger_accounts = Table(
    "ledger_accounts",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("account_code", Text, nullable=False),
    Column("owner_type", ledger_owner_type_enum, nullable=False),
    Column("owner_profile_id", UUID(as_uuid=True), ForeignKey("public.profiles.id")),
    Column("owner_market_id", UUID(as_uuid=True), ForeignKey("public.markets.id")),
    Column("asset_id", UUID(as_uuid=True), ForeignKey("public.assets.id"), nullable=False),
    Column("rail_mode", rail_type_enum, nullable=False),
    Column("is_system", Boolean, nullable=False),
    Column("metadata", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)

ledger_transactions = Table(
    "ledger_transactions",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("transaction_type", ledger_transaction_type_enum, nullable=False),
    Column("market_id", UUID(as_uuid=True), ForeignKey("public.markets.id")),
    Column("order_id", UUID(as_uuid=True), ForeignKey("public.orders.id")),
    Column("trade_id", UUID(as_uuid=True), ForeignKey("public.trades.id")),
    Column("initiated_by", UUID(as_uuid=True), ForeignKey("public.profiles.id")),
    Column("external_reference", Text),
    Column("description", Text),
    Column("metadata", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

notifications = Table(
    "notifications",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("profile_id", UUID(as_uuid=True), ForeignKey("public.profiles.id", ondelete="CASCADE"), nullable=False),
    Column("kind", Text, nullable=False),
    Column("title", Text, nullable=False),
    Column("body", Text),
    Column("market_slug", Text),
    Column("market_id", UUID(as_uuid=True), ForeignKey("public.markets.id", ondelete="SET NULL")),
    Column("order_id", UUID(as_uuid=True), ForeignKey("public.orders.id", ondelete="SET NULL")),
    Column("payload", JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    Column("is_read", Boolean, nullable=False, server_default=text("false")),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("timezone('utc', now())")),
)

ledger_entries = Table(
    "ledger_entries",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("transaction_id", UUID(as_uuid=True), ForeignKey("public.ledger_transactions.id"), nullable=False),
    Column("ledger_account_id", UUID(as_uuid=True), ForeignKey("public.ledger_accounts.id"), nullable=False),
    Column("direction", ledger_entry_direction_enum, nullable=False),
    Column("amount", Numeric(20, 8), nullable=False),
    Column("metadata", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

follows = Table(
    "follows",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("follower_id", UUID(as_uuid=True), ForeignKey("public.profiles.id"), nullable=False),
    Column("following_id", UUID(as_uuid=True), ForeignKey("public.profiles.id"), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("timezone('utc', now())")),
)

transfer_direction_enum = ENUM(
    "deposit",
    "withdrawal",
    name="transfer_direction",
    schema="public",
    create_type=False,
)

transfer_status_enum = ENUM(
    "pending",
    "processing",
    "completed",
    "failed",
    "cancelled",
    name="transfer_status",
    schema="public",
    create_type=False,
)

transfer_rail_enum = ENUM(
    "crypto",
    "fiat_bank",
    "fiat_card",
    name="transfer_rail",
    schema="public",
    create_type=False,
)

transfer_requests = Table(
    "transfer_requests",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("profile_id", UUID(as_uuid=True), ForeignKey("public.profiles.id"), nullable=False),
    Column("direction", transfer_direction_enum, nullable=False),
    Column("rail", transfer_rail_enum, nullable=False),
    Column("asset_code", Text, nullable=False),
    Column("amount", Numeric(20, 8), nullable=False),
    Column("fee_amount", Numeric(20, 8), nullable=False),
    Column("net_amount", Numeric(20, 8), nullable=False),
    Column("status", transfer_status_enum, nullable=False),
    Column("external_reference", Text),
    Column("wallet_address", Text),
    Column("bank_reference", Text),
    Column("failure_reason", Text),
    Column("metadata", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("timezone('utc', now())")),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=text("timezone('utc', now())")),
    Column("completed_at", DateTime(timezone=True)),
)

api_keys = Table(
    "api_keys",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("profile_id", UUID(as_uuid=True), ForeignKey("public.profiles.id"), nullable=False),
    Column("label", Text, nullable=False),
    Column("key_hash", Text, nullable=False),
    Column("key_prefix", Text, nullable=False),
    Column("permissions", JSONB, nullable=False),
    Column("is_active", Boolean, nullable=False, server_default=text("true")),
    Column("last_used_at", DateTime(timezone=True)),
    Column("expires_at", DateTime(timezone=True)),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("timezone('utc', now())")),
    Column("revoked_at", DateTime(timezone=True)),
)
