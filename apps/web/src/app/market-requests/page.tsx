import { AppScreenShell } from "@/components/app/app-screen-shell";
import { MarketRequestsWorkspace } from "@/components/app/market-requests-workspace";
import { ProtectedSessionCard } from "@/components/app/protected-session-card";

export default function MarketRequestsPage() {
  return (
    <AppScreenShell
      eyebrow="Market Requests"
      title="Submit market requests with the same authenticated bearer flow."
      description="This screen uses the live market request endpoints so you can test intake, answers, and review state before trading and settlement."
    >
      <MarketRequestsWorkspace />
      <ProtectedSessionCard title="Authenticated actor" />
    </AppScreenShell>
  );
}
