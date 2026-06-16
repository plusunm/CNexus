/**
 * Kernel projection API — UI reads ExecutionRecord (single truth source).
 */
import { getApiBase, getApiToken } from "./cnexusConfig";

export type ExecutionRecord = {
  version: string;
  trace_id: string;
  intent_type: string;
  result: unknown;
  identity?: string | null;
  graph_invariant?: string | null;
  graph?: Record<string, unknown> | null;
  nodes: Record<string, unknown>[];
  edges: Record<string, unknown>[];
  state_projection: Record<string, unknown>;
  causal_projection: Record<string, unknown>;
  explain_projection: Record<string, unknown>;
  equivalence?: Record<string, unknown> | null;
  replay_signature?: string | null;
  audit_log: Record<string, unknown>;
  audit: Record<string, unknown>;
  events: Record<string, unknown>[];
  derivation: Record<string, unknown>;
  elapsed_ms: number;
};

export type LearnExplanationV2 = {
  version: string;
  trace_id: string;
  execution_tier: string;
  mode: "fast" | "standard" | "deep" | string;
  summary: string;
  steps: string[];
  beginner_view: string;
  intermediate_view: string;
  expert_view: string;
  execution_story: string;
  memory_view: string[];
  reasoning_trace: string[];
  why_this_result: string;
  why_it_feels_fast_or_slow: string;
  mental_model: string;
  user_intent_summary: string;
};

export type LearnDisplayMode = "learn" | "hybrid" | "engineer";

export async function fetchExecutionRecord(traceId: string): Promise<ExecutionRecord> {
  const res = await fetch(`${getApiBase()}/v1/kernel/record/${encodeURIComponent(traceId)}`, {
    headers: getApiToken() ? { "X-CNexus-Token": getApiToken()! } : {},
  });
  if (!res.ok) {
    throw new Error(`execution record fetch failed: ${res.status}`);
  }
  return res.json() as Promise<ExecutionRecord>;
}

export async function fetchKernelLearn(traceId: string): Promise<LearnExplanationV2> {
  const res = await fetch(
    `${getApiBase()}/v1/kernel/record/${encodeURIComponent(traceId)}/learn`,
    {
      headers: getApiToken() ? { "X-CNexus-Token": getApiToken()! } : {},
    },
  );
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const detail = typeof body.detail === "string" ? body.detail : "";
    if (res.status === 404) {
      throw new Error(
        detail ||
          `未找到 trace_id「${traceId}」。请使用 Query 对话返回的 trace_id，或从 Spine 事件复制真实追踪 ID。`,
      );
    }
    throw new Error(detail || `learn projection fetch failed: ${res.status}`);
  }
  return res.json() as Promise<LearnExplanationV2>;
}

export async function fetchRecentTraceIds(limit = 20): Promise<string[]> {
  const res = await fetch(`${getApiBase()}/v1/kernel/records/recent?limit=${limit}`, {
    headers: getApiToken() ? { "X-CNexus-Token": getApiToken()! } : {},
  });
  if (!res.ok) return [];
  const data = (await res.json()) as { trace_ids?: string[] };
  return data.trace_ids ?? [];
}

export async function fetchKernelCapabilities(): Promise<Record<string, unknown>> {
  const res = await fetch(`${getApiBase()}/v1/kernel/capabilities`, {
    headers: getApiToken() ? { "X-CNexus-Token": getApiToken()! } : {},
  });
  if (!res.ok) {
    throw new Error(`kernel capabilities fetch failed: ${res.status}`);
  }
  return res.json() as Promise<Record<string, unknown>>;
}
