# RLS Policy Plan

This document outlines the first-pass Row Level Security model for Supabase.

## Guiding principles

- Public read should be explicit, not assumed.
- Private-group access should be membership-based.
- Users should only mutate rows they own unless they hold a moderator/admin role.
- Service-role operations should handle matching, settlement, and accounting writes.

## Profiles

Read:
- Authenticated users can read public profile fields for other users.

Write:
- Users can insert/update only their own `profiles` row.
- Only service role or admins can set `is_admin`.

## User wallets

Read:
- Users can read their own wallets.
- Service role can read all wallets.

Write:
- Users can insert/update/delete only their own wallets.

## Communities and memberships

Read:
- Public communities readable by all authenticated users.
- Private communities readable by members and service role.

Write:
- Community creation allowed for authenticated users.
- Membership changes restricted to owners/admins/moderators depending on action.

## Posts

Read:
- Approved posts in public communities readable by all authenticated users.
- Approved posts in private communities readable by members.
- Pending/rejected posts readable by author plus community moderators/admins/owners.

Write:
- Authors can create posts in communities they can post to.
- Authors can edit their own posts while status is `draft` or `pending_review`.
- Moderators/admins/owners can update review fields and status.

## Market creation requests

Read:
- Requester can read own requests.
- Community staff can read requests tied to their community.
- Service role and platform admins can read all requests.

Write:
- Authenticated users can create their own requests.
- Only requester can edit draft requests.
- Only community staff/platform admins can approve or reject.

## Markets and outcomes

Read:
- Public open/settled markets readable by all authenticated users.
- Private-group markets readable by community members.
- Pending internal markets readable by creator, moderators, admins, and service role.

Write:
- Direct client writes should be blocked.
- Service role or privileged backend creates and updates markets/outcomes.

## Orders, trades, and positions

Read:
- Users can read their own orders and positions.
- Users can read public market trade tape if market is readable.
- Private-group trade tape readable only by members.

Write:
- Orders should be inserted through backend or RPC only, not direct table writes from clients.
- Trades and positions should be service-role only.

## Resolution and disputes

Read:
- Resolution records readable to any user who can read the market.
- Disputes readable to involved user, moderators/admins, and service role.
- Dispute evidence readable to dispute participants and reviewers.

Write:
- Resolution candidates and votes should be service-role or council-member scoped.
- Disputes can be created by eligible market participants during dispute window.
- Final dispute decision should be admin/service role only.

## Ledger and payments

Read:
- Users can read their own `payment_intents`.
- Users should not directly query other users' ledger accounts or entries.
- Consider exposing user balances through a secured view/RPC rather than raw ledger tables.

Write:
- Ledger tables should be service-role only.
- Payment intents may be user-created through RPC/backend, but provider status updates must be service-role only.

## Recommended implementation order

1. Enable RLS on all user-facing tables.
2. Start with read policies for public vs private communities and markets.
3. Add self-service write policies for profiles, wallets, posts, and draft requests.
4. Keep trading, resolution, and ledger writes behind backend/service role.
5. Expose secure RPCs/views for balances, eligible markets, and moderation queues.
