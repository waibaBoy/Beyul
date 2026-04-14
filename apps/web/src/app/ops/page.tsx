import { AppScreenShell } from "@/components/app/app-screen-shell";
import { OpsDashboardWorkspace } from "@/components/app/ops-dashboard-workspace";

export const metadata = {
  title: "Operations — Satta",
  description: "System health, settlement queue, moderation SLA, and jurisdiction status.",
};

export default function OpsPage() {
  return (
    <AppScreenShell
      eyebrow="Operations"
      title="System health and operational status"
    >
      <OpsDashboardWorkspace />
    </AppScreenShell>
  );
}
