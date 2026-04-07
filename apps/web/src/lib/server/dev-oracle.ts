import { NextRequest, NextResponse } from "next/server";
import type { BackendUser } from "@/lib/api/types";

const getApiBaseUrl = () => process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

const getOracleSecret = () =>
  process.env.ORACLE_CALLBACK_SECRET ?? process.env.SATTA_ORACLE_CALLBACK_SECRET ?? "dev-oracle-secret";

const parseResponseBody = async (response: Response): Promise<unknown> => {
  const rawBody = await response.text();
  if (!rawBody) {
    return null;
  }
  try {
    return JSON.parse(rawBody);
  } catch {
    return rawBody;
  }
};

const getErrorDetail = (body: unknown): string | null => {
  if (typeof body === "string") {
    return body;
  }
  if (!body || typeof body !== "object" || !("detail" in body)) {
    return null;
  }
  const detail = body.detail;
  return typeof detail === "string" ? detail : null;
};

export const proxyDevOracleRequest = async (request: NextRequest, targetPath: string) => {
  if (process.env.NODE_ENV === "production") {
    return NextResponse.json({ detail: "Not found." }, { status: 404 });
  }

  const authorization = request.headers.get("authorization");
  if (!authorization) {
    return NextResponse.json({ detail: "Authentication is required." }, { status: 401 });
  }

  const apiBaseUrl = getApiBaseUrl();
  const actorResponse = await fetch(new URL("/api/v1/auth/me", apiBaseUrl), {
    headers: {
      Authorization: authorization
    },
    cache: "no-store"
  });
  const actorBody = await parseResponseBody(actorResponse);
  if (!actorResponse.ok) {
    return NextResponse.json(
      { detail: getErrorDetail(actorBody) ?? "Failed to verify the current actor." },
      { status: actorResponse.status }
    );
  }

  const actor = actorBody as BackendUser;
  if (!actor.is_admin) {
    return NextResponse.json({ detail: "Admin privileges are required for dev oracle controls." }, { status: 403 });
  }

  const rawPayload = await request.text();
  const proxyResponse = await fetch(new URL(targetPath, apiBaseUrl), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Satta-Oracle-Secret": getOracleSecret()
    },
    body: rawPayload || "{}",
    cache: "no-store"
  });
  const proxyBody = await parseResponseBody(proxyResponse);

  return NextResponse.json(proxyBody ?? {}, {
    status: proxyResponse.status
  });
};
