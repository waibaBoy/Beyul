create or replace function public.current_user_is_admin()
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1
    from public.profiles
    where id = auth.uid()
      and is_admin = true
  );
$$;

create or replace function public.current_user_role_in_community(target_community_id uuid)
returns public.community_role
language sql
stable
security definer
set search_path = public
as $$
  select cm.role
  from public.community_members cm
  where cm.community_id = target_community_id
    and cm.profile_id = auth.uid()
  limit 1;
$$;

create or replace function public.current_user_is_community_member(target_community_id uuid)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1
    from public.community_members cm
    where cm.community_id = target_community_id
      and cm.profile_id = auth.uid()
  );
$$;

create or replace function public.current_user_is_community_staff(target_community_id uuid)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1
    from public.community_members cm
    where cm.community_id = target_community_id
      and cm.profile_id = auth.uid()
      and cm.role in ('moderator', 'admin', 'owner')
  );
$$;

create or replace function public.current_user_can_read_community(target_community_id uuid)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1
    from public.communities c
    where c.id = target_community_id
      and (
        c.visibility = 'public'
        or c.created_by = auth.uid()
        or public.current_user_is_admin()
        or public.current_user_is_community_member(c.id)
      )
  );
$$;

create or replace function public.current_user_can_read_market(target_market_id uuid)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1
    from public.markets m
    where m.id = target_market_id
      and (
        (
          m.market_access_mode = 'public'
          and m.status in ('open', 'awaiting_resolution', 'disputed', 'settled')
        )
        or m.creator_id = auth.uid()
        or public.current_user_is_admin()
        or (
          m.community_id is not null
          and public.current_user_can_read_community(m.community_id)
        )
      )
  );
$$;

create or replace function public.current_user_can_dispute_market(target_market_id uuid)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1
    from public.markets m
    where m.id = target_market_id
      and (
        m.creator_id = auth.uid()
        or exists (
          select 1
          from public.orders o
          where o.market_id = m.id
            and o.profile_id = auth.uid()
        )
        or exists (
          select 1
          from public.positions p
          where p.market_id = m.id
            and p.profile_id = auth.uid()
        )
      )
  );
$$;

alter table public.profiles enable row level security;
alter table public.user_wallets enable row level security;
alter table public.communities enable row level security;
alter table public.community_members enable row level security;
alter table public.posts enable row level security;
alter table public.settlement_sources enable row level security;
alter table public.market_creation_requests enable row level security;
alter table public.market_creation_request_answers enable row level security;
alter table public.markets enable row level security;
alter table public.market_outcomes enable row level security;
alter table public.orders enable row level security;
alter table public.trades enable row level security;
alter table public.positions enable row level security;
alter table public.market_resolution_candidates enable row level security;
alter table public.market_resolution_votes enable row level security;
alter table public.market_resolutions enable row level security;
alter table public.disputes enable row level security;
alter table public.dispute_evidence enable row level security;
alter table public.ledger_accounts enable row level security;
alter table public.ledger_transactions enable row level security;
alter table public.ledger_entries enable row level security;
alter table public.payment_intents enable row level security;

drop policy if exists profiles_select_authenticated on public.profiles;
create policy profiles_select_authenticated
on public.profiles
for select
to authenticated
using (true);

drop policy if exists profiles_insert_self on public.profiles;
create policy profiles_insert_self
on public.profiles
for insert
to authenticated
with check (id = auth.uid());

drop policy if exists profiles_update_self on public.profiles;
create policy profiles_update_self
on public.profiles
for update
to authenticated
using (id = auth.uid() or public.current_user_is_admin())
with check (
  id = auth.uid()
  or public.current_user_is_admin()
);

drop policy if exists user_wallets_select_own on public.user_wallets;
create policy user_wallets_select_own
on public.user_wallets
for select
to authenticated
using (profile_id = auth.uid() or public.current_user_is_admin());

drop policy if exists user_wallets_insert_own on public.user_wallets;
create policy user_wallets_insert_own
on public.user_wallets
for insert
to authenticated
with check (profile_id = auth.uid() or public.current_user_is_admin());

drop policy if exists user_wallets_update_own on public.user_wallets;
create policy user_wallets_update_own
on public.user_wallets
for update
to authenticated
using (profile_id = auth.uid() or public.current_user_is_admin())
with check (profile_id = auth.uid() or public.current_user_is_admin());

drop policy if exists user_wallets_delete_own on public.user_wallets;
create policy user_wallets_delete_own
on public.user_wallets
for delete
to authenticated
using (profile_id = auth.uid() or public.current_user_is_admin());

