export type BackendUser = {
  id: string;
  username: string;
  display_name: string;
  is_admin: boolean;
};

export type Community = {
  id: string;
  slug: string;
  name: string;
  description: string | null;
  visibility: "public" | "private";
  require_post_approval: boolean;
  require_market_approval: boolean;
};

export type CommunityMember = {
  id: string;
  profile_id: string;
  username: string;
  display_name: string;
  role: string;
};

export type CommunityCreateInput = {
  slug: string;
  name: string;
  description?: string;
  visibility: "public" | "private";
  require_post_approval: boolean;
  require_market_approval: boolean;
};

export type MarketRequest = {
  id: string;
  requester_id: string;
  requester_username: string | null;
  requester_display_name: string;
  community_id: string | null;
  community_slug: string | null;
  community_name: string | null;
  title: string;
  slug: string | null;
  question: string;
  description: string | null;
  market_access_mode: "public" | "private_group";
  requested_rail: "custodial" | "onchain" | null;
  resolution_mode: "oracle" | "api" | "council";
  settlement_reference_url: string | null;
  status: string;
  review_notes: string | null;
  submitted_at: string | null;
  reviewed_at: string | null;
  created_at: string;
  updated_at: string;
};

export type MarketRequestCreateInput = {
  title: string;
  slug?: string;
  question: string;
  description?: string;
  market_access_mode: "public" | "private_group";
  requested_rail?: "custodial" | "onchain";
  resolution_mode: "oracle" | "api" | "council";
  community_id?: string;
  settlement_source_id?: string;
  settlement_reference_url?: string;
};

export type MarketRequestAnswer = {
  question_key: string;
  question_label: string;
  answer_text: string | null;
  answer_json: Record<string, unknown> | null;
};

export type Post = {
  id: string;
  community_id: string;
  community_slug: string;
  community_name: string;
  author_id: string;
  author_username: string | null;
  author_display_name: string;
  title: string | null;
  body: string;
  status: string;
  submitted_at: string | null;
  reviewed_at: string | null;
  reviewed_by: string | null;
  review_notes: string | null;
  created_at: string;
  updated_at: string;
};

export type PostCreateInput = {
  title?: string;
  body: string;
};

export type ReviewQueue = {
  pending_posts: Post[];
  pending_market_requests: MarketRequest[];
};

export type MarketOutcome = {
  id: string;
  code: string;
  label: string;
  outcome_index: number;
  status: string;
  settlement_value: string | null;
};

export type Market = {
  id: string;
  slug: string;
  title: string;
  question: string;
  description: string | null;
  status: string;
  market_access_mode: string;
  rail_mode: string;
  resolution_mode: string;
  rules_text: string;
  community_id: string | null;
  community_slug: string | null;
  community_name: string | null;
  created_from_request_id: string | null;
  creator_id: string;
  settlement_source_id: string;
  settlement_reference_url: string | null;
  min_seed_amount: string;
  min_participants: number;
  created_at: string;
  updated_at: string;
  outcomes: MarketOutcome[];
};
