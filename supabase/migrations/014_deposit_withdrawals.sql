-- Deposit and withdrawal request tracking

create type public.transfer_direction as enum ('deposit', 'withdrawal');
create type public.transfer_status as enum ('pending', 'processing', 'completed', 'failed', 'cancelled');
create type public.transfer_rail as enum ('crypto', 'fiat_bank', 'fiat_card');

create table if not exists public.transfer_requests (
  id uuid primary key default gen_random_uuid(),
  profile_id uuid not null references public.profiles(id),
  direction public.transfer_direction not null,
  rail public.transfer_rail not null,
  asset_code text not null default 'USDC',
  amount numeric(20,8) not null check (amount > 0),
  fee_amount numeric(20,8) not null default 0,
  net_amount numeric(20,8) not null,
  status public.transfer_status not null default 'pending',
  external_reference text,
  wallet_address text,
  bank_reference text,
  failure_reason text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  completed_at timestamptz
);

create index if not exists idx_transfer_requests_profile on public.transfer_requests(profile_id);
create index if not exists idx_transfer_requests_status on public.transfer_requests(status);

alter table public.transfer_requests enable row level security;

create policy "select_own_transfers" on public.transfer_requests for select using (
  profile_id = auth.uid()
);

create policy "insert_own_transfers" on public.transfer_requests for insert with check (
  profile_id = auth.uid()
);
