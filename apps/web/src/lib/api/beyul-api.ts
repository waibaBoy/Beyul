import { publicEnv } from "@/lib/env";

export class SattaApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "SattaApiError";
    this.status = status;
  }
}

export const BeyulApiError = SattaApiError;

type ApiOptions = RequestInit & {
  accessToken?: string | null;
  json?: unknown;
};

export const sattaApiFetch = async <T>(path: string, options: ApiOptions = {}): Promise<T> => {
  const { accessToken, json, headers, ...init } = options;

  const response = await fetch(new URL(path, publicEnv.apiBaseUrl).toString(), {
    ...init,
    headers: {
      ...(json ? { "Content-Type": "application/json" } : {}),
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      ...headers
    },
    body: json !== undefined ? JSON.stringify(json) : init.body,
    cache: "no-store"
  });

  const rawBody = await response.text();
  const body = rawBody ? tryParseJson(rawBody) : null;

  if (!response.ok) {
    const message = getErrorMessage(body) || response.statusText || "API request failed";
    throw new SattaApiError(message, response.status);
  }

  return body as T;
};

export const beyulApiFetch = sattaApiFetch;

const tryParseJson = (rawBody: string): unknown => {
  try {
    return JSON.parse(rawBody);
  } catch {
    return rawBody;
  }
};

const getErrorMessage = (body: unknown): string | null => {
  if (!body || typeof body !== "object" || !("detail" in body)) {
    return typeof body === "string" ? body : null;
  }

  const detail = body.detail;
  return typeof detail === "string" ? detail : null;
};
