"use client";

import { useMindOverview, CONNECTION_LABELS } from "@/cnexus-kernel";
import { useMindConnection } from "../MindConnectionProvider";
import { MindModeSwitch } from "../MindModeSwitch";
import { useMindTheme, useMindUi } from "../MindUiProvider";
import { ActivityFeedsRow } from "../ActivityFeedsRow";
import { ChatPanel } from "../ChatPanel";
import { MemoryPanel } from "../MemoryPanel";
import { UploadPanel } from "../UploadPanel";

/** 路线 B — 注意力引力场（认知模式） */
export default function CognitiveMindLayout() {
  const t = useMindTheme();
  const { mode } = useMindUi();
  const { overview, signals, isDemo, isLive } = useMindOverview();
  const { disconnect } = useMindConnection();
  const { goal, focus } = overview.cards;

  return (
    <div className="min-h-screen flex flex-col" style={{ backgroundColor: t.bg }}>
      {/* Top bar */}
      <header
        className="flex items-center justify-between gap-4 px-4 md:px-6 py-3 border-b shrink-0"
        style={{ borderColor: t.border, backgroundColor: t.surface }}
      >
        <div className="flex items-center gap-3">
          <span className="text-sm font-bold tracking-tight" style={{ color: t.blue }}>
            CNexus
          </span>
          <span className="text-[10px] hidden sm:inline" style={{ color: t.textLight }}>
            认知模式 · Attention Gravity
          </span>
        </div>
        <MindModeSwitch compact />
        <div className="flex items-center gap-2">
          <button
            type="button"
            className="text-[10px] px-2 py-1 rounded border"
            style={{ borderColor: t.border, color: t.textMuted }}
            onClick={disconnect}
          >
            切换数据源
          </button>
          <div className="flex items-center gap-2 text-[10px]" style={{ color: t.textMuted }}>
            <span
              className="w-2 h-2 rounded-full"
              style={{ backgroundColor: isDemo ? t.orange : isLive ? t.green : t.red }}
            />
            {isDemo ? CONNECTION_LABELS.demo.badge : isLive ? overview.system.health_label : signals.health.connectionLabel}
          </div>
        </div>
      </header>

      <div className="flex-1 overflow-auto p-4 md:p-6 space-y-5 max-w-[1600px] mx-auto w-full">
        {/* Goal anchor — 高视觉重心 */}
        <section
          className="rounded-2xl border p-6 md:p-8"
          style={{
            borderColor: t.blue,
            backgroundColor: t.blueSoft,
            boxShadow: t.goalGlow,
          }}
          id="goals"
        >
          <p
            className="text-[11px] uppercase tracking-widest mb-2 font-medium"
            style={{ color: t.blue, fontFamily: t.fontMono }}
          >
            canonical goal · system truth
          </p>
          <h1
            className="text-2xl md:text-3xl font-bold leading-tight mb-4 max-w-3xl"
            style={{ color: t.text }}
          >
            {goal.title}
          </h1>
          <div className="h-1.5 rounded-full mb-4 max-w-md overflow-hidden" style={{ backgroundColor: t.border }}>
            <div
              className="h-full rounded-full transition-all duration-500"
              style={{
                width: `${Math.round((goal.progress ?? 0) * 100)}%`,
                backgroundColor: t.blue,
              }}
            />
          </div>
          <div
            className="flex flex-wrap gap-4 text-xs"
            style={{ color: t.textMuted, fontFamily: t.fontMono }}
          >
            <span>
              progress <b style={{ color: t.blue }}>{goal.progress_label}</b>
            </span>
            <span>
              alignment <b style={{ color: t.blue }}>{goal.alignment_label}</b>
            </span>
            <span>
              priority <b style={{ color: t.orange }}>{goal.priority_label}</b>
            </span>
            <span>
              focus <b style={{ color: t.purple }}>{focus.title?.slice(0, 40)}</b>
            </span>
          </div>
        </section>

        {/* 三列引力场：Memory 左 · Chat 中 · Upload 右 */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 min-h-[480px]">
          <div className="lg:col-span-3 opacity-90 hover:opacity-100 transition-opacity" id="memory-panel">
            <p className="text-[10px] mb-2 uppercase tracking-wide" style={{ color: t.textLight }}>
              memory · 散列 · hover 增强
            </p>
            <MemoryPanel variant="cognitive" />
          </div>

          <div className="lg:col-span-6" id="chat-panel">
            <p className="text-[10px] mb-2 uppercase tracking-wide" style={{ color: t.textLight }}>
              chat · 流动层 · 沉浸
            </p>
            <ChatPanel variant="cognitive" />
          </div>

          <div
            className="lg:col-span-3 opacity-75 hover:opacity-95 transition-opacity"
            id="import"
          >
            <p className="text-[10px] mb-2 uppercase tracking-wide" style={{ color: t.textLight }}>
              upload · 边缘 · 低饱和
            </p>
            <UploadPanel variant="cognitive" />
          </div>
        </div>

        {/* 紧凑 feeds */}
        <div id="reflections" className="opacity-90">
          <ActivityFeedsRow compact />
        </div>

        <div id="governance" className="h-0" aria-hidden />

        <p className="text-[10px] text-center pb-4" style={{ color: t.textLight }}>
          模式: {mode} · 蓝=system truth · 紫=meta · 黄=pending · 红=conflict · 绿=resolved
        </p>
      </div>
    </div>
  );
}
