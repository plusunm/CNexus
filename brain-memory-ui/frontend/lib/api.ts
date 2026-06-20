import type { CognitiveOutput } from "./cognitiveTypes";
import type { MindOverview, RuntimeState } from "./runtimeTypes";

export type GtbsRawEvent = {
  event_type: string;
  transaction_id: string;
  timestamp?: string;
  ts?: string;
  payload?: Record<string, unknown>;
};
import { getApiBase, getWsBase, getApiToken } from "./cnexusConfig";

export type { RuntimeState, MindOverview } from "./runtimeTypes";
export type { CognitiveOutput } from "./cognitiveTypes";
export type {
  CognitiveInsightBlock,
  CognitiveActionBlock,
  CognitiveTextBlock,
} from "./cognitiveTypes";

/** Default true — wired full cognitive loop unless env disables it. */
export function getDefaultFullCognitiveLoop(): boolean {
  const raw = process.env.NEXT_PUBLIC_CNEXUS_FULL_COGNITIVE_LOOP;
  if (raw === "0" || raw === "false") return false;
  return true;
}

/** Health probes — ready endpoint is fast (Boot v2); short timeout avoids false offline. */
export const RUNTIME_PROBE_TIMEOUT_MS = 8_000;
/** Capability SSOT — allow cold-start without false offline. */
export const RUNTIME_CAPABILITY_TIMEOUT_MS = 15_000;
export function fastPathV3Enabled(): boolean {
  const raw = process.env.NEXT_PUBLIC_CNEXUS_FAST_PATH_V3;
  if (raw === "0" || raw === "false") return false;
  return true;
}

/** Fast-path v2 — progressive SSE ready stream. */
export const FAST_STREAM_TIMEOUT_MS = 8_000;
/** Fast-path v1 snapshot timeout. */
export const FAST_READY_TIMEOUT_MS = 2_500;

export function fastPathV2Enabled(): boolean {
  const raw = process.env.NEXT_PUBLIC_CNEXUS_FAST_PATH_V2;
  if (raw === "0" || raw === "false") return false;
  return true;
}
export const RUNTIME_DEFAULT_TIMEOUT_MS = 8_000;

export type ModelProfile = {
  id: string;
  name: string;
  provider: string;
  base_url: string;
  model: string;
  api_key_set: boolean;
  is_default: boolean;
  enabled: boolean;
};

export type RuntimeLogEntry = {
  id: string;
  timestamp: string;
  level: "info" | "debug" | "warn" | "error" | string;
  category: string;
  message: string;
  meta?: Record<string, unknown>;
};

function formatRequestError(data: unknown, status: number, statusText: string): string {
  const row = data as { detail?: unknown; message?: string };
  if (typeof row.detail === "string") return row.detail;
  if (row.detail && typeof row.detail === "object") {
    const payload = row.detail as Record<string, unknown>;
    if (status === 503 || payload.status === "warming") {
      return "Runtime 正在启动，记忆写入暂不可用，请稍候几秒后重试";
    }
    if (typeof payload.message === "string") return payload.message;
  }
  if (status === 503) return "Runtime 未就绪，请稍后再试";
  if (status === 401) return "API 鉴权失败";
  return statusText || "请求失败";
}

async function request<T>(path: string, init?: RequestInit, timeoutMs = RUNTIME_DEFAULT_TIMEOUT_MS): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const token = getApiToken();
  if (token) headers["X-CNexus-Token"] = token;

  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(`${getApiBase()}${path}`, {
      headers,
      ...init,
      signal: controller.signal,
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const detail = formatRequestError(data, res.status, res.statusText);
      if (res.status === 401) {
        throw new Error(`401 Unauthorized — ${detail || "API Key 无效或已过期"}`);
      }
      throw new Error(detail || res.statusText);
    }
    return data as T;
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new Error("请求超时 — 请确认 Runtime 已启动");
    }
    if (err instanceof TypeError) {
      throw new Error("无法连接 Runtime — 请确认应用已启动且 API 在运行");
    }
    throw err;
  } finally {
    window.clearTimeout(timer);
  }
}

