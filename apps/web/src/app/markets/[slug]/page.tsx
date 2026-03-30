import { AppScreenShell } from "@/components/app/app-screen-shell";
import { MarketDetailWorkspace } from "@/components/app/market-detail-workspace";

export default async function MarketDetailPage({
  params
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;

  return (
    <AppScreenShell
      eyebrow="Market Detail"
      title="Inspect the published market and its default outcomes."
      description="This is the first canonical market surface after a request is approved and converted."
    >
      <MarketDetailWorkspace slug={slug} />
    </AppScreenShell>
  );
}
