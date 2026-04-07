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
      title="Follow the feed, members, and moderation flow for this community."
      description="Stay inside one community while managing posts, approvals, and member context around its markets."
    >
      <CommunityDetailWorkspace slug={slug} />
      <ProtectedSessionCard />
    </AppScreenShell>
  );
}
