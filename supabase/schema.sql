create extension if not exists pgcrypto;
create extension if not exists citext;

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = timezone('utc', now());
  return new;
end;
$$;

do $$
begin
  if not exists (select 1 from pg_type where typname = 'community_visibility') then
    create type public.community_visibility as enum ('public', 'private');
  end if;
  if not exists (select 1 from pg_type where typname = 'community_role') then
    create type public.community_role as enum ('member', 'moderator', 'admin', 'owner');
  end if;
  if not exists (select 1 from pg_type where typname = 'post_status') then
    create type public.post_status as enum ('draft', 'pending_review', 'approved', 'rejected', 'archived');
  end if;
  if not exists (select 1 from pg_type where typname = 'settlement_tier') then
    create type public.settlement_tier as enum ('automatic', 'semi_automatic', 'community_verified');
  end if;
  if not exists (select 1 from pg_type where typname = 'market_access_mode') then
    create type public.market_access_mode as enum ('public', 'private_group');
  end if;
  if not exists (select 1 from pg_type where typname = 'market_status') then
    create type public.market_status as enum (
      'draft',
      'pending_review',
      'pending_liquidity',
      'open',
      'trading_paused',
      'awaiting_resolution',
      'disputed',
      'settled',
      'cancelled'
    );
  end if;
  if not exists (select 1 from pg_type where typname = 'market_resolution_mode') then
    create type public.market_resolution_mode as enum ('oracle', 'api', 'council');
  end if;
  if not exists (select 1 from pg_type where typname = 'market_request_status') then
    create type public.market_request_status as enum ('draft', 'submitted', 'approved', 'rejected', 'converted');
  end if;
  if not exists (select 1 from pg_type where typname = 'outcome_status') then
    create type public.outcome_status as enum ('active', 'winning', 'losing', 'voided');
  end if;
  if not exists (select 1 from pg_type where typname = 'order_side') then
    create type public.order_side as enum ('buy', 'sell');
  end if;
  if not exists (select 1 from pg_type where typname = 'order_type') then
    create type public.order_type as enum ('market', 'limit');
  end if;
  if not exists (select 1 from pg_type where typname = 'order_status') then
    create type public.order_status as enum (
      'pending_acceptance',
      'open',
      'partially_filled',
      'filled',
      'cancelled',
      'rejected',
      'expired'
    );
  end if;
  if not exists (select 1 from pg_type where typname = 'asset_kind') then
    create type public.asset_kind as enum ('fiat', 'stablecoin', 'crypto');
  end if;
  if not exists (select 1 from pg_type where typname = 'rail_type') then
    create type public.rail_type as enum ('custodial', 'onchain');
  end if;
  if not exists (select 1 from pg_type where typname = 'ledger_owner_type') then
    create type public.ledger_owner_type as enum ('platform', 'user', 'market', 'fee_pool', 'treasury');
  end if;
  if not exists (select 1 from pg_type where typname = 'ledger_transaction_type') then
    create type public.ledger_transaction_type as enum (
      'deposit',
      'withdrawal',
      'bet_lock',
      'trade_settlement',
      'refund',
      'payout',
      'platform_fee',
      'dispute_fee',
      'adjustment'
    );
  end if;
  if not exists (select 1 from pg_type where typname = 'ledger_entry_direction') then
    create type public.ledger_entry_direction as enum ('debit', 'credit');
  end if;
  if not exists (select 1 from pg_type where typname = 'payment_intent_type') then
    create type public.payment_intent_type as enum ('deposit', 'withdrawal', 'payout', 'onchain_fund', 'onchain_claim');
  end if;
  if not exists (select 1 from pg_type where typname = 'payment_intent_status') then
    create type public.payment_intent_status as enum ('created', 'processing', 'succeeded', 'failed', 'cancelled');
  end if;
  if not exists (select 1 from pg_type where typname = 'resolution_candidate_status') then
    create type public.resolution_candidate_status as enum ('proposed', 'confirmed', 'rejected', 'superseded');
  end if;
  if not exists (select 1 from pg_type where typname = 'vote_decision') then
    create type public.vote_decision as enum ('approve', 'reject');
  end if;
  if not exists (select 1 from pg_type where typname = 'dispute_status') then
    create type public.dispute_status as enum ('open', 'under_review', 'upheld', 'dismissed', 'withdrawn');
  end if;
