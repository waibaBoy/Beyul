create extension if not exists pgcrypto;
create extension if not exists citext;

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = timezone('utc', now());
  return new;
end;
$$;

do $$
begin
  if not exists (select 1 from pg_type where typname = 'community_visibility') then
    create type public.community_visibility as enum ('public', 'private');
  end if;
  if not exists (select 1 from pg_type where typname = 'community_role') then
    create type public.community_role as enum ('member', 'moderator', 'admin', 'owner');
  end if;
  if not exists (select 1 from pg_type where typname = 'post_status') then
    create type public.post_status as enum ('draft', 'pending_review', 'approved', 'rejected', 'archived');
  end if;
  if not exists (select 1 from pg_type where typname = 'settlement_tier') then
    create type public.settlement_tier as enum ('automatic', 'semi_automatic', 'community_verified');
  end if;
  if not exists (select 1 from pg_type where typname = 'market_access_mode') then
    create type public.market_access_mode as enum ('public', 'private_group');
  end if;
  if not exists (select 1 from pg_type where typname = 'market_status') then
    create type public.market_status as enum (
      'draft',
      'pending_review',
      'pending_liquidity',
      'open',
      'trading_paused',
      'awaiting_resolution',
      'disputed',
      'settled',
      'cancelled'
    );
  end if;
  if not exists (select 1 from pg_type where typname = 'market_resolution_mode') then
    create type public.market_resolution_mode as enum ('oracle', 'api', 'council');
  end if;
  if not exists (select 1 from pg_type where typname = 'market_request_status') then
    create type public.market_request_status as enum ('draft', 'submitted', 'approved', 'rejected', 'converted');
  end if;
  if not exists (select 1 from pg_type where typname = 'outcome_status') then
    create type public.outcome_status as enum ('active', 'winning', 'losing', 'voided');
  end if;
  if not exists (select 1 from pg_type where typname = 'order_side') then
    create type public.order_side as enum ('buy', 'sell');
  end if;
  if not exists (select 1 from pg_type where typname = 'order_type') then
    create type public.order_type as enum ('market', 'limit');
  end if;
  if not exists (select 1 from pg_type where typname = 'order_status') then
    create type public.order_status as enum (
      'pending_acceptance',
      'open',
      'partially_filled',
      'filled',
      'cancelled',
      'rejected',
      'expired'
    );
  end if;
  if not exists (select 1 from pg_type where typname = 'asset_kind') then
    create type public.asset_kind as enum ('fiat', 'stablecoin', 'crypto');
  end if;
  if not exists (select 1 from pg_type where typname = 'rail_type') then
    create type public.rail_type as enum ('custodial', 'onchain');
  end if;
  if not exists (select 1 from pg_type where typname = 'ledger_owner_type') then
    create type public.ledger_owner_type as enum ('platform', 'user', 'market', 'fee_pool', 'treasury');
  end if;
  if not exists (select 1 from pg_type where typname = 'ledger_transaction_type') then
    create type public.ledger_transaction_type as enum (
      'deposit',
      'withdrawal',
      'bet_lock',
      'trade_settlement',
      'refund',
      'payout',
      'platform_fee',
      'dispute_fee',
      'adjustment'
    );
  end if;
  if not exists (select 1 from pg_type where typname = 'ledger_entry_direction') then
    create type public.ledger_entry_direction as enum ('debit', 'credit');
  end if;
  if not exists (select 1 from pg_type where typname = 'payment_intent_type') then
    create type public.payment_intent_type as enum ('deposit', 'withdrawal', 'payout', 'onchain_fund', 'onchain_claim');
  end if;
  if not exists (select 1 from pg_type where typname = 'payment_intent_status') then
    create type public.payment_intent_status as enum ('created', 'processing', 'succeeded', 'failed', 'cancelled');
  end if;
  if not exists (select 1 from pg_type where typname = 'resolution_candidate_status') then
    create type public.resolution_candidate_status as enum ('proposed', 'confirmed', 'rejected', 'superseded');
  end if;
  if not exists (select 1 from pg_type where typname = 'vote_decision') then
    create type public.vote_decision as enum ('approve', 'reject');
  end if;
  if not exists (select 1 from pg_type where typname = 'dispute_status') then
    create type public.dispute_status as enum ('open', 'under_review', 'upheld', 'dismissed', 'withdrawn');
  end if;
end
$$;
