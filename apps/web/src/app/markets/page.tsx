import { AppScreenShell } from "@/components/app/app-screen-shell";
import { MarketsWorkspace } from "@/components/app/markets-workspace";

export default function MarketsPage() {
  return (
    <AppScreenShell
      eyebrow="Markets"
      title="Browse live markets through community filters and exchange-style rows."
      description="Use the community rail to narrow the board, open a featured market fast, and drill into active books below."
    >
      <MarketsWorkspace />
    </AppScreenShell>
  );
}