drop policy if exists communities_select_readable on public.communities;
create policy communities_select_readable
on public.communities
for select
to authenticated
using (public.current_user_can_read_community(id));

drop policy if exists communities_insert_authenticated on public.communities;
create policy communities_insert_authenticated
on public.communities
for insert
to authenticated
with check (created_by = auth.uid() or public.current_user_is_admin());

drop policy if exists communities_update_staff on public.communities;
create policy communities_update_staff
on public.communities
for update
to authenticated
using (
  created_by = auth.uid()
  or public.current_user_is_admin()
  or public.current_user_is_community_staff(id)
)
with check (
  created_by = auth.uid()
  or public.current_user_is_admin()
  or public.current_user_is_community_staff(id)
);

drop policy if exists community_members_select_readable on public.community_members;
create policy community_members_select_readable
on public.community_members
for select
to authenticated
using (
  profile_id = auth.uid()
  or public.current_user_is_admin()
  or public.current_user_can_read_community(community_id)
);

drop policy if exists community_members_insert_public_join_or_staff on public.community_members;
create policy community_members_insert_public_join_or_staff
on public.community_members
for insert
to authenticated
with check (
  public.current_user_is_admin()
  or public.current_user_is_community_staff(community_id)
  or (
    profile_id = auth.uid()
    and exists (
      select 1
      from public.communities c
      where c.id = community_id
        and c.visibility = 'public'
    )
  )
);

drop policy if exists community_members_update_staff on public.community_members;
create policy community_members_update_staff
on public.community_members
for update
to authenticated
using (
  public.current_user_is_admin()
  or public.current_user_is_community_staff(community_id)
)
with check (
  public.current_user_is_admin()
  or public.current_user_is_community_staff(community_id)
);

drop policy if exists community_members_delete_self_or_staff on public.community_members;
create policy community_members_delete_self_or_staff
on public.community_members
for delete
to authenticated
using (
  profile_id = auth.uid()
  or public.current_user_is_admin()
  or public.current_user_is_community_staff(community_id)
);

drop policy if exists posts_select_readable on public.posts;
create policy posts_select_readable
on public.posts
for select
to authenticated
using (
  (
    status = 'approved'
    and public.current_user_can_read_community(community_id)
  )
  or author_id = auth.uid()
  or public.current_user_is_admin()
  or public.current_user_is_community_staff(community_id)
);

drop policy if exists posts_insert_author on public.posts;
create policy posts_insert_author
on public.posts
for insert
to authenticated
with check (
  author_id = auth.uid()
  and public.current_user_can_read_community(community_id)
);

drop policy if exists posts_update_author_or_staff on public.posts;
create policy posts_update_author_or_staff
on public.posts
for update
to authenticated
using (
  public.current_user_is_admin()
  or public.current_user_is_community_staff(community_id)
  or (
    author_id = auth.uid()
    and status in ('draft', 'pending_review')
  )
)
with check (
  public.current_user_is_admin()
  or public.current_user_is_community_staff(community_id)
  or (
    author_id = auth.uid()
    and status in ('draft', 'pending_review')
  )
);

drop policy if exists settlement_sources_select_all on public.settlement_sources;
create policy settlement_sources_select_all
on public.settlement_sources
for select
to authenticated
using (true);

drop policy if exists market_requests_select_scope on public.market_creation_requests;
create policy market_requests_select_scope
on public.market_creation_requests
for select
to authenticated
using (
  requester_id = auth.uid()
  or public.current_user_is_admin()
  or (
    community_id is not null
    and public.current_user_is_community_staff(community_id)
  )
);

drop policy if exists market_requests_insert_own on public.market_creation_requests;
create policy market_requests_insert_own
on public.market_creation_requests
for insert
to authenticated
with check (requester_id = auth.uid() or public.current_user_is_admin());

drop policy if exists market_requests_update_scope on public.market_creation_requests;
create policy market_requests_update_scope
on public.market_creation_requests
for update
to authenticated
using (
  public.current_user_is_admin()
  or (
    requester_id = auth.uid()
    and status = 'draft'
  )
  or (
    community_id is not null
    and public.current_user_is_community_staff(community_id)
  )
)
with check (
  public.current_user_is_admin()
  or (
    requester_id = auth.uid()
    and status in ('draft', 'submitted')
  )
  or (
    community_id is not null
    and public.current_user_is_community_staff(community_id)
  )
);

drop policy if exists market_request_answers_select_scope on public.market_creation_request_answers;
create policy market_request_answers_select_scope
on public.market_creation_request_answers
for select
to authenticated
using (
  exists (
    select 1
    from public.market_creation_requests mcr
    where mcr.id = market_request_id
      and (
        mcr.requester_id = auth.uid()
        or public.current_user_is_admin()
        or (
          mcr.community_id is not null
          and public.current_user_is_community_staff(mcr.community_id)
        )
      )
  )
);

