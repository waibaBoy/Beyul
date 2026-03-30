import { AppScreenShell } from "@/components/app/app-screen-shell";
import { CommunityDetailWorkspace } from "@/components/app/community-detail-workspace";
import { ProtectedSessionCard } from "@/components/app/protected-session-card";

export default async function CommunityDetailPage({
  params
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;

  return (
    <AppScreenShell
      eyebrow="Community Detail"
      title="Run the social feed and post approval flow for one community."
      description="This route combines community metadata, membership, and the moderated post feed against the live FastAPI backend."
    >
      <CommunityDetailWorkspace slug={slug} />
      <ProtectedSessionCard />
    </AppScreenShell>
  );
}
