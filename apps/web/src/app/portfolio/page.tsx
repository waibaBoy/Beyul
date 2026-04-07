import { AppScreenShell } from "@/components/app/app-screen-shell";
import { PortfolioWorkspace } from "@/components/app/portfolio-workspace";

export default function PortfolioPage() {
  return (
    <AppScreenShell
      eyebrow="Portfolio"
      title="Balances, positions, and trade history"
    >
      <PortfolioWorkspace />
    </AppScreenShell>
  );
}