export type IngestDocumentResult = {
  memory_id: string;
  status: string;
  filename: string;
  format: string;
  char_count: number;
  preview: string;
  truncated: boolean;
  keywords: string[];
  cognition?: Record<string, unknown>;
};

async function requestMultipart<T>(
  path: string,
  form: FormData,
  timeoutMs = RUNTIME_DEFAULT_TIMEOUT_MS,
): Promise<T> {
  const headers: Record<string, string> = {};
  const token = getApiToken();
  if (token) headers["X-CNexus-Token"] = token;

  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(`${getApiBase()}${path}`, {
      method: "POST",
      headers,
      body: form,
      signal: controller.signal,
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const detail = formatRequestError(data, res.status, res.statusText);
      throw new Error(detail || res.statusText);
    }
    return data as T;
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new Error("请求超时 — 请确认 Runtime 已启动");
    }
    if (err instanceof TypeError) {
      throw new Error("无法连接 Runtime — 请确认应用已启动且 API 在运行");
    }
    throw err;
  } finally {
    window.clearTimeout(timer);
  }
}

/** CNexus Product API — UI 只依赖 RUNTIME_CONTRACT.md 中的 Stable 面，不 import Python */
export const cnexusProductApi = {
  health: () => request<{ status: string; service?: string; version?: string }>("/v1/health"),
  systemReady: () =>
    request<{
      status: string;
      boot_id: string;
      boot_phase?: string;
      token_valid: boolean;
      license_valid?: boolean;
      ws: string;
      http?: string;
      memory?: string;
      uptime_ms: number;
      version: string;
      boot?: Record<string, unknown>;
      render_mode?: string;
      ui?: string;
      checks?: Record<string, unknown>;
    }>("/v1/system/ready", undefined, RUNTIME_PROBE_TIMEOUT_MS),
  systemReadyFast: () =>
    request<{
      status: string;
      ui?: string;
      render_mode?: string;
      boot_id: string;
      boot_phase?: string;
      ws: string;
      http?: string;
      checks?: Record<string, unknown>;
    }>("/v1/system/ready?mode=fast", undefined, FAST_READY_TIMEOUT_MS),
  systemReadyFull: () =>
    request<{
      status: string;
      boot_id: string;
      boot_phase?: string;
      ws: string;
      boot?: Record<string, unknown>;
      ready_gate_ok?: boolean;
      layer?: string;
      ready?: boolean;
      reason?: string | null;
      progress?: number;
      operational_ready?: boolean;
      full_ready?: boolean;
      cognitive_status?: string;
      capabilities?: Record<string, boolean>;
      ready_for_chat?: boolean;
      ready_for_upload?: boolean;
    }>("/v1/system/ready?mode=full", undefined, RUNTIME_PROBE_TIMEOUT_MS),
  systemCapability: () =>
    request<{
      status: string;
      boot_id: string;
      boot_phase?: string;
      ws?: string;
      boot?: Record<string, unknown>;
      ready?: boolean;
      reason?: string | null;
      progress?: number;
      operational_ready?: boolean;
      full_ready?: boolean;
      cognitive_status?: string;
      capabilities?: Record<string, boolean>;
      ready_for_chat?: boolean;
      ready_for_upload?: boolean;
    }>("/v1/system/capability", undefined, RUNTIME_CAPABILITY_TIMEOUT_MS),
  reportConflictLog: (body: Record<string, unknown>) =>
    request<{ ok: boolean }>("/v1/system/conflict_log", {
      method: "POST",
      body: JSON.stringify(body),
    }, 5_000),
  conflictLogTail: (tail = 200) =>
    request<{ path: string; entries: Record<string, unknown>[] }>(
      `/v1/system/conflict_log?tail=${tail}`,
      undefined,
      RUNTIME_PROBE_TIMEOUT_MS,
    ),
  systemCompute: (intent: string, payload: Record<string, unknown> = {}) =>
    request<{
      type?: string;
      status?: string;
      data?: unknown;
      l3?: number;
      cluster?: string;
      intent?: string;
      path?: string;
    }>(
      "/v1/system/compute",
      { method: "POST", body: JSON.stringify({ intent, payload }) },
      RUNTIME_PROBE_TIMEOUT_MS,
    ),
  chatFast: (input: string, options?: { timeout_s?: number; model_id?: string }) =>
    request<{
      response: string;
      status: string;
      path: string;
      mode?: string;
    }>(
      "/v1/chat/fast",
      {
        method: "POST",
        body: JSON.stringify({
          input,
          timeout_s: options?.timeout_s,
          model_id: options?.model_id,
        }),
      },
      Math.max(FAST_READY_TIMEOUT_MS, (options?.timeout_s ?? 3) * 1000 + 500),
    ),
  chatFastStreamUrl: () => `${getApiBase()}/v1/chat/fast/stream`,
  sibtProject: (input: string, options?: { source_lang?: string; intent?: string }) =>
    request<{
      status: string;
      semantic_invariant_id: string;
      semantic_layer: Record<string, unknown>;
      zh: { text: string; faithfulness: number };
      en: { text: string; faithfulness: number };
      reversibility_score: number;
      loss_report: Record<string, unknown>;
      mode: string;
    }>(
      "/v1/sibt/project",
      {
        method: "POST",
        body: JSON.stringify({ input, ...options }),
      },
      RUNTIME_PROBE_TIMEOUT_MS,
    ),
  systemReadyStreamUrl: () => `${getApiBase()}/v1/system/ready/stream`,
  mindOverview: () => request<MindOverview>("/v1/mind/overview"),
  cseLive: (window = 200) =>
    request<CognitiveOutput>(`/v1/cse/live?window=${window}`, undefined, 15_000),
  cseSynthesize: (window = 200) =>
    request<CognitiveOutput>(
      "/v1/cse/synthesize",
      { method: "POST", body: JSON.stringify({ window, mode: "full" }) },
      30_000,
    ),
  runtimeLogs: (limit = 100) =>
    request<{ logs: RuntimeLogEntry[]; count: number }>(`/logs?limit=${limit}`),
  gtbsEvents: (limit = 300) =>
    request<{ events: GtbsRawEvent[]; count: number }>(`/v1/gtbs/events?limit=${limit}`),
  executionStatus: () =>
    request<{
      active_chat_provider: string | null;
      active_embed_provider: string | null;
      providers: Record<
        string,
        {
          state: string;
          capabilities: string[];
          reachable: boolean;
          issues: string[];
          details: Record<string, unknown>;
        }
      >;
      suggested_actions: string[];
      embedding: Record<string, unknown>;
      ollama: Record<string, unknown>;
    }>("/v1/execution/status", undefined, 12_000),
  executionBootstrap: (models?: string[]) =>
    request<{ ok: boolean; detail: string; results: Record<string, unknown>[] }>(
      "/v1/execution/bootstrap",
      {
        method: "POST",
        body: JSON.stringify({ models }),
      },
      120_000,
    ),
  capture: (
    content: string,
    layer = "episodic",
    role = "user",
    importance = 0.6,
    cognize = true,
  ) =>
    request<{ memory_id: string; cognition?: Record<string, unknown> }>("/v1/memory/capture", {
      method: "POST",
      body: JSON.stringify({ role, content, layer, importance, cognize }),
    }),
  ingestDocument: (
    file: File,
    opts: {
      layer?: string;
      importance?: number;
      cognize?: boolean;
      goal?: string;
    } = {},
  ) => {
    const form = new FormData();
    form.append("file", file, file.name);
    form.append("layer", opts.layer ?? "episodic");
    form.append("importance", String(opts.importance ?? 0.7));
    if (opts.cognize !== undefined) form.append("cognize", String(opts.cognize));
    if (opts.goal?.trim()) form.append("goal", opts.goal.trim());
    return requestMultipart<IngestDocumentResult>("/v1/memory/ingest", form);
  },
  recall: (query: string) =>
    request<{ context: string }>(`/v1/memory/recall?query=${encodeURIComponent(query)}`),
  chat: (
    message: string,
    modelId?: string,
    useMemory = true,
    fullCognitiveLoop = false,
    allowProactive = true,
  ) =>
    request<{
      reply: string;
      model_name: string;
      coherence_score?: number;
      meta_reflection?: Record<string, unknown>;
      emotion_state?: Record<string, unknown>;
      active_intent?: string;
      value_alignment?: Record<string, unknown>;
      proactive?: Record<string, unknown>;
      latency_ms?: number;
      cognitive_loop?: boolean;
      human_authorized?: boolean;
    }>("/chat", {
      method: "POST",
      body: JSON.stringify({
        message,
        model_id: modelId,
        use_memory: useMemory,
        full_cognitive_loop: fullCognitiveLoop,
        allow_proactive: allowProactive,
      }),
    }, 120_000),
  chatPrepare: (
    message: string,
    modelId?: string,
    useMemory = true,
    fullCognitiveLoop = getDefaultFullCognitiveLoop(),
  ) =>
    request<{
      prepare_id: string;
      user_message: string;
      memory_context: string;
      governance_injection: string;
      system_prompt: string;
      outbound_preview: string;
      has_injection: boolean;
      chat_governance_notes: Record<string, unknown>[];
      expires_in_seconds: number;
    }>("/chat/prepare", {
      method: "POST",
      body: JSON.stringify({
        message,
        model_id: modelId,
        use_memory: useMemory,
        full_cognitive_loop: fullCognitiveLoop,
      }),
    }, 60_000),
  chatConfirm: (
    prepareId: string,
    modelId?: string,
    options?: {
      authorized?: boolean;
      sendMode?: "with_injection" | "user_only";
      fullCognitiveLoop?: boolean;
    },
  ) =>
    request<{
      reply: string;
      model_name: string;
      coherence_score?: number;
      meta_reflection?: Record<string, unknown>;
      emotion_state?: Record<string, unknown>;
      active_intent?: string;
      value_alignment?: Record<string, unknown>;
      proactive?: Record<string, unknown>;
      latency_ms?: number;
      human_authorized?: boolean;
      memory_capture?: {
        chat_governance_notes?: Array<Record<string, unknown>>;
        intercepted?: boolean;
        cognition_deferred?: boolean;
      };
    }>("/chat/confirm", {
      method: "POST",
      body: JSON.stringify({
        prepare_id: prepareId,
        authorized: options?.authorized ?? true,
        send_mode: options?.sendMode ?? "with_injection",
        model_id: modelId,
        full_cognitive_loop: options?.fullCognitiveLoop ?? getDefaultFullCognitiveLoop(),
      }),
    }, 120_000),
  chatCancel: (prepareId: string) =>
    request<{ ok: boolean; cancelled: boolean }>("/chat/cancel", {
      method: "POST",
      body: JSON.stringify({ prepare_id: prepareId, authorized: false }),
    }),
  interact: (
    message: string,
    options?: {
      userId?: string;
      sessionId?: string;
      useMemory?: boolean;
      temperature?: number;
    },
  ) =>
    request<{
      response: string;
      coherence_score?: number;
      governance_pass: boolean;
      reflection?: string;
      meta?: Record<string, unknown>;
    }>("/v1/interact", {
      method: "POST",
      body: JSON.stringify({
        user_id: options?.userId ?? "cnexus-ui",
        message,
        session_id: options?.sessionId,
        options: {
          use_memory: options?.useMemory ?? true,
          temperature: options?.temperature ?? 0.7,
        },
      }),
    }, 120_000),
  memoryStats: () =>
    request<{ total: number; by_layer: Record<string, number>; avg_importance: number }>(
      "/v1/memory/stats",
    ),
  models: () => request<{ models: ModelProfile[] }>("/models"),
  logs: (limit = 100) =>
    request<{ logs: RuntimeLogEntry[]; count: number }>(`/logs?limit=${limit}`),
  connectStateStream: (onUpdate: (state: RuntimeState) => void) => {
    const ws = new WebSocket(`${getWsBase()}/ws/state`);
    ws.onmessage = (e) => onUpdate(JSON.parse(e.data) as RuntimeState);
    ws.onerror = () => ws.close();
    return ws;
  },
  connectLogStream: (onEntry: (entry: RuntimeLogEntry) => void) => {
    const ws = new WebSocket(`${getWsBase()}/logs/ws`);
    ws.onmessage = (e) => onEntry(JSON.parse(e.data));
    ws.onerror = () => ws.close();
    return ws;
  },
};

