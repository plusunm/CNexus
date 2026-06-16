"use client";

import { useMemo } from "react";
import { useMindStore } from "@/cnexus-kernel";
import { floatTy } from "@/lib/floatTypography";
import { FloatSelect } from "./floating/FloatSelect";
import { useMindTheme } from "./MindUiProvider";

type Props = {
  compact?: boolean;
  className?: string;
  disabled?: boolean;
};

function modelLabel(id: string, name: string, model: string, isDefault: boolean): string {
  const title = name?.trim() || id;
  const suffix = isDefault ? " ★" : "";
  if (id === "ollama-local") {
    return `Ollama 本地 · ${model}${suffix}`;
  }
  return `${title} · ${model}${suffix}`;
}

export function ChatModelSelect({ compact = false, className, disabled = false }: Props) {
  const t = useMindTheme();
  const models = useMindStore((s) => s.models);
  const selectedModelId = useMindStore((s) => s.selectedModelId);
  const setSelectedModel = useMindStore((s) => s.setSelectedModel);

  const chatModels = useMemo(
    () =>
      models.filter(
        (m) => m.enabled && (m.api_key_set || m.provider === "ollama"),
      ),
    [models],
  );

  const options = useMemo(
    () =>
      chatModels.map((m) => ({
        value: m.id,
        label: modelLabel(m.id, m.name, m.model, m.is_default),
      })),
    [chatModels],
  );

  const selected =
    chatModels.find((m) => m.id === selectedModelId) ??
    chatModels.find((m) => m.is_default) ??
    chatModels[0];

  if (options.length === 0) {
    return (
      <p
        className={`${compact ? floatTy.caption : "text-[10px]"} ${className ?? ""}`}
        style={{ color: t.orange }}
      >
        未配置可用模型 — 悬浮窗菜单 →「大模型 API」→ Provider 选「Ollama 本地」并保存
      </p>
    );
  }

  const value = selected?.id ?? options[0]?.value ?? "";

  return (
    <div className={className} style={disabled ? { opacity: 0.55, pointerEvents: "none" } : undefined}>
      <FloatSelect
        label={compact ? "对话模型" : "当前对话模型"}
        value={value}
        options={options}
        onChange={(id) => setSelectedModel(id)}
      />
      {selected?.id === "ollama-local" && (
        <p className={`mt-1 ${compact ? floatTy.caption : "text-[10px]"}`} style={{ color: t.textMuted }}>
          使用本机 Ollama（无需 API Key）· 模型名在上方 Model ID 填写，如 llama3.2
        </p>
      )}
    </div>
  );
}