drop policy if exists market_request_answers_insert_owner on public.market_creation_request_answers;
create policy market_request_answers_insert_owner
on public.market_creation_request_answers
for insert
to authenticated
with check (
  exists (
    select 1
    from public.market_creation_requests mcr
    where mcr.id = market_request_id
      and mcr.requester_id = auth.uid()
      and mcr.status = 'draft'
  )
);

drop policy if exists market_request_answers_update_owner on public.market_creation_request_answers;
create policy market_request_answers_update_owner
on public.market_creation_request_answers
for update
to authenticated
using (
  exists (
    select 1
    from public.market_creation_requests mcr
    where mcr.id = market_request_id
      and mcr.requester_id = auth.uid()
      and mcr.status = 'draft'
  )
)
with check (
  exists (
    select 1
    from public.market_creation_requests mcr
    where mcr.id = market_request_id
      and mcr.requester_id = auth.uid()
      and mcr.status = 'draft'
  )
);

drop policy if exists markets_select_readable on public.markets;
create policy markets_select_readable
on public.markets
for select
to authenticated
using (public.current_user_can_read_market(id));

drop policy if exists market_outcomes_select_readable on public.market_outcomes;
create policy market_outcomes_select_readable
on public.market_outcomes
for select
to authenticated
using (public.current_user_can_read_market(market_id));

drop policy if exists orders_select_own on public.orders;
create policy orders_select_own
on public.orders
for select
to authenticated
using (
  profile_id = auth.uid()
  or public.current_user_is_admin()
);

drop policy if exists trades_select_market_scope on public.trades;
create policy trades_select_market_scope
on public.trades
for select
to authenticated
using (
  public.current_user_can_read_market(market_id)
);

drop policy if exists positions_select_own on public.positions;
create policy positions_select_own
on public.positions
for select
to authenticated
using (
  profile_id = auth.uid()
  or public.current_user_is_admin()
);

drop policy if exists market_resolutions_select_readable on public.market_resolutions;
create policy market_resolutions_select_readable
on public.market_resolutions
for select
to authenticated
using (public.current_user_can_read_market(market_id));

drop policy if exists disputes_select_scope on public.disputes;
create policy disputes_select_scope
on public.disputes
for select
to authenticated
using (
  raised_by = auth.uid()
  or public.current_user_is_admin()
  or exists (
    select 1
    from public.markets m
    where m.id = market_id
      and m.community_id is not null
      and public.current_user_is_community_staff(m.community_id)
  )
);

drop policy if exists disputes_insert_eligible on public.disputes;
create policy disputes_insert_eligible
on public.disputes
for insert
to authenticated
with check (
  raised_by = auth.uid()
  and public.current_user_can_dispute_market(market_id)
);

drop policy if exists disputes_update_staff on public.disputes;
create policy disputes_update_staff
on public.disputes
for update
to authenticated
using (
  public.current_user_is_admin()
  or exists (
    select 1
    from public.markets m
    where m.id = market_id
      and m.community_id is not null
      and public.current_user_is_community_staff(m.community_id)
  )
)
with check (
  public.current_user_is_admin()
  or exists (
    select 1
    from public.markets m
    where m.id = market_id
      and m.community_id is not null
      and public.current_user_is_community_staff(m.community_id)
  )
);

drop policy if exists dispute_evidence_select_scope on public.dispute_evidence;
create policy dispute_evidence_select_scope
on public.dispute_evidence
for select
to authenticated
using (
  submitted_by = auth.uid()
  or public.current_user_is_admin()
  or exists (
    select 1
    from public.disputes d
    join public.markets m on m.id = d.market_id
    where d.id = dispute_id
      and (
        d.raised_by = auth.uid()
        or (
          m.community_id is not null
          and public.current_user_is_community_staff(m.community_id)
        )
      )
  )
);

drop policy if exists dispute_evidence_insert_scope on public.dispute_evidence;
create policy dispute_evidence_insert_scope
on public.dispute_evidence
for insert
to authenticated
with check (
  submitted_by = auth.uid()
  and exists (
    select 1
    from public.disputes d
    where d.id = dispute_id
      and d.raised_by = auth.uid()
  )
);

drop policy if exists payment_intents_select_own on public.payment_intents;
create policy payment_intents_select_own
on public.payment_intents
for select
to authenticated
using (
  profile_id = auth.uid()
  or public.current_user_is_admin()
);