export type StreamReadyEvent = {
  phase: "shell" | "local" | "cluster" | "final";
  status?: string;
  render_mode?: string;
  boot_phase?: string;
  ws?: string;
  l3?: boolean;
  memory?: string;
  cluster?: string;
  ready?: boolean;
  gate?: Record<string, unknown>;
};

/** Subscribe to Fast-Path v2 SSE progressive ready stream. */
export function subscribeSystemReadyStream(
  onEvent: (event: StreamReadyEvent) => void,
): () => void {
  if (typeof window === "undefined" || typeof EventSource === "undefined") {
    return () => {};
  }

  const token = getApiToken();
  const url = new URL(cnexusProductApi.systemReadyStreamUrl());
  if (token) url.searchParams.set("token", token);

  const es = new EventSource(url.toString());
  es.onmessage = (msg) => {
    try {
      onEvent(JSON.parse(msg.data) as StreamReadyEvent);
    } catch {
      /* ignore malformed frames */
    }
  };
  es.onerror = () => es.close();

  return () => es.close();
}

export type ChatFastStreamEvent = {
  token?: string;
  done?: boolean;
  status?: string;
  path?: string;
  error?: string;
};

/** Subscribe to LLM Fast Lane v2 SSE token stream (POST + fetch reader). */
export function subscribeChatFastStream(
  input: string,
  onEvent: (event: ChatFastStreamEvent) => void,
  options?: { timeout_s?: number; model_id?: string },
): () => void {
  const controller = new AbortController();
  const timeoutMs = Math.max(
    FAST_READY_TIMEOUT_MS,
    (options?.timeout_s ?? 30) * 1000 + 1000,
  );
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);

  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const token = getApiToken();
  if (token) headers["X-CNexus-Token"] = token;

  void (async () => {
    try {
      const res = await fetch(cnexusProductApi.chatFastStreamUrl(), {
        method: "POST",
        headers,
        body: JSON.stringify({
          input,
          timeout_s: options?.timeout_s,
          model_id: options?.model_id,
        }),
        signal: controller.signal,
      });
      if (!res.ok || !res.body) return;

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let pending = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        pending += decoder.decode(value, { stream: true });
        const frames = pending.split("\n\n");
        pending = frames.pop() ?? "";
        for (const frame of frames) {
          const line = frame
            .split("\n")
            .find((l) => l.startsWith("data:"));
          if (!line) continue;
          try {
            onEvent(JSON.parse(line.slice(5).trim()) as ChatFastStreamEvent);
          } catch {
            /* ignore malformed frames */
          }
        }
      }
    } catch {
      /* aborted or network error */
    } finally {
      clearTimeout(timer);
    }
  })();

  return () => {
    clearTimeout(timer);
    controller.abort();
  };
}

