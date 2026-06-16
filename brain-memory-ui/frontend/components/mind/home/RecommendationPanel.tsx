"use client";

import { useState } from "react";
import { CheckCircle2, Loader2, Sparkles } from "lucide-react";
import type { CognitiveOutput } from "@/lib/cognitiveTypes";
import {
  displayAction,
  priorityLabel,
  reversibilityLabel,
} from "@/lib/cognitiveDisplay";
import { executeCognitiveAction } from "@/lib/cognitiveActions";
import { useCnexusConfigStore } from "@/lib/cnexusConfigStore";
import { useMindTheme } from "../MindUiProvider";

type Props = {
  data: CognitiveOutput;
  loading: boolean;
  refreshing?: boolean;
  error: string | null;
};

/** 右侧 — 今日建议（原左侧 hero） */
export function RecommendationPanel({ data, loading, refreshing, error }: Props) {
  const t = useMindTheme();
  const lastAction = useCnexusConfigStore((s) => s.lastActionApplied);
  const [toast, setToast] = useState<string | null>(null);

  const actions = (data.top_actions?.length ? data.top_actions : data.actions).slice(0, 3);
  const hero = actions[0] ? displayAction(actions[0]) : null;

  const onApply = () => {
    if (!actions[0]) return;
    const result = executeCognitiveAction(actions[0]);
    setToast(result.message);
    window.setTimeout(() => setToast(null), 4000);
  };

  return (
    <aside
      className="w-full shrink-0 rounded-2xl border p-5 relative overflow-hidden flex flex-col"
      style={{
        borderColor: t.blue,
        background: `radial-gradient(ellipse at 100% 0%, ${t.blueSoft} 0%, transparent 50%), ${t.surface}`,
        boxShadow: t.goalGlow,
      }}
    >
      {loading && (
        <div
          className="absolute inset-0 flex items-center justify-center backdrop-blur-[1px] z-10"
          style={{ backgroundColor: "rgba(7,11,20,0.5)" }}
        >
          <Loader2 className="w-6 h-6 animate-spin" style={{ color: t.blue }} />
        </div>
      )}

      <div className="flex items-center gap-2 mb-3">
        <Sparkles className="w-4 h-4" style={{ color: t.blue }} />
        <p className="text-xs font-medium" style={{ color: t.blue }}>
          今日建议
        </p>
        {refreshing && !loading && (
          <span
            className="w-1.5 h-1.5 rounded-full animate-pulse"
            style={{ backgroundColor: t.blue }}
            title="更新中"
          />
        )}
      </div>

      <h2 className="text-xl font-bold leading-snug mb-2" style={{ color: t.text }}>
        {hero?.title ?? "正在观察系统运行…"}
      </h2>
      <p className="text-sm leading-relaxed mb-4" style={{ color: t.textMuted }}>
        {hero?.subtitle ?? "使用提问、记录或分析后，系统会把运行历史压缩成可执行的结论。"}
      </p>

      {hero && (
        <div className="flex flex-wrap gap-2 mb-4">
          <span
            className="text-[11px] px-2 py-0.5 rounded-full"
            style={{ backgroundColor: t.orangeSoft, color: t.orange }}
          >
            {priorityLabel(hero.priority)}
          </span>
          <span
            className="text-[11px] px-2 py-0.5 rounded-full"
            style={{ backgroundColor: t.greenSoft, color: t.green }}
          >
            {reversibilityLabel(hero.reversibility)}
          </span>
        </div>
      )}

      {hero?.why && (
        <div
          className="rounded-xl p-3 mb-4 text-xs leading-relaxed"
          style={{ backgroundColor: t.chatBg, color: t.textMuted, borderLeft: `3px solid ${t.purple}` }}
        >
          <span style={{ color: t.purple }}>为什么 · </span>
          {hero.why}
        </div>
      )}

      {error && (
        <p className="text-xs mb-3" style={{ color: t.red }}>
          {error}
        </p>
      )}
      {(toast || lastAction) && (
        <p className="text-xs mb-3 flex items-center gap-1.5" style={{ color: t.green }}>
          <CheckCircle2 className="w-3.5 h-3.5" />
          {toast || "已应用建议"}
        </p>
      )}

      {hero && hero.raw !== "continue_monitoring" && (
        <button
          type="button"
          onClick={onApply}
          className="w-full py-2.5 rounded-xl text-sm font-semibold mt-auto"
          style={{ backgroundColor: t.blue, color: "#fff" }}
        >
          {hero.cta}
        </button>
      )}

      {actions.length > 1 && (
        <div className="mt-4 pt-4 border-t" style={{ borderColor: t.border }}>
          <p className="text-[10px] mb-2" style={{ color: t.textLight }}>
            其他建议
          </p>
          <div className="flex flex-col gap-1.5">
            {actions.slice(1).map((a) => {
              const d = displayAction(a);
              return (
                <span
                  key={a.action}
                  className="text-[11px] px-2.5 py-1.5 rounded-lg border"
                  style={{ borderColor: t.border, color: t.textMuted }}
                >
                  {d.title}
                </span>
              );
            })}
          </div>
        </div>
      )}
    </aside>
  );
}
