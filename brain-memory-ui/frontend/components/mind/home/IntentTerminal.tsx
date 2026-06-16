"use client";

import { useState } from "react";
import { ArrowUp, Loader2, MessageSquarePlus, Search, Sparkles, BookmarkPlus } from "lucide-react";
import { brainApi, getDefaultFullCognitiveLoop } from "@/lib/api";
import { useMindStore } from "@/cnexus-kernel";
import { useMindTheme } from "../MindUiProvider";
import { INTENT_MODE_LABELS, type IntentMode } from "@/lib/cognitiveTypes";

const MODE_ICONS = {
  ask: MessageSquarePlus,
  capture: BookmarkPlus,
  analyze: Sparkles,
  recall: Search,
} as const;

type Props = {
  onAnalyze?: () => Promise<void>;
  onResult?: (mode: IntentMode, payload: string) => void;
  intentResult?: string | null;
  disabled?: boolean;
  disabledHint?: string;
  variant?: "compact" | "primary";
};

export function IntentTerminal({
  onAnalyze,
  onResult,
  intentResult,
  disabled,
  disabledHint,
  variant = "compact",
}: Props) {
  const t = useMindTheme();
  const selectedModelId = useMindStore((s) => s.selectedModelId);
  const [mode, setMode] = useState<IntentMode>("ask");
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const isPrimary = variant === "primary";

  const meta = INTENT_MODE_LABELS[mode];

  const submit = async () => {
    if (disabled) return;
    const text = input.trim();
    if (mode !== "analyze" && !text) return;
    setLoading(true);
    try {
      if (mode === "ask") {
        const res = await brainApi.chat(text, selectedModelId, true, getDefaultFullCognitiveLoop());
        onResult?.(mode, res.reply || "（无回复）");
      } else if (mode === "capture") {
        const layer = text.includes("目标") ? "goal" : "episodic";
        await brainApi.capture(text, layer, "user", 0.75, true);
        onResult?.(mode, `已写入记忆（${layer === "goal" ? "目标" : "情景"}层）`);
      } else if (mode === "recall") {
        const res = await brainApi.recall(text);
        onResult?.(mode, res.context || "未找到相关记忆");
      } else {
        await onAnalyze?.();
        onResult?.(mode, text ? `已针对「${text}」重新分析` : "已重新分析运行历史");
      }
      if (mode !== "analyze") setInput("");
    } catch (err) {
      onResult?.(mode, err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <section
      className={`rounded-2xl border flex flex-col ${isPrimary ? "flex-1 min-h-[560px] lg:min-h-[640px] p-5 md:p-6" : "p-4"}`}
      style={{
        borderColor: isPrimary ? t.blue : t.border,
        background: isPrimary
          ? `radial-gradient(ellipse at 20% 100%, ${t.blueSoft} 0%, transparent 55%), linear-gradient(180deg, ${t.surface} 0%, ${t.chatBg} 100%)`
          : `linear-gradient(180deg, ${t.surface} 0%, ${t.chatBg} 100%)`,
        boxShadow: isPrimary ? t.goalGlow : undefined,
      }}
    >
      {isPrimary && (
        <p className="text-xs font-medium mb-3" style={{ color: t.blue }}>
          与系统对话
        </p>
      )}

      {disabled && disabledHint && (
        <p className="text-xs mb-3 px-3 py-2 rounded-lg border" style={{ borderColor: t.orange, color: t.orange, backgroundColor: t.orangeSoft }}>
          {disabledHint}
        </p>
      )}

      <div className="flex flex-wrap gap-2 mb-3">
        {(Object.keys(INTENT_MODE_LABELS) as IntentMode[]).map((key) => {
          const Icon = MODE_ICONS[key];
          const active = mode === key;
          return (
            <button
              key={key}
              type="button"
              disabled={disabled || loading}
              onClick={() => setMode(key)}
              className={`inline-flex items-center gap-1.5 rounded-full font-medium border transition-colors disabled:opacity-45 disabled:cursor-not-allowed active:scale-[0.98] ${
                isPrimary ? "px-3.5 py-2 text-sm" : "px-3 py-1.5 text-xs"
              }`}
              style={{
                borderColor: active ? t.blue : t.border,
                backgroundColor: active ? t.blueSoft : "transparent",
                color: active ? t.blue : t.textMuted,
              }}
            >
              <Icon className={isPrimary ? "w-4 h-4" : "w-3.5 h-3.5"} />
              {INTENT_MODE_LABELS[key].label}
            </button>
          );
        })}
      </div>

      <p className={`mb-3 ${isPrimary ? "text-xs" : "text-[11px]"}`} style={{ color: t.textLight }}>
        {meta.hint}
      </p>

      {isPrimary && (
        <div
          className="flex-1 rounded-xl border p-4 mb-4 overflow-auto min-h-[320px] lg:min-h-[420px]"
          style={{ borderColor: t.border, backgroundColor: t.bg }}
        >
          {intentResult ? (
            <p className="text-sm leading-relaxed whitespace-pre-wrap" style={{ color: t.text }}>
              {intentResult}
            </p>
          ) : (
            <p className="text-sm" style={{ color: t.textLight }}>
              在此显示对话回复、回忆结果或操作反馈…
            </p>
          )}
        </div>
      )}

      <div className={`flex gap-2 ${isPrimary ? "mt-auto" : ""}`}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={meta.placeholder}
          className={`flex-1 outline-none rounded-xl px-4 border ${
            isPrimary ? "text-sm py-3.5" : "text-sm py-3"
          }`}
          style={{ borderColor: t.border, backgroundColor: t.bg, color: t.text }}
          disabled={disabled || loading}
          onKeyDown={(e) => e.key === "Enter" && void submit()}
        />
        <button
          type="button"
          disabled={loading || disabled || (mode !== "analyze" && !input.trim())}
          onClick={() => void submit()}
          className={`rounded-xl flex items-center gap-2 font-medium disabled:opacity-40 shrink-0 transition-transform active:scale-[0.98] ${
            isPrimary ? "px-6 py-3.5 text-sm" : "px-5 py-3 text-sm"
          }`}
          style={{ backgroundColor: t.blue, color: "#fff" }}
        >
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <ArrowUp className="w-4 h-4" />}
          发送
        </button>
      </div>
    </section>
  );
}