/** Poll authoritative Runtime READY (REST). Warming = API alive, not yet fully ready. */
export type RuntimeProbeDetail = {
  phase: "ready" | "warming" | "offline";
  bootPhase?: string | null;
  ready?: boolean;
  reason?: string | null;
  progress?: number | null;
};

export type SystemReadyPayload = {
  status?: string;
  boot_phase?: string;
  ws?: string;
  http?: string;
  ready?: boolean;
  reason?: string | null;
  progress?: number;
  runtime_pointer?: boolean;
  operational_ready?: boolean;
  full_ready?: boolean;
  ready_for_chat?: boolean;
  ready_for_upload?: boolean;
  capabilities?: Record<string, boolean>;
};

function classifyReadyPayload(
  payload: SystemReadyPayload,
  options?: { skipWs?: boolean },
): RuntimeProbeDetail {
  const bootPhase = payload.boot_phase ?? null;
  const bootMeta = {
    bootPhase,
    ready: payload.ready ?? payload.full_ready,
    reason: payload.reason ?? null,
    progress: payload.progress ?? null,
  };
  if (payload.operational_ready || payload.ready_for_chat || payload.status === "operational") {
    return {
      phase: "ready",
      ...bootMeta,
      ready: Boolean(payload.operational_ready ?? payload.ready_for_chat),
    };
  }
  if (payload.status === "ready_fast" || payload.status === "streaming") {
    return { phase: "warming", ...bootMeta };
  }
  if (payload.status === "ready" && payload.ws === "alive") {
    if (options?.skipWs) return { phase: "ready", ...bootMeta, ready: true, progress: 100, reason: null };
    return { phase: "ready", ...bootMeta, ready: true, progress: 100, reason: null };
  }
  if (payload.status === "ready" && payload.runtime_pointer === false) {
    return { phase: "warming", ...bootMeta };
  }
  if (payload.status === "warming") {
    return { phase: "warming", ...bootMeta };
  }
  if (bootPhase && bootPhase !== "boot_0_api" && bootPhase !== "boot_4_ready") {
    return { phase: "warming", ...bootMeta };
  }
  if (payload.http === "listening" && payload.ws === "starting") {
    return { phase: "warming", ...bootMeta };
  }
  return { phase: "offline", ...bootMeta };
}

