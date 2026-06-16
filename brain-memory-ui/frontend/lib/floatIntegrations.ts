/** Local integration settings for float menu (persisted in localStorage). */

export type DingTalkConfig = {
  enabled: boolean;
  webhook: string;
  secret: string;
  notifyOnCapture: boolean;
  notifyOnConflict: boolean;
};

export type LlmQuickConfig = {
  provider: string;
  baseUrl: string;
  model: string;
  apiKey: string;
  label: string;
};

/** DeepSeek official OpenAI-compatible endpoint (SDK adds /v1). */
export const DEEPSEEK_OPENAI_BASE_URL = "https://api.deepseek.com";

export const DEEPSEEK_MODEL_OPTIONS = [
  { value: "deepseek-v4-flash", label: "deepseek-v4-flash（推荐）" },
  { value: "deepseek-v4-pro", label: "deepseek-v4-pro" },
  { value: "deepseek-chat", label: "deepseek-chat（旧，将弃用）" },
  { value: "deepseek-reasoner", label: "deepseek-reasoner（旧，将弃用）" },
] as const;

const DINGTALK_KEY = "cnexus-dingtalk-config";
const LLM_KEY = "cnexus-llm-quick-config";

const DEFAULT_DINGTALK: DingTalkConfig = {
  enabled: false,
  webhook: "",
  secret: "",
  notifyOnCapture: true,
  notifyOnConflict: true,
};

const DEFAULT_LLM: LlmQuickConfig = {
  provider: "deepseek",
  baseUrl: DEEPSEEK_OPENAI_BASE_URL,
  model: "deepseek-v4-flash",
  apiKey: "",
  label: "DeepSeek V4 Flash",
};

const LEGACY_DEEPSEEK_MODELS: Record<string, string> = {
  "deepseek-chat": "deepseek-v4-flash",
  "deepseek-reasoner": "deepseek-v4-pro",
};

function readJson<T>(key: string, fallback: T): T {
  if (typeof window === "undefined") return fallback;
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return fallback;
    return { ...fallback, ...JSON.parse(raw) } as T;
  } catch {
    return fallback;
  }
}

function writeJson(key: string, value: unknown): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(key, JSON.stringify(value));
}

export function normalizeDeepseekModel(model: string): string {
  const trimmed = model.trim();
  return LEGACY_DEEPSEEK_MODELS[trimmed] ?? trimmed;
}

export function loadDingTalkConfig(): DingTalkConfig {
  return readJson(DINGTALK_KEY, DEFAULT_DINGTALK);
}

export function saveDingTalkConfig(config: DingTalkConfig): void {
  writeJson(DINGTALK_KEY, config);
}

export function loadLlmQuickConfig(): LlmQuickConfig {
  const raw = readJson(LLM_KEY, DEFAULT_LLM);
  const normalized = normalizeLlmQuickConfig(raw);
  return { ...normalized, provider: uiProviderFromStored(normalized) };
}

/** Restore UI provider after legacy saves that stored openai_compatible. */
export function uiProviderFromStored(config: LlmQuickConfig): string {
  const host = config.baseUrl.toLowerCase();
  if (config.provider === "ollama" || host.includes("localhost:11434") || host.includes("127.0.0.1:11434")) {
    return "ollama";
  }
  if (config.provider === "openai_compatible" && host.includes("deepseek.com")) {
    return "deepseek";
  }
  if (config.provider === "openai_compatible" && host.includes("openai.com")) {
    return "openai";
  }
  if (config.provider === "openai_compatible" && host.includes("anthropic")) {
    return "anthropic";
  }
  return config.provider || DEFAULT_LLM.provider;
}

export function saveLlmQuickConfig(config: LlmQuickConfig): void {
  writeJson(LLM_KEY, normalizeLlmQuickConfig(config));
}

/** Map UI provider labels to Runtime registry providers. */
export function runtimeProviderForLlm(provider: string): string {
  if (provider === "ollama" || provider === "openai") return provider;
  return "openai_compatible";
}

/** Fix common DeepSeek / OpenAI-compatible URL mistakes before save or request. */
export function normalizeLlmQuickConfig(config: LlmQuickConfig): LlmQuickConfig {
  let provider = config.provider;
  let baseUrl = config.baseUrl.trim();
  let model = normalizeDeepseekModel(config.model.trim());

  if (provider === "deepseek") {
    if (!model) model = "deepseek-v4-flash";
    if (!baseUrl || /deepseek\.com/i.test(baseUrl)) {
      baseUrl = DEEPSEEK_OPENAI_BASE_URL;
    }
  }

  if (provider === "ollama") {
    baseUrl = "http://localhost:11434";
    if (!model) model = "llama3.2";
  }

  if (provider === "anthropic") {
    /* UI label only — runtime maps to openai_compatible on sync */
  }

  const isOllama =
    provider === "ollama" ||
    baseUrl.includes("localhost:11434") ||
    baseUrl.includes("127.0.0.1:11434");

  if (!baseUrl.startsWith("http://") && !baseUrl.startsWith("https://")) {
    baseUrl = `https://${baseUrl}`;
  }
  if (!isOllama && baseUrl.startsWith("http://")) {
    baseUrl = `https://${baseUrl.slice("http://".length)}`;
  }

  baseUrl = baseUrl.replace(/\/+$/, "");
  try {
    const parsed = new URL(baseUrl);
    if (/deepseek\.com/i.test(parsed.hostname)) {
      const path = parsed.pathname.replace(/\/+$/, "");
      if (path === "" || path === "/v1") {
        baseUrl = DEEPSEEK_OPENAI_BASE_URL;
      }
    }
  } catch {
    /* keep user input if unparsable */
  }

  return {
    ...config,
    provider,
    baseUrl,
    model: model || DEFAULT_LLM.model,
    label: config.label.trim() || DEFAULT_LLM.label,
  };
}

