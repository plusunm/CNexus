"use client";

import { Target, Zap } from "lucide-react";
import { useMindOverview } from "@/cnexus-kernel";
import { EMPTY_INTENT_OBSERVATION } from "@/lib/runtimeTypes";
import { useMindTheme } from "../MindUiProvider";

/** 意向观测 — 活跃目标、焦点与主动推进信号 */
export function IntentObservationPanel() {
  const t = useMindTheme();
  const { overview, isLive, isDemo } = useMindOverview();
  const intent = overview.intent ?? {
    ...EMPTY_INTENT_OBSERVATION,
    goals: overview.cards.goal.title && overview.cards.goal.title !== "等待 Runtime 连接…"
      ? [{
          goal_id: "top-goal",
          description: overview.cards.goal.title ?? "—",
          priority: overview.cards.goal.priority ?? 0,
          priority_label: overview.cards.goal.priority_label ?? "—",
          motivation: 0.6,
          motivation_label: "60%",
          alignment_score: overview.cards.goal.alignment ?? 0,
          alignment_label: overview.cards.goal.alignment_label ?? "—",
          progress: overview.cards.goal.progress ?? 0,
          progress_label: overview.cards.goal.progress_label ?? "—",
          status: "active",
        }]
      : [],
    current_focus_label: overview.cards.focus.title ?? "—",
    active_goal_count: overview.cards.focus.related_goals ?? 0,
  };
  const offline = !isLive && !isDemo;
  const { proactive, goals } = intent;

  return (
    <section
      className="rounded-2xl border overflow-hidden"
      style={{ borderColor: t.border, backgroundColor: t.surface }}
    >
      <div
        className="flex items-center gap-2 px-4 py-3 border-b"
        style={{ borderColor: t.border, backgroundColor: t.chatBg }}
      >
        <Target className="w-4 h-4 shrink-0" style={{ color: t.green }} />
        <div className="min-w-0">
          <h3 className="text-sm font-semibold" style={{ color: t.text }}>意向观测</h3>
          <p className="text-[11px]" style={{ color: t.textMuted }}>
            IntentEngine · 活跃目标与主动推进
          </p>
        </div>
        {offline && (
          <span className="ml-auto text-[10px] px-2 py-0.5 rounded-full" style={{ backgroundColor: t.orangeSoft, color: t.orange }}>
            等待连接
          </span>
        )}
      </div>

      <div className="p-4 space-y-4">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-[11px]">
          <div className="rounded-lg border p-2.5" style={{ borderColor: t.border, backgroundColor: t.bg }}>
            <p style={{ color: t.textLight }}>当前焦点</p>
            <p className="text-xs font-medium mt-1 line-clamp-2" style={{ color: t.text }}>
              {intent.current_focus_label || overview.cards.focus.title || "—"}
            </p>
          </div>
          <div className="rounded-lg border p-2.5" style={{ borderColor: t.border, backgroundColor: t.bg }}>
            <p style={{ color: t.textLight }}>动机基线</p>
            <p className="text-xs font-medium mt-1" style={{ color: t.text }}>{intent.motivation_baseline_label}</p>
          </div>
          <div className="rounded-lg border p-2.5" style={{ borderColor: t.border, backgroundColor: t.bg }}>
            <p style={{ color: t.textLight }}>活跃目标</p>
            <p className="text-xs font-medium mt-1" style={{ color: t.text }}>{intent.active_goal_count} 个</p>
          </div>
          <div className="rounded-lg border p-2.5" style={{ borderColor: t.border, backgroundColor: t.bg }}>
            <p style={{ color: t.textLight }}>最近更新</p>
            <p className="text-xs font-medium mt-1" style={{ color: t.text }}>{intent.last_updated_ago}</p>
          </div>
        </div>

        <div
          className="rounded-xl border p-3 flex gap-3"
          style={{
            borderColor: proactive.should_trigger ? t.green : t.border,
            backgroundColor: proactive.should_trigger ? `${t.green}12` : t.bg,
          }}
        >
          <Zap
            className="w-4 h-4 shrink-0 mt-0.5"
            style={{ color: proactive.should_trigger ? t.green : t.textLight }}
          />
          <div className="min-w-0">
            <p className="text-xs font-semibold" style={{ color: t.text }}>
              主动推进信号 · {proactive.should_trigger ? "已触发" : "未触发"}
            </p>
            {proactive.should_trigger ? (
              <>
                <p className="text-sm mt-1" style={{ color: t.text }}>{proactive.suggested_action || proactive.reason}</p>
                <p className="text-[11px] mt-1" style={{ color: t.textMuted }}>
                  优先级 {proactive.priority_label}
                  {proactive.goal_id ? ` · ${proactive.goal_id}` : ""}
                </p>
              </>
            ) : (
              <p className="text-[11px] mt-1" style={{ color: t.textMuted }}>
                当前动机或进度未达主动推进阈值
              </p>
            )}
          </div>
        </div>

        <div className="rounded-xl border overflow-hidden" style={{ borderColor: t.border }}>
          <div
            className="grid grid-cols-[1fr_repeat(4,minmax(52px,1fr))] gap-2 px-3 py-2 text-[10px] uppercase tracking-wide border-b"
            style={{ borderColor: t.border, backgroundColor: t.chatBg, color: t.textLight }}
          >
            <span>目标</span>
            <span className="text-center">进度</span>
            <span className="text-center">动机</span>
            <span className="text-center">对齐</span>
            <span className="text-center">优先级</span>
          </div>
          {goals.length ? goals.map((goal) => (
            <div
              key={goal.goal_id}
              className="grid grid-cols-[1fr_repeat(4,minmax(52px,1fr))] gap-2 px-3 py-2.5 text-[11px] border-b last:border-b-0 items-center"
              style={{ borderColor: t.border, color: t.textMuted }}
            >
              <span className="line-clamp-2" style={{ color: t.text }}>{goal.description}</span>
              <span className="text-center">{goal.progress_label}</span>
              <span className="text-center">{goal.motivation_label}</span>
              <span className="text-center">{goal.alignment_label}</span>
              <span className="text-center" style={{ color: goal.priority_label === "高" ? t.red : t.text }}>
                {goal.priority_label}
              </span>
            </div>
          )) : (
            <p className="px-3 py-4 text-sm text-center" style={{ color: t.textMuted }}>暂无活跃目标</p>
          )}
        </div>
      </div>
    </section>
  );
}
