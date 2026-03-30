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

settlement_sources = Table(
    "settlement_sources",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("code", String, nullable=False),
    Column("name", Text, nullable=False),
    Column("resolution_mode", market_resolution_mode_enum, nullable=False),
    Column("base_url", Text),
)

profiles = Table(
    "profiles",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
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

user_wallets = Table(
    "user_wallets",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
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
    Column("id", UUID(as_uuid=True), primary_key=True),
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
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("community_id", UUID(as_uuid=True), ForeignKey("public.communities.id"), nullable=False),
    Column("profile_id", UUID(as_uuid=True), ForeignKey("public.profiles.id"), nullable=False),
    Column("role", community_role_enum, nullable=False),
    Column("joined_at", DateTime(timezone=True), nullable=False),
)

posts = Table(
    "posts",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
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
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("requester_id", UUID(as_uuid=True), ForeignKey("public.profiles.id"), nullable=False),
    Column("community_id", UUID(as_uuid=True), ForeignKey("public.communities.id")),
    Column("title", Text, nullable=False),
    Column("slug", String),
    Column("question", Text, nullable=False),
    Column("description", Text),
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
    Column("id", UUID(as_uuid=True), primary_key=True),
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
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("community_id", UUID(as_uuid=True), ForeignKey("public.communities.id")),
    Column("created_from_request_id", UUID(as_uuid=True), ForeignKey("public.market_creation_requests.id")),
    Column("creator_id", UUID(as_uuid=True), ForeignKey("public.profiles.id"), nullable=False),
    Column("settlement_source_id", UUID(as_uuid=True), ForeignKey("public.settlement_sources.id"), nullable=False),
    Column("slug", String, nullable=False),
    Column("title", Text, nullable=False),
    Column("question", Text, nullable=False),
    Column("description", Text),
    Column("rules_text", Text, nullable=False),
    Column("market_access_mode", market_access_mode_enum, nullable=False),
    Column("rail_mode", rail_type_enum, nullable=False),
    Column("status", market_status_enum, nullable=False),
    Column("resolution_mode", market_resolution_mode_enum, nullable=False),
    Column("settlement_reference_url", Text),
    Column("min_seed_amount", Numeric(20, 8), nullable=False),
    Column("min_participants", Integer, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)

market_outcomes = Table(
    "market_outcomes",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("market_id", UUID(as_uuid=True), ForeignKey("public.markets.id"), nullable=False),
    Column("code", Text, nullable=False),
    Column("label", Text, nullable=False),
    Column("outcome_index", Integer, nullable=False),
    Column("status", outcome_status_enum, nullable=False),
    Column("settlement_value", Numeric(20, 8)),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)
