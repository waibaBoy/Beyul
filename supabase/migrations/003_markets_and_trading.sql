create table if not exists public.settlement_sources (
  id uuid primary key default gen_random_uuid(),
  code citext not null unique,
  name text not null,
  tier public.settlement_tier not null,
  resolution_mode public.market_resolution_mode not null,
  provider_name text not null,
  source_type text not null,
  base_url text,
  is_active boolean not null default true,
  requires_manual_review boolean not null default false,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.market_creation_requests (
  id uuid primary key default gen_random_uuid(),
  requester_id uuid not null references public.profiles (id),
  community_id uuid references public.communities (id) on delete set null,
  title text not null,
  slug citext unique,
  question text not null,
  description text,
  market_access_mode public.market_access_mode not null,
  requested_rail public.rail_type,
  settlement_source_id uuid references public.settlement_sources (id),
  settlement_reference_url text,
  resolution_mode public.market_resolution_mode not null,
  expires_at timestamptz,
  event_starts_at timestamptz,
  min_seed_amount numeric(20, 8),
  min_participants integer,
  status public.market_request_status not null default 'draft',
  submitted_at timestamptz,
  reviewed_at timestamptz,
  reviewed_by uuid references public.profiles (id),
  review_notes text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.market_creation_request_answers (
  id uuid primary key default gen_random_uuid(),
  market_request_id uuid not null references public.market_creation_requests (id) on delete cascade,
  question_key text not null,
  question_label text not null,
  answer_text text,
  answer_json jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  unique (market_request_id, question_key)
);

create table if not exists public.assets (
  id uuid primary key default gen_random_uuid(),
  code citext not null unique,
  name text not null,
  kind public.asset_kind not null,
  decimals integer not null check (decimals between 0 and 18),
  is_active boolean not null default true,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.markets (
  id uuid primary key default gen_random_uuid(),
  community_id uuid references public.communities (id) on delete set null,
  created_from_request_id uuid unique references public.market_creation_requests (id) on delete set null,
  creator_id uuid not null references public.profiles (id),
  settlement_source_id uuid not null references public.settlement_sources (id),
  slug citext not null unique,
  title text not null,
  question text not null,
  description text,
  rules_text text not null,
  market_access_mode public.market_access_mode not null,
  rail_mode public.rail_type not null,
  status public.market_status not null default 'draft',
  resolution_mode public.market_resolution_mode not null,
  settlement_reference_url text,
  settlement_reference_label text,
  trading_opens_at timestamptz,
  trading_closes_at timestamptz,
  resolution_due_at timestamptz,
  dispute_window_ends_at timestamptz,
  activated_at timestamptz,
  cancelled_at timestamptz,
  settled_at timestamptz,
  min_seed_amount numeric(20, 8) not null default 0,
  min_liquidity_amount numeric(20, 8) not null default 0,
  min_participants integer not null default 2,
  creator_fee_bps integer not null default 0 check (creator_fee_bps between 0 and 10000),
  platform_fee_bps integer not null default 100 check (platform_fee_bps between 0 and 10000),
  total_volume numeric(20, 8) not null default 0,
  total_trades_count integer not null default 0,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  check (
    trading_closes_at is null
    or trading_opens_at is null
    or trading_closes_at > trading_opens_at
  )
);

create table if not exists public.market_outcomes (
  id uuid primary key default gen_random_uuid(),
  market_id uuid not null references public.markets (id) on delete cascade,
  code text not null,
  label text not null,
  outcome_index integer not null,
  status public.outcome_status not null default 'active',
  settlement_value numeric(20, 8),
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  unique (market_id, code),
  unique (market_id, outcome_index)
);

create table if not exists public.orders (
  id uuid primary key default gen_random_uuid(),
  market_id uuid not null references public.markets (id) on delete cascade,
  outcome_id uuid not null references public.market_outcomes (id) on delete cascade,
  profile_id uuid not null references public.profiles (id),
  asset_id uuid not null references public.assets (id),
  rail_mode public.rail_type not null,
  side public.order_side not null,
  order_type public.order_type not null,
  status public.order_status not null default 'pending_acceptance',
  quantity numeric(20, 8) not null check (quantity > 0),
  price numeric(20, 8) check (price >= 0 and price <= 1),
  matched_quantity numeric(20, 8) not null default 0 check (matched_quantity >= 0),
  remaining_quantity numeric(20, 8) not null check (remaining_quantity >= 0),
  max_total_cost numeric(20, 8),
  source text not null default 'web',
  engine_order_id text,
  client_order_id text,
  expires_at timestamptz,
  accepted_at timestamptz,
  cancelled_at timestamptz,
  rejection_reason text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.trades (
  id uuid primary key default gen_random_uuid(),
  market_id uuid not null references public.markets (id) on delete cascade,
  outcome_id uuid not null references public.market_outcomes (id) on delete cascade,
  asset_id uuid not null references public.assets (id),
  rail_mode public.rail_type not null,
  maker_order_id uuid not null references public.orders (id),
  taker_order_id uuid not null references public.orders (id),
  maker_profile_id uuid not null references public.profiles (id),
  taker_profile_id uuid not null references public.profiles (id),
  quantity numeric(20, 8) not null check (quantity > 0),
  price numeric(20, 8) not null check (price >= 0 and price <= 1),
  gross_notional numeric(20, 8) not null check (gross_notional >= 0),
  platform_fee_amount numeric(20, 8) not null default 0,
  creator_fee_amount numeric(20, 8) not null default 0,
  engine_trade_id text unique,
  executed_at timestamptz not null default timezone('utc', now()),
  created_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.positions (
  id uuid primary key default gen_random_uuid(),
  market_id uuid not null references public.markets (id) on delete cascade,
  outcome_id uuid not null references public.market_outcomes (id) on delete cascade,
  profile_id uuid not null references public.profiles (id) on delete cascade,
  asset_id uuid not null references public.assets (id),
  rail_mode public.rail_type not null,
  quantity numeric(20, 8) not null default 0,
  average_entry_price numeric(20, 8),
  net_cost numeric(20, 8) not null default 0,
  realized_pnl numeric(20, 8) not null default 0,
  unrealized_pnl numeric(20, 8) not null default 0,
  last_trade_at timestamptz,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  unique (market_id, outcome_id, profile_id, asset_id, rail_mode)
);

create index if not exists idx_orders_market_status on public.orders (market_id, status, created_at desc);
create index if not exists idx_orders_profile_created_at on public.orders (profile_id, created_at desc);
create index if not exists idx_trades_market_executed_at on public.trades (market_id, executed_at desc);
create index if not exists idx_trades_maker_profile on public.trades (maker_profile_id, executed_at desc);
create index if not exists idx_trades_taker_profile on public.trades (taker_profile_id, executed_at desc);

drop trigger if exists trg_settlement_sources_updated_at on public.settlement_sources;
create trigger trg_settlement_sources_updated_at before update on public.settlement_sources for each row execute function public.set_updated_at();

drop trigger if exists trg_market_creation_requests_updated_at on public.market_creation_requests;
create trigger trg_market_creation_requests_updated_at before update on public.market_creation_requests for each row execute function public.set_updated_at();

drop trigger if exists trg_assets_updated_at on public.assets;
create trigger trg_assets_updated_at before update on public.assets for each row execute function public.set_updated_at();

drop trigger if exists trg_markets_updated_at on public.markets;
create trigger trg_markets_updated_at before update on public.markets for each row execute function public.set_updated_at();

drop trigger if exists trg_market_outcomes_updated_at on public.market_outcomes;
create trigger trg_market_outcomes_updated_at before update on public.market_outcomes for each row execute function public.set_updated_at();

drop trigger if exists trg_orders_updated_at on public.orders;
create trigger trg_orders_updated_at before update on public.orders for each row execute function public.set_updated_at();

drop trigger if exists trg_positions_updated_at on public.positions;
create trigger trg_positions_updated_at before update on public.positions for each row execute function public.set_updated_at();