export async function probeRuntimeReadyDetail(options?: {
  wsTimeoutMs?: number;
  skipWs?: boolean;
  fast?: boolean;
}): Promise<RuntimeProbeDetail> {
  try {
    if (options?.fast) {
      const payload = await cnexusProductApi.systemReadyFast();
      return classifyReadyPayload(payload, options);
    }
    const payload = await cnexusProductApi.systemCapability();
    const classified = classifyReadyPayload(payload, options);
    if (classified.phase === "ready" && payload.ws === "alive" && !options?.skipWs) {
      const wsOk = await probeWsStateHandshake(options?.wsTimeoutMs ?? 5000);
      return wsOk ? classified : { phase: "warming", bootPhase: classified.bootPhase };
    }
    return classified;
  } catch {
    try {
      const health = await cnexusProductApi.health();
      if (health.status === "ok") return { phase: "warming", bootPhase: null };
    } catch {
      /* API down */
    }
    return { phase: "offline", bootPhase: null };
  }
}

export async function probeRuntimeReady(options?: {
  wsTimeoutMs?: number;
  skipWs?: boolean;
  fast?: boolean;
}): Promise<"ready" | "warming" | "offline"> {
  const detail = await probeRuntimeReadyDetail(options);
  return detail.phase;
}

/** True when runtime is operational (chat/basic API). Set requireFull for upload gate. */
export async function isRuntimeReady(options?: {
  wsTimeoutMs?: number;
  skipWs?: boolean;
  requireFull?: boolean;
}): Promise<boolean> {
  try {
    const payload = await cnexusProductApi.systemCapability();
    const operational = Boolean(payload.operational_ready ?? payload.ready_for_chat);
    const full = Boolean(payload.full_ready ?? payload.ready);
    if (options?.requireFull) {
      if (!full) return false;
    } else if (!operational) {
      return false;
    }
    if (options?.skipWs) return true;
    return probeWsStateHandshake(options?.wsTimeoutMs ?? 5000);
  } catch {
    try {
      const health = await cnexusProductApi.health();
      if (health.status === "ok") return false;
    } catch {
      /* API down */
    }
    return false;
  }
}

