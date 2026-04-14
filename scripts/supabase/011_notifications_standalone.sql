-- Standalone version of 011_notifications.sql for manual application via Supabase SQL editor.
-- Safe to re-run (all statements use IF NOT EXISTS / DROP IF EXISTS).

create table if not exists public.notifications (
  id uuid primary key default gen_random_uuid(),
  profile_id uuid not null references public.profiles (id) on delete cascade,
  kind text not null,
  title text not null,
  body text,
  market_slug text,
  market_id uuid references public.markets (id) on delete set null,
  order_id uuid references public.orders (id) on delete set null,
  payload jsonb not null default '{}'::jsonb,
  is_read boolean not null default false,
  created_at timestamptz not null default timezone('utc', now()),
  constraint notifications_kind_chk check (
    kind in (
      'order_filled', 'order_cancelled', 'order_rejected',
      'market_opened', 'market_settled', 'market_cancelled', 'market_disputed',
      'settlement_requested', 'settlement_finalized',
      'price_alert', 'system'
    )
  )
);

create index if not exists notifications_profile_id_idx on public.notifications (profile_id);
create index if not exists notifications_profile_unread_idx on public.notifications (profile_id) where not is_read;
create index if not exists notifications_created_at_idx on public.notifications (created_at desc);

alter table public.notifications enable row level security;

drop policy if exists notifications_select_own on public.notifications;
create policy notifications_select_own
on public.notifications
for select
to authenticated
using (profile_id = auth.uid() or public.current_user_is_admin());

drop policy if exists notifications_update_own on public.notifications;
create policy notifications_update_own
on public.notifications
for update
to authenticated
using (profile_id = auth.uid())
with check (profile_id = auth.uid());

drop policy if exists notifications_insert_system on public.notifications;
create policy notifications_insert_system
on public.notifications
for insert
to authenticated
with check (profile_id = auth.uid() or public.current_user_is_admin());
