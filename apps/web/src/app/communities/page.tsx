import { AppScreenShell } from "@/components/app/app-screen-shell";
import { CommunitiesWorkspace } from "@/components/app/communities-workspace";
import { ProtectedSessionCard } from "@/components/app/protected-session-card";

export default function CommunitiesPage() {
  return (
    <AppScreenShell
      eyebrow="Communities"
      title="Create and inspect communities against the live Satta backend."
      description="Communities now act as the social container for posts, moderation, and market intake using the same FastAPI + Supabase stack."
    >
      <CommunitiesWorkspace />
      <ProtectedSessionCard />
    </AppScreenShell>
  );
}