export function probeWsStateHandshake(timeoutMs = 2000): Promise<boolean> {
  return new Promise((resolve) => {
    if (typeof WebSocket === "undefined") {
      resolve(false);
      return;
    }
    let settled = false;
    const finish = (ok: boolean) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      try {
        ws.close();
      } catch {
        /* ignore */
      }
      resolve(ok);
    };
    const ws = new WebSocket(`${getWsBase()}/ws/state`);
    const timer = setTimeout(() => finish(false), timeoutMs);
    ws.onmessage = () => finish(true);
    ws.onerror = () => finish(false);
  });
}

export const brainApi = {
  ...cnexusProductApi,
  state: () => request<RuntimeState>("/governance/state"),
  governance: () => request<Record<string, unknown>>("/governance/cycle", { method: "POST" }),
  clearLogs: () => request<{ ok: boolean }>("/logs", { method: "DELETE" }),
  createModel: (body: Record<string, unknown>) =>
    request<{ model: ModelProfile }>("/models", { method: "POST", body: JSON.stringify(body) }),
  updateModel: (id: string, body: Record<string, unknown>) =>
    request<{ model: ModelProfile }>(`/models/${id}`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),
  deleteModel: (id: string) => request<{ ok: boolean }>(`/models/${id}`, { method: "DELETE" }),
  testModel: (id: string) =>
    request<{ success: boolean; detail: string }>(`/models/${id}/test`, { method: "POST" }),
  mindOverview: () => cnexusProductApi.mindOverview(),
  embeddingStatus: () =>
    request<{
      configured_mode: string;
      active_mode: "ollama" | "hash";
      ollama_reachable: boolean;
      model: string;
      host: string;
      used_on: string[];
      not_used_on: string[];
    }>("/v1/memory/embedding-status"),
  ollamaStatus: () =>
    request<{
      installed: boolean;
      binary_found: boolean;
      running: boolean;
      host: string;
      download_url: string;
      binary_path?: string | null;
    }>("/v1/ollama/status", undefined, 4_000),
  ollamaStart: () =>
    request<{
      ok: boolean;
      detail: string;
      running: boolean;
      download_url?: string | null;
    }>("/v1/ollama/start", { method: "POST" }, 30_000),
  ollamaStop: () =>
    request<{
      ok: boolean;
      detail: string;
      running: boolean;
    }>("/v1/ollama/stop", { method: "POST" }, 15_000),
};

