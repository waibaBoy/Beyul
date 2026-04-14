-- Signup / compliance audit trail (synced from Supabase auth user_metadata on first API hit).
-- Run after 009. Apply via Supabase SQL editor or `supabase db push` / psql.

create table if not exists public.legal_acceptances (
  id uuid primary key default gen_random_uuid(),
  profile_id uuid not null references public.profiles (id) on delete cascade,
  acceptance_type text not null,
  document_version text not null,
  accepted_at timestamptz not null default timezone('utc', now()),
  source text not null default 'api_jwt_sync',
  client_asserted_at timestamptz,
  created_at timestamptz not null default timezone('utc', now()),
  constraint legal_acceptances_type_chk check (
    acceptance_type in ('terms', 'privacy', 'age_18')
  ),
  constraint legal_acceptances_document_version_len check (char_length(document_version) <= 128),
  constraint legal_acceptances_source_len check (char_length(source) <= 64),
  constraint legal_acceptances_profile_type_version_key unique (profile_id, acceptance_type, document_version)
);

create index if not exists legal_acceptances_profile_id_idx on public.legal_acceptances (profile_id);

comment on table public.legal_acceptances is 'Immutable-style record of signup compliance; rows inserted server-side from verified JWT user_metadata.';

alter table public.legal_acceptances enable row level security;

drop policy if exists legal_acceptances_select_own on public.legal_acceptances;
create policy legal_acceptances_select_own
on public.legal_acceptances
for select
to authenticated
using (profile_id = auth.uid() or public.current_user_is_admin());

drop policy if exists legal_acceptances_insert_own on public.legal_acceptances;
create policy legal_acceptances_insert_own
on public.legal_acceptances
for insert
to authenticated
with check (profile_id = auth.uid());