end
$$;

create table if not exists public.profiles (
  id uuid primary key references auth.users (id) on delete cascade,
  username citext unique,
  display_name text not null,
  bio text,
  avatar_url text,
  phone_e164 text,
  country_code text,
  is_admin boolean not null default false,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.user_wallets (
  id uuid primary key default gen_random_uuid(),
  profile_id uuid not null references public.profiles (id) on delete cascade,
  chain_name text not null,
  wallet_address text not null,
  is_primary boolean not null default false,
  verified_at timestamptz,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  unique (chain_name, wallet_address)
);

create table if not exists public.communities (
  id uuid primary key default gen_random_uuid(),
  slug citext not null unique,
  name text not null,
  description text,
  visibility public.community_visibility not null default 'public',
  require_post_approval boolean not null default true,
  require_market_approval boolean not null default true,
  created_by uuid not null references public.profiles (id),
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.community_members (
  id uuid primary key default gen_random_uuid(),
  community_id uuid not null references public.communities (id) on delete cascade,
  profile_id uuid not null references public.profiles (id) on delete cascade,
  role public.community_role not null default 'member',
  joined_at timestamptz not null default timezone('utc', now()),
  unique (community_id, profile_id)
);

create table if not exists public.posts (
  id uuid primary key default gen_random_uuid(),
  community_id uuid not null references public.communities (id) on delete cascade,
  author_id uuid not null references public.profiles (id),
  title text,
  body text not null,
  status public.post_status not null default 'pending_review',
  submitted_at timestamptz,
  reviewed_at timestamptz,
  reviewed_by uuid references public.profiles (id),
  review_notes text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

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

create table if not exists public.market_resolution_candidates (
  id uuid primary key default gen_random_uuid(),
  market_id uuid not null references public.markets (id) on delete cascade,
  proposed_outcome_id uuid references public.market_outcomes (id) on delete set null,
  proposed_by uuid references public.profiles (id),
  settlement_source_id uuid references public.settlement_sources (id),
  status public.resolution_candidate_status not null default 'proposed',
  source_reference_url text,
  source_reference_text text,
  payload jsonb not null default '{}'::jsonb,
  proposed_at timestamptz not null default timezone('utc', now()),
  reviewed_at timestamptz,
  reviewed_by uuid references public.profiles (id)
);

create table if not exists public.market_resolution_votes (
  id uuid primary key default gen_random_uuid(),
  candidate_id uuid not null references public.market_resolution_candidates (id) on delete cascade,
  voter_id uuid not null references public.profiles (id) on delete cascade,
  decision public.vote_decision not null,
  notes text,
  voted_at timestamptz not null default timezone('utc', now()),
  unique (candidate_id, voter_id)
);

create table if not exists public.market_resolutions (
  id uuid primary key default gen_random_uuid(),
  market_id uuid not null unique references public.markets (id) on delete cascade,
  winning_outcome_id uuid references public.market_outcomes (id) on delete set null,
  candidate_id uuid references public.market_resolution_candidates (id) on delete set null,
  resolved_by uuid references public.profiles (id),
  resolution_mode public.market_resolution_mode not null,
  settlement_source_id uuid references public.settlement_sources (id),
  source_reference_url text,
  final_payload jsonb not null default '{}'::jsonb,
  dispute_window_hours integer not null default 24 check (dispute_window_hours between 0 and 168),
  finalizes_at timestamptz,
  resolved_at timestamptz not null default timezone('utc', now()),
  created_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.disputes (
  id uuid primary key default gen_random_uuid(),
  market_id uuid not null references public.markets (id) on delete cascade,
  resolution_id uuid references public.market_resolutions (id) on delete set null,
  raised_by uuid not null references public.profiles (id),
  status public.dispute_status not null default 'open',
  title text not null,
  reason text not null,
  fee_amount numeric(20, 8) not null default 0,
  opened_at timestamptz not null default timezone('utc', now()),
  closed_at timestamptz,
  reviewed_by uuid references public.profiles (id),
  review_notes text,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.dispute_evidence (
  id uuid primary key default gen_random_uuid(),
  dispute_id uuid not null references public.disputes (id) on delete cascade,
  submitted_by uuid not null references public.profiles (id),
  evidence_type text not null,
  url text,
  description text,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.ledger_accounts (
  id uuid primary key default gen_random_uuid(),
  account_code text not null unique,
  owner_type public.ledger_owner_type not null,
  owner_profile_id uuid references public.profiles (id) on delete cascade,
  owner_market_id uuid references public.markets (id) on delete cascade,
  asset_id uuid not null references public.assets (id),
  rail_mode public.rail_type not null,
  is_system boolean not null default false,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  check (
    (owner_type = 'user' and owner_profile_id is not null)
    or (owner_type = 'market' and owner_market_id is not null)
    or (owner_type in ('platform', 'fee_pool', 'treasury'))
  )
);

create table if not exists public.ledger_transactions (
  id uuid primary key default gen_random_uuid(),
  transaction_type public.ledger_transaction_type not null,
  market_id uuid references public.markets (id) on delete set null,
  order_id uuid references public.orders (id) on delete set null,
  trade_id uuid references public.trades (id) on delete set null,
  dispute_id uuid references public.disputes (id) on delete set null,
  initiated_by uuid references public.profiles (id),
  external_reference text,
  description text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.ledger_entries (
  id uuid primary key default gen_random_uuid(),
  transaction_id uuid not null references public.ledger_transactions (id) on delete cascade,
  ledger_account_id uuid not null references public.ledger_accounts (id) on delete cascade,
  direction public.ledger_entry_direction not null,
  amount numeric(20, 8) not null check (amount > 0),
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.payment_intents (
  id uuid primary key default gen_random_uuid(),
  profile_id uuid not null references public.profiles (id) on delete cascade,
  asset_id uuid not null references public.assets (id),
  rail_mode public.rail_type not null,
  intent_type public.payment_intent_type not null,
  status public.payment_intent_status not null default 'created',
  amount numeric(20, 8) not null check (amount > 0),
  provider_name text,
  provider_reference text,
  wallet_address text,
  tx_hash text,
  description text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create or replace view public.account_balances as
select
  la.id as ledger_account_id,
  la.account_code,
  la.owner_type,
  la.owner_profile_id,
  la.owner_market_id,
  a.code as asset_code,
  la.rail_mode,
  coalesce(
    sum(
      case le.direction
        when 'debit' then le.amount
        when 'credit' then -le.amount
      end
    ),
    0
  ) as balance
from public.ledger_accounts la
join public.assets a on a.id = la.asset_id
left join public.ledger_entries le on le.ledger_account_id = la.id
group by la.id, la.account_code, la.owner_type, la.owner_profile_id, la.owner_market_id, a.code, la.rail_mode;

create index if not exists idx_resolution_candidates_market on public.market_resolution_candidates (market_id, proposed_at desc);
create index if not exists idx_ledger_entries_transaction on public.ledger_entries (transaction_id);
create index if not exists idx_ledger_entries_account on public.ledger_entries (ledger_account_id, created_at desc);
create index if not exists idx_payment_intents_profile on public.payment_intents (profile_id, created_at desc);

drop trigger if exists trg_profiles_updated_at on public.profiles;
create trigger trg_profiles_updated_at before update on public.profiles for each row execute function public.set_updated_at();

drop trigger if exists trg_user_wallets_updated_at on public.user_wallets;
create trigger trg_user_wallets_updated_at before update on public.user_wallets for each row execute function public.set_updated_at();

drop trigger if exists trg_communities_updated_at on public.communities;
create trigger trg_communities_updated_at before update on public.communities for each row execute function public.set_updated_at();

drop trigger if exists trg_posts_updated_at on public.posts;
create trigger trg_posts_updated_at before update on public.posts for each row execute function public.set_updated_at();

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

drop trigger if exists trg_disputes_updated_at on public.disputes;
create trigger trg_disputes_updated_at before update on public.disputes for each row execute function public.set_updated_at();

drop trigger if exists trg_ledger_accounts_updated_at on public.ledger_accounts;
create trigger trg_ledger_accounts_updated_at before update on public.ledger_accounts for each row execute function public.set_updated_at();

drop trigger if exists trg_payment_intents_updated_at on public.payment_intents;
create trigger trg_payment_intents_updated_at before update on public.payment_intents for each row execute function public.set_updated_at();