// ==================== WS Interact 重连管理器 ====================

export interface InteractMessage {
  type: string;
  content?: string;
  [key: string]: unknown;
}

export interface InteractWSError {
  type: "error";
  error: string;
  message?: string;
  retry?: boolean;
  retry_after?: number;
  [key: string]: unknown;
}

export type InteractWSResponse = InteractWSError | Record<string, unknown>;

class WSInteractManager {
  private ws: WebSocket | null = null;
  private retries = 0;
  private maxRetries = 6;
  private messageQueue: Array<{
    msg: InteractMessage;
    resolve: (res: InteractWSResponse) => void;
    reject: (err: unknown) => void;
  }> = [];
  private isConnecting = false;
  private pendingPing: ReturnType<typeof setInterval> | null = null;
  private onMessageCallback: ((data: InteractWSResponse) => void) | null = null;
  private onStatusChange: ((status: "connected" | "disconnected" | "reconnecting") => void) | null = null;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;

  connect(
    onMessage: (data: InteractWSResponse) => void,
    onStatus?: (status: "connected" | "disconnected" | "reconnecting") => void,
  ): void {
    this.onMessageCallback = onMessage;
    this.onStatusChange = onStatus ?? null;
    this._connect();
  }

  private _connect(): void {
    if (this.isConnecting || this.ws?.readyState === WebSocket.OPEN) return;
    this.isConnecting = true;
    this.onStatusChange?.("reconnecting");

    this.ws = new WebSocket(`${getWsBase()}/ws/interact`);

    this.ws.onopen = () => {
      console.log("[WS Interact] Connected");
      this.retries = 0;
      this.isConnecting = false;
      this.onStatusChange?.("connected");
      this._flushQueue();
      this._startHeartbeat();
    };

    this.ws.onmessage = (event: MessageEvent) => {
      try {
        const data: InteractWSResponse = JSON.parse(event.data as string);
        this.onMessageCallback?.(data);
        if (data && "error" in data && data.error && (data as InteractWSError).retry) {
          console.warn("[WS Interact] Server asked to retry:", (data as InteractWSError).message);
        }
      } catch (e) {
        console.error("[WS Interact] Parse error", e);
      }
    };

    this.ws.onclose = () => {
      console.warn("[WS Interact] Closed");
      this.isConnecting = false;
      this._stopHeartbeat();
      this.onStatusChange?.("disconnected");

      if (this.retries < this.maxRetries) {
        this.retries++;
        const delay = Math.min(1000 * Math.pow(1.5, this.retries), 30000);
        console.log(`[WS Interact] Reconnecting in ${delay}ms (${this.retries}/${this.maxRetries})`);
        this.reconnectTimer = setTimeout(() => this._connect(), delay);
      } else {
        console.error("[WS Interact] Max retries reached");
      }
    };

    this.ws.onerror = () => {
      console.error("[WS Interact] Error");
      this.ws?.close();
    };
  }

