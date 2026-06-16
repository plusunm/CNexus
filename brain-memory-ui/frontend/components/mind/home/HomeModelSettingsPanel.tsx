"use client";

import { useEffect, useState } from "react";
import { isRuntimeReady } from "@/lib/api";
import { useMindStore } from "@/cnexus-kernel";
import {
  DEEPSEEK_MODEL_OPTIONS,
  DEEPSEEK_OPENAI_BASE_URL,
  loadLlmQuickConfig,
  normalizeDeepseekModel,
  normalizeLlmQuickConfig,
  saveLlmQuickConfig,
  syncLlmQuickConfigToRuntime,
  type LlmQuickConfig,
} from "@/lib/floatIntegrations";
import { useMindTheme } from "../MindUiProvider";
import { FloatSelect } from "../floating/FloatSelect";

const LLM_PROVIDER_OPTIONS = [
  { value: "deepseek", label: "DeepSeek 云端（推荐）" },
  { value: "ollama", label: "Ollama 本地" },
  { value: "openai", label: "OpenAI" },
  { value: "openai_compatible", label: "OpenAI 兼容 API" },
  { value: "anthropic", label: "Anthropic 兼容" },
] as const;

export function HomeModelSettingsPanel() {
  const t = useMindTheme();
  const models = useMindStore((s) => s.models);
  const selectedModelId = useMindStore((s) => s.selectedModelId);
  const [llm, setLlm] = useState<LlmQuickConfig>(() => loadLlmQuickConfig());
  const [status, setStatus] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setLlm(loadLlmQuickConfig());
  }, []);

  const fieldClass = "w-full border rounded-lg px-3 py-2 text-sm outline-none focus:ring-1";
  const fieldStyle: React.CSSProperties = {
    borderColor: t.border,
    backgroundColor: t.chatBg,
    color: t.text,
  };

  const activeModel = models.find((m) => m.id === selectedModelId);

  const save = async () => {
    const normalized = normalizeLlmQuickConfig(llm);
    const isOllama =
      normalized.provider === "ollama" ||
      normalized.baseUrl.includes("localhost:11434") ||
      normalized.baseUrl.includes("127.0.0.1:11434");
    if (!normalized.apiKey.trim() && !isOllama) {
      setStatus("请填写 API Key，或选择 Ollama 本地");
      return;
    }
    setLlm(normalized);
    saveLlmQuickConfig(normalized);
    setBusy(true);
    setStatus(null);
    try {
      const online = await isRuntimeReady({ skipWs: true });
      if (online) {
        const result = await syncLlmQuickConfigToRuntime();
        await useMindStore.getState().refreshModels();
        if (result.ok && result.testOk && result.modelId) {
          useMindStore.getState().setSelectedModel(result.modelId);
          setStatus(
            result.modelId === "ollama-local"
              ? "已切换为 Ollama 本地 — 可直接聊天（无需 Key）"
              : "已保存并同步到 Runtime",
          );
        } else if (result.ok) {
          setStatus("已保存 — 请检查 Base URL 与 Key 是否正确");
        } else {
          setStatus("已保存到本地，Runtime 同步失败");
        }
      } else {
        setStatus("已保存到本地 — 连接 Runtime 后将自动同步");
      }
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "保存失败");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="p-4 space-y-4">
      {activeModel && (
        <div
          className="rounded-xl px-3 py-2.5 text-xs border flex items-center justify-between gap-2"
          style={{ borderColor: t.border, backgroundColor: t.chatBg }}
        >
          <span style={{ color: t.textMuted }}>当前对话模型</span>
          <span className="font-medium truncate" style={{ color: t.green }}>
            {activeModel.name || activeModel.model}
          </span>
        </div>
      )}

      <p className="text-xs" style={{ color: t.textMuted }}>
        配置大模型 API — 支持 DeepSeek / Ollama / OpenAI 兼容接口
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <label className="flex flex-col gap-1.5 text-xs">
          <span style={{ color: t.textMuted }}>显示名称</span>
          <input
            className={fieldClass}
            style={fieldStyle}
            value={llm.label}
            onChange={(e) => setLlm((c) => ({ ...c, label: e.target.value }))}
          />
        </label>
        <FloatSelect
          label="Provider"
          value={llm.provider}
          options={[...LLM_PROVIDER_OPTIONS]}
          onChange={(provider) => {
            setLlm((c) => {
              const next = { ...c, provider };
              if (provider === "deepseek") {
                next.baseUrl = DEEPSEEK_OPENAI_BASE_URL;
                next.model = normalizeDeepseekModel(c.model.trim() || "deepseek-v4-flash");
                next.label = c.label.trim() || "DeepSeek V4 Flash";
              }
              if (provider === "ollama") {
                next.baseUrl = "http://localhost:11434";
                next.model = c.model.trim() || "llama3.2";
                next.label = c.label.trim() || "Ollama 本地";
                next.apiKey = "";
              }
              if (provider === "openai") {
                next.baseUrl = "https://api.openai.com/v1";
                next.label = c.label.trim() || "OpenAI";
              }
              return next;
            });
          }}
        />
        <label className="flex flex-col gap-1.5 text-xs md:col-span-2">
          <span style={{ color: t.textMuted }}>Base URL</span>
          <input
            className={fieldClass}
            style={fieldStyle}
            placeholder={DEEPSEEK_OPENAI_BASE_URL}
            value={llm.baseUrl}
            onChange={(e) => setLlm((c) => ({ ...c, baseUrl: e.target.value }))}
          />
        </label>
        <label className="flex flex-col gap-1.5 text-xs">
          <span style={{ color: t.textMuted }}>Model ID</span>
          {llm.provider === "deepseek" || llm.baseUrl.includes("deepseek.com") ? (
            <FloatSelect
              value={llm.model}
              options={DEEPSEEK_MODEL_OPTIONS.map((opt) => ({
                value: opt.value,
                label: opt.label,
              }))}
              onChange={(model) => setLlm((c) => ({ ...c, model }))}
            />
          ) : (
            <input
              className={fieldClass}
              style={fieldStyle}
              placeholder={llm.provider === "ollama" ? "llama3.2" : "deepseek-v4-flash"}
              value={llm.model}
              onChange={(e) => setLlm((c) => ({ ...c, model: e.target.value }))}
            />
          )}
        </label>
        <label className="flex flex-col gap-1.5 text-xs">
          <span style={{ color: t.textMuted }}>API Key</span>
          <input
            type="password"
            className={fieldClass}
            style={fieldStyle}
            placeholder={llm.provider === "ollama" ? "本地 Ollama 无需 Key" : "sk-..."}
            value={llm.apiKey}
            disabled={llm.provider === "ollama"}
            onChange={(e) => setLlm((c) => ({ ...c, apiKey: e.target.value }))}
          />
        </label>
      </div>

      <button
        type="button"
        disabled={busy}
        onClick={() => void save()}
        className="px-5 py-2.5 rounded-xl text-sm font-medium disabled:opacity-50"
        style={{ backgroundColor: t.purple, color: "#fff" }}
      >
        {busy ? "保存中…" : "保存配置"}
      </button>

      {status && (
        <p className="text-xs" style={{ color: status.includes("通过") ? t.green : t.textMuted }}>
          {status}
        </p>
      )}
    </div>
  );
}
