import { AdminReviewWorkspace } from "@/components/app/admin-review-workspace";
import { AppScreenShell } from "@/components/app/app-screen-shell";
import { ProtectedSessionCard } from "@/components/app/protected-session-card";

export default function AdminReviewPage() {
  return (
    <AppScreenShell
      eyebrow="Admin Review"
      title="Approve or reject pending posts and market requests from one queue."
      description="This is the moderation surface for social posts and market intake before they become visible or operational."
    >
      <AdminReviewWorkspace />
      <ProtectedSessionCard title="Authenticated moderator" />
    </AppScreenShell>
  );
}