  private _startHeartbeat(): void {
    this._stopHeartbeat();
    this.pendingPing = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: "ping" }));
      }
    }, 25000);
  }

  private _stopHeartbeat(): void {
    if (this.pendingPing) {
      clearInterval(this.pendingPing);
      this.pendingPing = null;
    }
  }

  private _flushQueue(): void {
    while (this.messageQueue.length > 0) {
      const item = this.messageQueue.shift()!;
      this._sendNow(item.msg).then(item.resolve).catch(item.reject);
    }
  }

  private _sendNow(msg: InteractMessage): Promise<InteractWSResponse> {
    return new Promise((resolve) => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify(msg));
        resolve({ type: "sent" });
      } else {
        resolve({ type: "buffer" });
      }
    });
  }

  send(msg: InteractMessage): Promise<InteractWSResponse> {
    return new Promise((resolve, reject) => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify(msg));
        resolve({ type: "sent" });
      } else {
        this.messageQueue.push({ msg, resolve, reject });
        if (!this.isConnecting) this._connect();
      }
    });
  }

  close(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this._stopHeartbeat();
    this.ws?.close();
    this.messageQueue = [];
    this.retries = this.maxRetries;
  }

  getStatus(): "connected" | "disconnected" | "connecting" {
    if (this.ws?.readyState === WebSocket.OPEN) return "connected";
    if (this.isConnecting) return "connecting";
    return "disconnected";
  }
}

export const wsInteractManager = new WSInteractManager();

// ==================== HTTP interact 自动重试 ====================

export interface InteractPayload {
  message: string;
  userId?: string;
  sessionId?: string;
  useMemory?: boolean;
  temperature?: number;
}

export interface InteractResult {
  response: string;
  coherence_score?: number;
  governance_pass: boolean;
  reflection?: string;
  meta?: Record<string, unknown>;
  error?: string;
  retry?: boolean;
  retry_after?: number;
}

export async function interactWithRetry(
  payload: InteractPayload,
  maxRetries = 3,
): Promise<InteractResult> {
  let lastError: unknown;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      const result = await cnexusProductApi.interact(
        payload.message,
        {
          userId: payload.userId,
          sessionId: payload.sessionId,
          useMemory: payload.useMemory,
          temperature: payload.temperature,
        },
      );

      const r = result as InteractResult;
      if (r.retry) {
        const delay = (r.retry_after ?? 5) * 1000;
        console.warn(`[Interact] Server retry requested, waiting ${delay}ms`);
        await new Promise((r) => { setTimeout(r, delay); });
        continue;
      }

      return result as InteractResult;
    } catch (err: unknown) {
      lastError = err;
      const errMsg = err instanceof Error ? err.message : String(err);
      console.warn(`[Interact] Attempt ${attempt + 1}/${maxRetries + 1} failed: ${errMsg}`);

      if (attempt === maxRetries) break;

      const delay = Math.min(1000 * Math.pow(1.5, attempt), 10000);
      await new Promise((r) => { setTimeout(r, delay); });
    }
  }

  throw lastError;
}


export { getApiBase as API_BASE, getWsBase as WS_BASE };
