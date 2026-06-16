import { getApiBase, getApiToken } from "@/lib/cnexusConfig";
import type { TokenField, TokenObservatoryResponse } from "./types";

function authHeaders(): Record<string, string> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const token = getApiToken();
  if (token) headers["X-CNexus-Token"] = token;
  return headers;
}

export async function fetchTokenField(traceId: string): Promise<TokenField> {
  const res = await fetch(`${getApiBase()}/v1/spine/token/trace/${encodeURIComponent(traceId)}`, {
    headers: authHeaders(),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = typeof data.detail === "string" ? data.detail : res.statusText;
    throw new Error(detail || "token field load failed");
  }
  return data as TokenField;
}

export async function fetchTokenObservatory(limit = 100): Promise<TokenObservatoryResponse> {
  const res = await fetch(`${getApiBase()}/v1/spine/token/observatory?limit=${limit}`, {
    headers: authHeaders(),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = typeof data.detail === "string" ? data.detail : res.statusText;
    throw new Error(detail || "token observatory load failed");
  }
  return data as TokenObservatoryResponse;
}

export async function fetchRuntimeTokenTraces(): Promise<TokenObservatoryResponse> {
  const res = await fetch(`${getApiBase()}/v1/runtime/introspect`, {
    headers: authHeaders(),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = typeof data.detail === "string" ? data.detail : res.statusText;
    throw new Error(detail || "runtime introspect failed");
  }
  const traces = Array.isArray(data.token_traces) ? data.token_traces : [];
  return { token_traces: traces, count: traces.length };
}
