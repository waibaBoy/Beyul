-- Creator reward tier reference data and creator stats view.
-- Run after 011.

create table if not exists public.creator_reward_tiers (
  id serial primary key,
  tier_code text not null unique,
  tier_label text not null,
  min_volume_usd numeric(20, 2) not null default 0,
  fee_share_bps integer not null default 0 check (fee_share_bps between 0 and 5000),
  badge_color text not null default '#6b7280',
  sort_order integer not null default 0
);

comment on table public.creator_reward_tiers is 'Reference table defining volume-based reward tiers for market creators.';

insert into public.creator_reward_tiers (tier_code, tier_label, min_volume_usd, fee_share_bps, badge_color, sort_order)
values
  ('starter',   'Starter',   0,       0,    '#6b7280', 0),
  ('bronze',    'Bronze',    1000,    1000, '#cd7f32', 1),
  ('silver',    'Silver',    10000,   1500, '#c0c0c0', 2),
  ('gold',      'Gold',      50000,   2500, '#f7b955', 3),
  ('platinum',  'Platinum',  250000,  3500, '#e5e4e2', 4),
  ('diamond',   'Diamond',   1000000, 5000, '#b9f2ff', 5)
on conflict (tier_code) do update
  set tier_label      = excluded.tier_label,
      min_volume_usd  = excluded.min_volume_usd,
      fee_share_bps   = excluded.fee_share_bps,
      badge_color     = excluded.badge_color,
      sort_order      = excluded.sort_order;

-- Lightweight view for per-creator aggregate stats.
create or replace view public.creator_stats_v as
select
  m.creator_id as profile_id,
  count(distinct m.id)       as markets_created,
  count(distinct case when m.status = 'open' then m.id end) as markets_open,
  count(distinct case when m.status = 'settled' then m.id end) as markets_settled,
  coalesce(sum(m.total_volume), 0) as total_volume,
  coalesce(sum(m.total_trades_count), 0) as total_trades
from public.markets m
group by m.creator_id;

comment on view public.creator_stats_v is 'Aggregated creator statistics computed from the markets table.';
