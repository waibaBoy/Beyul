import { AppScreenShell } from "@/components/app/app-screen-shell";
import { MarketsWorkspace } from "@/components/app/markets-workspace";

export default function MarketsPage() {
  return (
    <AppScreenShell
      eyebrow="Markets"
      title="Inspect the canonical markets created from approved requests."
      description="This surface shows the first real publish step from intake into a canonical market record with outcomes."
    >
      <MarketsWorkspace />
    </AppScreenShell>
  );
}
