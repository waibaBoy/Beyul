"use client";

import { useEffect, useState } from "react";
import { beyulApiFetch } from "@/lib/api/beyul-api";

type LeaderboardEntry = {
  rank: number;
  username: string;
  display_name: string | null;
  total_pnl: string;
  position_count: number;
};

const fmt = (v: string) => {
  const n = Number(v);
  if (!Number.isFinite(n)) return "—";
  const sign = n >= 0 ? "+" : "";
  return `${sign}${n.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
};

const rankMedal = (rank: number) => {
  if (rank === 1) return "🥇";
  if (rank === 2) return "🥈";
  if (rank === 3) return "🥉";
  return `#${rank}`;
};

export const LeaderboardWorkspace = () => {
  const [entries, setEntries] = useState<LeaderboardEntry[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    beyulApiFetch<{ entries: LeaderboardEntry[] }>("/api/v1/social/leaderboard")
      .then((res) => setEntries(res.entries))
      .catch(() => {})
      .finally(() => setIsLoading(false));
  }, []);

  if (isLoading) return <div className="lb-loading">Loading leaderboard…</div>;

  return (
    <div className="lb-shell">
      {entries.length === 0 ? (
        <p className="lb-empty">No trading activity yet. Be the first!</p>
      ) : (
        <table className="lb-table">
          <thead>
            <tr>
              <th className="lb-th-rank">Rank</th>
              <th>Trader</th>
              <th className="lb-th-num">PnL</th>
              <th className="lb-th-num">Positions</th>
            </tr>
          </thead>
          <tbody>
            {entries.map((e) => {
              const pnlN = Number(e.total_pnl);
              const pnlClass = pnlN > 0 ? "lb-pnl-pos" : pnlN < 0 ? "lb-pnl-neg" : "";
              return (
                <tr key={e.username} className="lb-row">
                  <td className="lb-rank">{rankMedal(e.rank)}</td>
                  <td>
                    <a href={`/profile/${e.username}`} className="lb-user-link">
                      <strong>{e.display_name || e.username}</strong>
                      <span className="lb-username">@{e.username}</span>
                    </a>
                  </td>
                  <td className={`lb-td-num ${pnlClass}`}>{fmt(e.total_pnl)}</td>
                  <td className="lb-td-num">{e.position_count}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
};
