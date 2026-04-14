-- Run manually against Supabase if not using migration runner
-- Social follows + trading stats view

create table if not exists public.follows (
  id uuid primary key default gen_random_uuid(),
  follower_id uuid not null references public.profiles(id),
  following_id uuid not null references public.profiles(id),
  created_at timestamptz not null default now(),
  constraint follows_no_self_follow check (follower_id <> following_id),
  constraint follows_unique unique (follower_id, following_id)
);

create index if not exists idx_follows_follower on public.follows(follower_id);
create index if not exists idx_follows_following on public.follows(following_id);

create or replace view public.trading_stats_v as
select
  p.id as profile_id,
  p.username,
  p.display_name,
  coalesce(pos.total_positions, 0) as total_positions,
  coalesce(pos.realized_pnl, 0) as realized_pnl,
  coalesce(t.total_trades, 0) as total_trades,
  coalesce(t.total_volume, 0) as total_volume,
  coalesce(f_in.follower_count, 0) as follower_count,
  coalesce(f_out.following_count, 0) as following_count
from public.profiles p
left join lateral (
  select count(*) as total_positions, coalesce(sum(realized_pnl), 0) as realized_pnl
  from public.positions where profile_id = p.id
) pos on true
left join lateral (
  select count(*) as total_trades, coalesce(sum(gross_notional), 0) as total_volume
  from public.trades where taker_profile_id = p.id or maker_profile_id = p.id
) t on true
left join lateral (
  select count(*) as follower_count from public.follows where following_id = p.id
) f_in on true
left join lateral (
  select count(*) as following_count from public.follows where follower_id = p.id
) f_out on true;

alter table public.follows enable row level security;

create policy "select_follows" on public.follows for select using (true);
create policy "insert_own_follow" on public.follows for insert with check (
  follower_id = auth.uid()
);
create policy "delete_own_follow" on public.follows for delete using (
  follower_id = auth.uid()
);
