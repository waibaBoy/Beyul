-- Run manually against Supabase for performance indexes
-- NOTE: CONCURRENTLY requires running outside a transaction block

create index concurrently if not exists idx_positions_profile_id
  on public.positions(profile_id);

create index concurrently if not exists idx_positions_market_outcome
  on public.positions(market_id, outcome_id);

create index concurrently if not exists idx_trades_outcome_executed_at
  on public.trades(outcome_id, executed_at desc);

create index concurrently if not exists idx_trades_taker_executed
  on public.trades(taker_profile_id, executed_at desc);

create index concurrently if not exists idx_orders_outcome_status
  on public.orders(outcome_id, status) where status in ('open', 'partially_filled');

create index concurrently if not exists idx_markets_status_created
  on public.markets(status, created_at desc);

create index concurrently if not exists idx_api_keys_hash_active
  on public.api_keys(key_hash) where is_active = true;

create index concurrently if not exists idx_transfers_profile_created
  on public.transfer_requests(profile_id, created_at desc);
