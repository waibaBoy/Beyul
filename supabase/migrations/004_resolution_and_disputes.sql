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

create index if not exists idx_resolution_candidates_market on public.market_resolution_candidates (market_id, proposed_at desc);

drop trigger if exists trg_disputes_updated_at on public.disputes;
create trigger trg_disputes_updated_at before update on public.disputes for each row execute function public.set_updated_at();
