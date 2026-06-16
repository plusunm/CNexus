import type { SpineQueryResponse } from "./spineQueryTypes";
import { getApiBase, getApiToken } from "./cnexusConfig";

export async function spineQuery(
  query: string,
  limit = 200,
  opts?: { engine?: "v1" | "v2" | "v3" },
): Promise<SpineQueryResponse> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const token = getApiToken();
  if (token) headers["X-CNexus-Token"] = token;

  const res = await fetch(`${getApiBase()}/v1/spine/query`, {
    method: "POST",
    headers,
    body: JSON.stringify({ query, limit, engine: opts?.engine ?? "v3" }),
  });

  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = typeof data.detail === "string" ? data.detail : res.statusText;
    throw new Error(detail || "spine query failed");
  }
  return data as SpineQueryResponse;
}
