import { AppScreenShell } from "@/components/app/app-screen-shell";
import { CreatorDashboardWorkspace } from "@/components/app/creator-dashboard-workspace";

export const metadata = {
  title: "Creator Dashboard — Satta",
  description: "Track your market-making performance, reward tier, and see top creators.",
};

export default function CreatorsPage() {
  return (
    <AppScreenShell
      eyebrow="Creators"
      title="Your market-making stats, reward tiers, and leaderboard"
    >
      <CreatorDashboardWorkspace />
    </AppScreenShell>
  );
}
