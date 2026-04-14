import { AppScreenShell } from "@/components/app/app-screen-shell";
import { LeaderboardWorkspace } from "@/components/app/leaderboard-workspace";

export const metadata = {
  title: "Leaderboard — Satta",
  description: "See the top traders ranked by realized PnL.",
};

export default function LeaderboardPage() {
  return (
    <AppScreenShell eyebrow="Leaderboard" title="Top traders by realized PnL">
      <LeaderboardWorkspace />
    </AppScreenShell>
  );
}
