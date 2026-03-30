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

create index if not exists idx_ledger_entries_transaction on public.ledger_entries (transaction_id);
create index if not exists idx_ledger_entries_account on public.ledger_entries (ledger_account_id, created_at desc);
create index if not exists idx_payment_intents_profile on public.payment_intents (profile_id, created_at desc);

drop trigger if exists trg_ledger_accounts_updated_at on public.ledger_accounts;
create trigger trg_ledger_accounts_updated_at before update on public.ledger_accounts for each row execute function public.set_updated_at();

drop trigger if exists trg_payment_intents_updated_at on public.payment_intents;
create trigger trg_payment_intents_updated_at before update on public.payment_intents for each row execute function public.set_updated_at();
