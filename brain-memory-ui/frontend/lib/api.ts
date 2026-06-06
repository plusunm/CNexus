const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";
const WS_BASE = process.env.NEXT_PUBLIC_WS_BASE ?? "ws://localhost:8000";

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

export type RuntimeState = {
  stability_metrics: Record<string, number>;
  narrative: { summary: string; coherence: number; version: number };
  beliefs: Record<string, { content: string; confidence: number }>;
  working_memory_count: number;
  timestamp: string;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail ?? res.statusText);
  return data as T;
}

export const brainApi = {
  health: () => request<{ status: string }>("/health"),

  capture: (content: string, layer = "episodic", role = "user", importance = 0.6) =>
    request<{ memory_id: string }>("/memory/capture", {
      method: "POST",
      body: JSON.stringify({ role, content, layer, importance }),
    }),

  recall: (query: string) =>
    request<{ context: string }>(`/memory/recall?query=${encodeURIComponent(query)}`),

  chat: (message: string, modelId?: string, useMemory = true) =>
    request<{ reply: string; model_name: string }>("/chat", {
      method: "POST",
      body: JSON.stringify({ message, model_id: modelId, use_memory: useMemory }),
    }),

  models: () => request<{ models: ModelProfile[] }>("/models"),

  createModel: (body: Record<string, unknown>) =>
    request<{ model: ModelProfile }>("/models", { method: "POST", body: JSON.stringify(body) }),

  deleteModel: (id: string) =>
    request<{ ok: boolean }>(`/models/${id}`, { method: "DELETE" }),

  testModel: (id: string) =>
    request<{ success: boolean; detail: string }>(`/models/${id}/test`, { method: "POST" }),

  state: () => request<RuntimeState>("/governance/state"),

  governance: () => request<Record<string, unknown>>("/governance/cycle", { method: "POST" }),

  logs: (limit = 100) =>
    request<{ logs: RuntimeLogEntry[]; count: number }>(`/logs?limit=${limit}`),

  clearLogs: () => request<{ ok: boolean }>("/logs", { method: "DELETE" }),

  connectLogStream: (onEntry: (entry: RuntimeLogEntry) => void) => {
    const ws = new WebSocket(`${WS_BASE}/logs/ws`);
    ws.onmessage = (e) => onEntry(JSON.parse(e.data));
    ws.onerror = () => ws.close();
    return ws;
  },

  connectStateStream: (onUpdate: (state: RuntimeState) => void) => {
    const ws = new WebSocket(`${WS_BASE}/ws/state`);
    ws.onmessage = (e) => onUpdate(JSON.parse(e.data));
    ws.onerror = () => ws.close();
    return ws;
  },
};

export { API_BASE, WS_BASE };
