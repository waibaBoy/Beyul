-- API keys for programmatic trading

create table if not exists public.api_keys (
  id uuid primary key default gen_random_uuid(),
  profile_id uuid not null references public.profiles(id),
  label text not null,
  key_hash text not null,
  key_prefix text not null,
  permissions jsonb not null default '["read","trade"]'::jsonb,
  is_active boolean not null default true,
  last_used_at timestamptz,
  expires_at timestamptz,
  created_at timestamptz not null default now(),
  revoked_at timestamptz
);

create unique index if not exists idx_api_keys_hash on public.api_keys(key_hash);
create index if not exists idx_api_keys_profile on public.api_keys(profile_id);

alter table public.api_keys enable row level security;

create policy "select_own_keys" on public.api_keys for select using (
  profile_id = auth.uid()
);
create policy "insert_own_keys" on public.api_keys for insert with check (
  profile_id = auth.uid()
);
create policy "update_own_keys" on public.api_keys for update using (
  profile_id = auth.uid()
);
