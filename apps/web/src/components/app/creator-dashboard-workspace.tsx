"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/components/auth/auth-provider";
import { sattaApiFetch } from "@/lib/api/beyul-api";
import type {
  CreatorLeaderboardEntry,
  CreatorLeaderboardResponse,
  CreatorRewardTier,
  CreatorStats,
  CreatorTiersResponse,
} from "@/lib/api/types";

function formatVolume(vol: string): string {
  const n = parseFloat(vol);
  if (!Number.isFinite(n) || n === 0) return "$0";
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `$${(n / 1_000).toFixed(1)}K`;
  return `$${n.toFixed(2)}`;
}

function feeShareLabel(bps: number): string {
  if (bps === 0) return "—";
  return `${(bps / 100).toFixed(0)}%`;
}

export const CreatorDashboardWorkspace = () => {
  const { user, getAccessToken } = useAuth();
  const [stats, setStats] = useState<CreatorStats | null>(null);
  const [tiers, setTiers] = useState<CreatorRewardTier[]>([]);
  const [leaderboard, setLeaderboard] = useState<CreatorLeaderboardEntry[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    try {
      const tiersRes = await sattaApiFetch<CreatorTiersResponse>("/api/v1/creators/tiers");
      setTiers(tiersRes.tiers);

      const lbRes = await sattaApiFetch<CreatorLeaderboardResponse>("/api/v1/creators/leaderboard?limit=10");
      setLeaderboard(lbRes.entries);

      if (user) {
        const token = await getAccessToken();
        if (token) {
          const statsRes = await sattaApiFetch<CreatorStats>("/api/v1/creators/me/stats", { accessToken: token });
          setStats(statsRes);
        }
      }
    } catch {
      // silent
    } finally {
      setIsLoading(false);
    }
  }, [user, getAccessToken]);

  useEffect(() => {
    void fetchData();
  }, [fetchData]);

  if (isLoading) {
    return <div className="creator-loading">Loading creator data...</div>;
  }

  return (
    <div className="creator-dashboard">
      {user && stats ? <MyCreatorStats stats={stats} /> : <SignInPrompt />}
      <TierTable tiers={tiers} currentTierCode={stats?.current_tier.tier_code} />
      <Leaderboard entries={leaderboard} />
    </div>
  );
};

const SignInPrompt = () => (
  <div className="creator-card creator-prompt">
    <h3>Sign in to see your creator stats</h3>
    <p>Create markets, drive volume, and earn a share of the platform fees.</p>
    <Link href="/auth/sign-in" className="creator-cta-btn">Sign in</Link>
  </div>
);

const MyCreatorStats = ({ stats }: { stats: CreatorStats }) => (
  <div className="creator-card creator-mystats">
    <div className="creator-mystats-header">
      <div>
        <span className="creator-mystats-label">Your creator tier</span>
        <div className="creator-tier-badge" style={{ borderColor: stats.current_tier.badge_color }}>
          <span className="creator-tier-dot" style={{ background: stats.current_tier.badge_color }} />
          {stats.current_tier.tier_label}
        </div>
      </div>
      {stats.current_tier.fee_share_bps > 0 ? (
        <div className="creator-fee-share-pill">
          {feeShareLabel(stats.current_tier.fee_share_bps)} fee share
        </div>
      ) : null}
    </div>

    <div className="creator-stat-grid">
      <div className="creator-stat-item">
        <span className="creator-stat-value">{stats.markets_created}</span>
        <span className="creator-stat-label">Markets created</span>
      </div>
      <div className="creator-stat-item">
        <span className="creator-stat-value">{stats.markets_open}</span>
        <span className="creator-stat-label">Open</span>
      </div>
      <div className="creator-stat-item">
        <span className="creator-stat-value">{stats.markets_settled}</span>
        <span className="creator-stat-label">Settled</span>
      </div>
      <div className="creator-stat-item">
        <span className="creator-stat-value">{formatVolume(stats.total_volume)}</span>
        <span className="creator-stat-label">Total volume</span>
      </div>
      <div className="creator-stat-item">
        <span className="creator-stat-value">{stats.total_trades}</span>
        <span className="creator-stat-label">Total trades</span>
      </div>
    </div>

    {stats.next_tier ? (
      <div className="creator-progress-section">
        <div className="creator-progress-labels">
          <span>{stats.current_tier.tier_label}</span>
          <span>{stats.next_tier.tier_label}</span>
        </div>
        <div className="creator-progress-bar">
          <div
            className="creator-progress-fill"
            style={{
              width: `${Math.min(stats.progress_pct, 100)}%`,
              background: stats.next_tier.badge_color,
            }}
          />
        </div>
        <span className="creator-progress-hint">
          {formatVolume(stats.volume_to_next_tier)} more volume to reach {stats.next_tier.tier_label}
        </span>
      </div>
    ) : (
      <div className="creator-progress-section">
        <span className="creator-progress-hint">You&apos;ve reached the highest tier!</span>
      </div>
    )}
  </div>
);

const TierTable = ({ tiers, currentTierCode }: { tiers: CreatorRewardTier[]; currentTierCode?: string }) => (
  <div className="creator-card">
    <h3 className="creator-card-title">Reward tiers</h3>
    <p className="creator-card-desc">
      Reach volume milestones across your markets to unlock a share of the platform fees collected.
    </p>
    <div className="creator-tier-table">
      <div className="creator-tier-row creator-tier-header">
        <span>Tier</span>
        <span>Min volume</span>
        <span>Fee share</span>
      </div>
      {tiers.map((tier) => (
        <div
          key={tier.tier_code}
          className={`creator-tier-row ${currentTierCode === tier.tier_code ? "creator-tier-current" : ""}`}
        >
          <span className="creator-tier-cell-name">
            <span className="creator-tier-dot" style={{ background: tier.badge_color }} />
            {tier.tier_label}
          </span>
          <span>{formatVolume(tier.min_volume_usd)}</span>
          <span>{feeShareLabel(tier.fee_share_bps)}</span>
        </div>
      ))}
    </div>
  </div>
);

const Leaderboard = ({ entries }: { entries: CreatorLeaderboardEntry[] }) => {
  if (entries.length === 0) {
    return (
      <div className="creator-card">
        <h3 className="creator-card-title">Top creators</h3>
        <p className="creator-card-desc">No creators with volume yet. Be the first!</p>
        <Link href="/market-requests" className="creator-cta-btn">Create a market</Link>
      </div>
    );
  }

  return (
    <div className="creator-card">
      <h3 className="creator-card-title">Top creators</h3>
      <div className="creator-lb-table">
        <div className="creator-lb-row creator-lb-header">
          <span>#</span>
          <span>Creator</span>
          <span>Tier</span>
          <span>Volume</span>
          <span>Markets</span>
        </div>
        {entries.map((entry, i) => (
          <div key={entry.profile_id} className="creator-lb-row">
            <span className="creator-lb-rank">{i + 1}</span>
            <span className="creator-lb-name">
              {entry.display_name}
              {entry.username ? <span className="creator-lb-username">@{entry.username}</span> : null}
            </span>
            <span>
              <span className="creator-tier-dot" style={{ background: entry.badge_color }} />
              {entry.tier_label}
            </span>
            <span>{formatVolume(entry.total_volume)}</span>
            <span>{entry.markets_created}</span>
          </div>
        ))}
      </div>
    </div>
  );
};
