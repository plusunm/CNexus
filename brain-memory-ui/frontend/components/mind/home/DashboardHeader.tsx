"use client";

import { useMindOverview, CONNECTION_LABELS } from "@/cnexus-kernel";
import { healthColor } from "@/cnexus-kernel";
import { useMindTheme } from "../MindUiProvider";

/** Mind 概览 — 运行时仪表盘页眉（无拟人化、无对话入口） */
export function DashboardHeader() {
  const t = useMindTheme();
  const { overview, signals, runtimeState, isDemo, isLive } = useMindOverview();

  const badge = isDemo
    ? CONNECTION_LABELS.demo.badge
    : isLive
      ? overview.system.health_label
      : signals.health.connectionLabel;

  return (
    <header className="flex flex-col gap-1">
      <div className="flex items-center gap-2 flex-wrap">
        <h1 className="text-xl font-bold" style={{ color: t.text }}>
          CNexus 认知运行时
        </h1>
        <span
          className="text-[10px] px-2 py-0.5 rounded-full border"
          style={{
            color: isDemo ? t.orange : healthColor(overview.system.health_label),
            borderColor: isDemo ? t.orange : healthColor(overview.system.health_label),
          }}
        >
          {badge}
        </span>
      </div>
      <p className="text-sm" style={{ color: t.textMuted }}>
        System Observable Runtime Dashboard · 表达系统正在发生什么，而非对话内容
        {runtimeState?.timestamp ? ` · 同步 ${overview.system.last_update_ago}` : ""}
      </p>
    </header>
  );
}
