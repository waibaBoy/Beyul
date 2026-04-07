import { AppScreenShell } from "@/components/app/app-screen-shell";
import { MarketDetailWorkspace } from "@/components/app/market-detail-workspace";

export default async function MarketDetailPage({
  params
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;

  return (
    <AppScreenShell>
      <MarketDetailWorkspace slug={slug} />
    </AppScreenShell>
  );
}
