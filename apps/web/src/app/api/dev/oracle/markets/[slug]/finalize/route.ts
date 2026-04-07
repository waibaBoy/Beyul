import { NextRequest } from "next/server";
import { proxyDevOracleRequest } from "@/lib/server/dev-oracle";

type RouteContext = {
  params: Promise<{
    slug: string;
  }>;
};

export const POST = async (request: NextRequest, context: RouteContext) => {
  const { slug } = await context.params;
  return proxyDevOracleRequest(request, `/api/v1/markets/${slug}/oracle/finalize`);
};