/** Match float quick-save to built-in Runtime preset when possible. */
export function presetModelIdForLlm(config: LlmQuickConfig): string | null {
  const normalized = normalizeLlmQuickConfig(config);
  const host = normalized.baseUrl.toLowerCase();
  if (normalized.provider === "ollama" || host.includes("localhost:11434") || host.includes("127.0.0.1:11434")) {
    return "ollama-local";
  }
  if (host.includes("deepseek.com")) return "deepseek-chat";
  if (host.includes("openai.com")) return "openai-default";
  if (host.includes("moonshot.cn")) return "moonshot-kimi";
  if (host.includes("dashscope.aliyuncs.com")) return "qwen-turbo";
  if (host.includes("bigmodel.cn")) return "zhipu-glm4";
  if (host.includes("siliconflow.cn")) return "siliconflow-deepseek";
  if (host.includes("generativelanguage.googleapis.com")) return "google-gemini";
  return null;
}

export function buildOllamaLocalPayload(model = "llama3.2") {
  return {
    presetId: "ollama-local",
    payload: {
      name: "Ollama 本地",
      provider: "ollama",
      base_url: "http://localhost:11434",
      model,
      api_key: "",
      is_default: true,
      enabled: true,
    },
  };
}

/** Payload for pushing float LLM settings into Runtime model registry. */
export function buildRuntimeModelPayload(config?: LlmQuickConfig): {
  presetId: string | null;
  payload: {
    name: string;
    provider: string;
    base_url: string;
    model: string;
    api_key: string;
    is_default: boolean;
    enabled: boolean;
  };
} | null {
  const normalized = normalizeLlmQuickConfig(config ?? loadLlmQuickConfig());
  const presetId = presetModelIdForLlm(normalized);
  const isOllama =
    normalized.provider === "ollama" ||
    normalized.baseUrl.includes("localhost:11434") ||
    normalized.baseUrl.includes("127.0.0.1:11434");
  if (!normalized.apiKey.trim() && !isOllama) return null;

  return {
    presetId,
    payload: {
      name: normalized.label.trim() || (isOllama ? "Ollama 本地" : "DeepSeek Chat"),
      provider: isOllama ? "ollama" : runtimeProviderForLlm(normalized.provider),
      base_url: isOllama ? "http://localhost:11434" : normalized.baseUrl,
      model: normalized.model || (isOllama ? "llama3.2" : "deepseek-v4-flash"),
      api_key: normalized.apiKey.trim(),
      is_default: false,
      enabled: true,
    },
  };
}

export function formatLlmTestFailure(detail: string): string {
  const lower = detail.toLowerCase();
  if (lower.includes("401") || lower.includes("unauthorized")) {
    return "API Key 无效或已过期 — 请在 platform.deepseek.com 检查 Key 是否有效且有余额";
  }
  return detail;
}

/** Push float LLM settings into Runtime (when localStorage has a key). */
export async function syncLlmQuickConfigToRuntime(): Promise<{
  ok: boolean;
  modelId?: string;
  testOk?: boolean;
  testDetail?: string;
  error?: string;
}> {
  const sync = buildRuntimeModelPayload();
  if (!sync) return { ok: false, error: "missing_key" };
  const { brainApi } = await import("./api");
  try {
    const profile = sync.presetId
      ? (await brainApi.updateModel(sync.presetId, sync.payload)).model
      : (await brainApi.createModel(sync.payload)).model;
    const test = await brainApi.testModel(profile.id);
    if (!test.success) {
      try {
        await brainApi.updateModel("ollama-local", { is_default: true, enabled: true });
        if (sync.presetId) {
          await brainApi.updateModel(sync.presetId, { is_default: false });
        }
      } catch {
        /* best-effort rollback so Ollama stays chat fallback */
      }
      return {
        ok: true,
        modelId: profile.id,
        testOk: false,
        testDetail: test.detail,
      };
    }
    const activated = sync.presetId
      ? (await brainApi.updateModel(sync.presetId, { is_default: true, enabled: true })).model
      : profile;
    try {
      await brainApi.updateModel("ollama-local", { is_default: false });
    } catch {
      /* non-fatal */
    }
    return {
      ok: true,
      modelId: activated.id,
      testOk: true,
      testDetail: test.detail,
    };
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : "sync_failed" };
  }
}

export async function syncOllamaLocalToRuntime(model = "llama3.2"): Promise<{
  ok: boolean;
  modelId?: string;
  testOk?: boolean;
  testDetail?: string;
  error?: string;
}> {
  const sync = buildOllamaLocalPayload(model);
  const { brainApi } = await import("./api");
  try {
    const { model: profile } = await brainApi.updateModel(sync.presetId, sync.payload);
    const test = await brainApi.testModel(profile.id);
    return {
      ok: true,
      modelId: profile.id,
      testOk: test.success,
      testDetail: test.detail,
    };
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : "sync_failed" };
  }
}

/** Fire-and-forget DingTalk robot message (client-side, demo-friendly). */
export async function sendDingTalkTest(config: DingTalkConfig, text: string): Promise<void> {
  if (!config.webhook.trim()) throw new Error("请先填写 Webhook 地址");
  const url = config.webhook.trim();
  const body = { msgtype: "text", text: { content: text } };
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`发送失败 (${res.status})`);
}
