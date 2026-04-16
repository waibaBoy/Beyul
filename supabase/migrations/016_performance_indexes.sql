-- Performance indexes for high-traffic query patterns

-- Positions by profile (portfolio, leaderboard, trading stats)
create index if not exists idx_positions_profile_id
  on public.positions(profile_id);

-- Positions by market + outcome (settlement, depth queries)
create index if not exists idx_positions_market_outcome
  on public.positions(market_id, outcome_id);

-- Trades by outcome + executed_at (last price per outcome, quote loading)
create index if not exists idx_trades_outcome_executed_at
  on public.trades(outcome_id, executed_at desc);

-- Trades by taker profile (trading stats view, PnL calculations)
create index if not exists idx_trades_taker_executed
  on public.trades(taker_profile_id, executed_at desc);

-- Orders by outcome + status (order book depth aggregation)
create index if not exists idx_orders_outcome_status
  on public.orders(outcome_id, status) where status in ('open', 'partially_filled');

-- Markets by status (active market listing)
create index if not exists idx_markets_status_created
  on public.markets(status, created_at desc);

-- API keys by hash (key validation lookup)
create index if not exists idx_api_keys_hash_active
  on public.api_keys(key_hash) where is_active = true;

-- Transfer requests by profile + created (wallet history)
create index if not exists idx_transfers_profile_created
  on public.transfer_requests(profile_id, created_at desc);
