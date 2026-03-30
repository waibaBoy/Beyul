create table if not exists public.profiles (
  id uuid primary key references auth.users (id) on delete cascade,
  username citext unique,
  display_name text not null,
  bio text,
  avatar_url text,
  phone_e164 text,
  country_code text,
  is_admin boolean not null default false,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.user_wallets (
  id uuid primary key default gen_random_uuid(),
  profile_id uuid not null references public.profiles (id) on delete cascade,
  chain_name text not null,
  wallet_address text not null,
  is_primary boolean not null default false,
  verified_at timestamptz,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  unique (chain_name, wallet_address)
);

create table if not exists public.communities (
  id uuid primary key default gen_random_uuid(),
  slug citext not null unique,
  name text not null,
  description text,
  visibility public.community_visibility not null default 'public',
  require_post_approval boolean not null default true,
  require_market_approval boolean not null default true,
  created_by uuid not null references public.profiles (id),
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.community_members (
  id uuid primary key default gen_random_uuid(),
  community_id uuid not null references public.communities (id) on delete cascade,
  profile_id uuid not null references public.profiles (id) on delete cascade,
  role public.community_role not null default 'member',
  joined_at timestamptz not null default timezone('utc', now()),
  unique (community_id, profile_id)
);

create table if not exists public.posts (
  id uuid primary key default gen_random_uuid(),
  community_id uuid not null references public.communities (id) on delete cascade,
  author_id uuid not null references public.profiles (id),
  title text,
  body text not null,
  status public.post_status not null default 'pending_review',
  submitted_at timestamptz,
  reviewed_at timestamptz,
  reviewed_by uuid references public.profiles (id),
  review_notes text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

drop trigger if exists trg_profiles_updated_at on public.profiles;
create trigger trg_profiles_updated_at before update on public.profiles for each row execute function public.set_updated_at();

drop trigger if exists trg_user_wallets_updated_at on public.user_wallets;
create trigger trg_user_wallets_updated_at before update on public.user_wallets for each row execute function public.set_updated_at();

drop trigger if exists trg_communities_updated_at on public.communities;
create trigger trg_communities_updated_at before update on public.communities for each row execute function public.set_updated_at();

drop trigger if exists trg_posts_updated_at on public.posts;
create trigger trg_posts_updated_at before update on public.posts for each row execute function public.set_updated_at();
