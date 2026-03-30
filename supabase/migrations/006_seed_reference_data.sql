insert into public.assets (code, name, kind, decimals, metadata)
values
  ('AUD', 'Australian Dollar', 'fiat', 2, '{"symbol":"$"}'::jsonb),
  ('USDC', 'USD Coin', 'stablecoin', 6, '{"network":"polygon"}'::jsonb)
on conflict (code) do update
set
  name = excluded.name,
  kind = excluded.kind,
  decimals = excluded.decimals,
  metadata = excluded.metadata;

insert into public.settlement_sources (
  code,
  name,
  tier,
  resolution_mode,
  provider_name,
  source_type,
  base_url,
  requires_manual_review,
  metadata
)
values
  (
    'CHAINLINK_CRYPTO',
    'Chainlink Crypto Feeds',
    'automatic',
    'oracle',
    'Chainlink',
    'oracle_feed',
    'https://data.chain.link',
    false,
    '{"categories":["crypto","forex"]}'::jsonb
  ),
  (
    'SPORTRADAR_RESULTS',
    'SportRadar Results Feed',
    'semi_automatic',
    'api',
    'SportRadar',
    'sports_api',
    'https://developer.sportradar.com',
    true,
    '{"categories":["nrl","afl","cricket","tennis","f1"]}'::jsonb
  ),
  (
    'AEC_ELECTIONS',
    'Australian Electoral Commission',
    'semi_automatic',
    'api',
    'AEC',
    'official_api',
    'https://www.aec.gov.au',
    true,
    '{"categories":["federal_elections"]}'::jsonb
  ),
  (
    'RBA_RATES',
    'Reserve Bank of Australia',
    'semi_automatic',
    'api',
    'RBA',
    'official_api',
    'https://www.rba.gov.au',
    true,
    '{"categories":["interest_rates"]}'::jsonb
  ),
  (
    'COUNCIL_VERIFIED',
    'Beyul Council Verified',
    'community_verified',
    'council',
    'Beyul Council',
    'manual_review',
    null,
    true,
    '{"minimum_votes":3,"dispute_window_hours":24}'::jsonb
  )
on conflict (code) do update
set
  name = excluded.name,
  tier = excluded.tier,
  resolution_mode = excluded.resolution_mode,
  provider_name = excluded.provider_name,
  source_type = excluded.source_type,
  base_url = excluded.base_url,
  requires_manual_review = excluded.requires_manual_review,
  metadata = excluded.metadata;
