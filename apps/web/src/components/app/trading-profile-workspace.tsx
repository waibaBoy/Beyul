"use client";

import { useEffect, useState } from "react";
import { beyulApiFetch } from "@/lib/api/beyul-api";
import { useAuth } from "@/components/auth/auth-provider";

type TradingProfile = {
  profile_id: string | null;
  username: string;
  display_name: string | null;
  total_positions: number;
  realized_pnl: string;
  total_trades: number;
  total_volume: string;
  follower_count: number;
  following_count: number;
  is_following: boolean;
};

type FollowEntry = { username: string; display_name: string | null; followed_at: string };

const fmt = (v: string | number, d = 2) => {
  const n = Number(v);
  return Number.isFinite(n) ? n.toLocaleString(undefined, { maximumFractionDigits: d }) : "—";
};

export const TradingProfileWorkspace = ({ username }: { username: string }) => {
  const { getAccessToken, session } = useAuth();
  const [profile, setProfile] = useState<TradingProfile | null>(null);
  const [followers, setFollowers] = useState<FollowEntry[]>([]);
  const [following, setFollowing] = useState<FollowEntry[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [followLoading, setFollowLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<"followers" | "following">("followers");

  const load = async () => {
    setIsLoading(true);
    try {
      const accessToken = await getAccessToken().catch(() => null);
      const [prof, frs, fng] = await Promise.all([
        beyulApiFetch<TradingProfile>(`/api/v1/social/profile/${username}`, { accessToken: accessToken ?? undefined }),
        beyulApiFetch<{ users: FollowEntry[] }>(`/api/v1/social/followers/${username}`),
        beyulApiFetch<{ users: FollowEntry[] }>(`/api/v1/social/following/${username}`),
      ]);
      setProfile(prof);
      setFollowers(frs.users);
      setFollowing(fng.users);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load profile");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => { void load(); }, [username, session]);

  const toggleFollow = async () => {
    if (!profile || !session) return;
    setFollowLoading(true);
    try {
      const accessToken = await getAccessToken();
      const endpoint = profile.is_following ? "/api/v1/social/unfollow" : "/api/v1/social/follow";
      await beyulApiFetch(endpoint, { method: "POST", accessToken, json: { username } });
      await load();
    } finally {
      setFollowLoading(false);
    }
  };

  if (isLoading) return <div className="tp-loading">Loading profile…</div>;
  if (error) return <div className="tp-error">{error}</div>;
  if (!profile) return <div className="tp-error">Profile not found</div>;

  const pnlN = Number(profile.realized_pnl);
  const pnlClass = pnlN > 0 ? "tp-pnl-pos" : pnlN < 0 ? "tp-pnl-neg" : "";

  return (
    <div className="tp-shell">
      <div className="tp-header">
        <div className="tp-identity">
          <div className="tp-avatar">{(profile.display_name || username).charAt(0).toUpperCase()}</div>
          <div>
            <h2 className="tp-display-name">{profile.display_name || username}</h2>
            <span className="tp-username">@{profile.username}</span>
          </div>
        </div>
        {session ? (
          <button
            type="button"
            className={`tp-follow-btn ${profile.is_following ? "tp-following" : ""}`}
            onClick={toggleFollow}
            disabled={followLoading}
          >
            {profile.is_following ? "Following" : "Follow"}
          </button>
        ) : null}
      </div>

      <div className="tp-stats-grid">
        <div className="tp-stat">
          <span className="tp-stat-value">{profile.total_trades}</span>
          <span className="tp-stat-label">Trades</span>
        </div>
        <div className="tp-stat">
          <span className="tp-stat-value">{fmt(profile.total_volume)}</span>
          <span className="tp-stat-label">Volume</span>
        </div>
        <div className="tp-stat">
          <span className={`tp-stat-value ${pnlClass}`}>{fmt(profile.realized_pnl)}</span>
          <span className="tp-stat-label">Realized PnL</span>
        </div>
        <div className="tp-stat">
          <span className="tp-stat-value">{profile.total_positions}</span>
          <span className="tp-stat-label">Positions</span>
        </div>
        <div className="tp-stat">
          <span className="tp-stat-value">{profile.follower_count}</span>
          <span className="tp-stat-label">Followers</span>
        </div>
        <div className="tp-stat">
          <span className="tp-stat-value">{profile.following_count}</span>
          <span className="tp-stat-label">Following</span>
        </div>
      </div>

      <div className="tp-tab-bar">
        <button type="button" className={`tp-tab ${tab === "followers" ? "is-active" : ""}`} onClick={() => setTab("followers")}>
          Followers ({followers.length})
        </button>
        <button type="button" className={`tp-tab ${tab === "following" ? "is-active" : ""}`} onClick={() => setTab("following")}>
          Following ({following.length})
        </button>
      </div>

      <div className="tp-list">
        {(tab === "followers" ? followers : following).length === 0 ? (
          <p className="tp-empty">No {tab} yet.</p>
        ) : (
          (tab === "followers" ? followers : following).map((u) => (
            <a key={u.username} href={`/profile/${u.username}`} className="tp-user-row">
              <div className="tp-user-avatar">{(u.display_name || u.username).charAt(0).toUpperCase()}</div>
              <div>
                <strong>{u.display_name || u.username}</strong>
                <span className="tp-username">@{u.username}</span>
              </div>
            </a>
          ))
        )}
      </div>
    </div>
  );
};
