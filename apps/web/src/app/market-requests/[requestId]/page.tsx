import { AppScreenShell } from "@/components/app/app-screen-shell";
import { MarketRequestDetailWorkspace } from "@/components/app/market-request-detail-workspace";
import { ProtectedSessionCard } from "@/components/app/protected-session-card";

export default async function MarketRequestDetailPage({
  params
}: {
  params: Promise<{ requestId: string }>;
}) {
  const { requestId } = await params;

  return (
    <AppScreenShell
      eyebrow="Market Request Detail"
      title="Fill intake answers and move requests into the moderation queue."
      description="This route exposes the answer set, draft state, and submission transition for a single market request."
    >
      <MarketRequestDetailWorkspace requestId={requestId} />
      <ProtectedSessionCard title="Authenticated requester" />
    </AppScreenShell>
  );
}
