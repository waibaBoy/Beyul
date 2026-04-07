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
      title="Complete the request details before sending this market for review."
      description="Answer the intake questions, review the request state, and move it into moderation when it is ready."
    >
      <MarketRequestDetailWorkspace requestId={requestId} />
      <ProtectedSessionCard title="Authenticated requester" />
    </AppScreenShell>
  );
}
