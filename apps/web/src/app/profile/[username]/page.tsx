import { AppScreenShell } from "@/components/app/app-screen-shell";
import { TradingProfileWorkspace } from "@/components/app/trading-profile-workspace";

export const metadata = {
  title: "Trader Profile — Satta",
  description: "View a trader's public profile, stats, and positions.",
};

export default async function ProfilePage({ params }: { params: Promise<{ username: string }> }) {
  const { username } = await params;
  return (
    <AppScreenShell eyebrow="Profile" title={`@${username}`}>
      <TradingProfileWorkspace username={username} />
    </AppScreenShell>
  );
}
