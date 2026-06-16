"use client";

import Link from "next/link";
import {
  ArrowLeft,
  Database,
  Eye,
  Upload,
  Wrench,
} from "lucide-react";
import type { ExecLogEvent, ExecTraceManifest } from "@/lib/cognitiveTypes";
import type { CognitiveOutput } from "@/lib/cognitiveTypes";
import { MemoryPanel } from "../MemoryPanel";
import { UploadPanel } from "../UploadPanel";
import { CognitiveSourceBar } from "./CognitiveSourceBar";
import { SystemObservationPanel } from "./SystemObservationPanel";
import { HomeBottomPanel } from "./HomeBottomPanel";
import { DashboardHeader } from "./DashboardHeader";
import { RuntimeDashboard } from "./RuntimeDashboard";
import { useMindTheme } from "../MindUiProvider";

const SECTIONS = [
  { id: "zone-execution", label: "仪表盘", icon: Eye },
  { id: "memory-panel", label: "记忆索引", icon: Database },
  { id: "import", label: "高级导入", icon: Upload },
  { id: "runtime", label: "运行配置", icon: Wrench },
] as const;

function scrollTo(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
}

type Props = {
  data: CognitiveOutput;
  loading: boolean;
  error: string | null;
  isExample: boolean;
  isEmpty: boolean;
  onSwitchSource: () => void;
  logs: ExecLogEvent[];
  traces: ExecTraceManifest[];
  traceLoading: boolean;
  traceRefreshing?: boolean;
  onRefreshTrace: () => void;
};

/** Mind 概览 — 系统可观测运行面板（非对话界面） */
export function HomeClassicMindView({
  data,
  loading,
  error,
  isExample,
  isEmpty,
  onSwitchSource,
  logs,
  traces,
  traceLoading,
  traceRefreshing,
  onRefreshTrace,
}: Props) {
  const t = useMindTheme();

  return (
    <div className="space-y-5 w-full max-w-[920px]">
      <div className="space-y-3">
        <DashboardHeader />
        <CognitiveSourceBar
          generatedAt={data.generated_at}
          windowSize={data.window_size}
          onSwitchSource={onSwitchSource}
        />
      </div>

      <nav
        className="sticky top-0 z-20 flex flex-wrap items-center gap-2 rounded-xl border px-3 py-2 backdrop-blur-md"
        style={{
          borderColor: t.border,
          backgroundColor: `${t.surface}ee`,
        }}
        aria-label="Mind 概览导航"
      >
        <Link
          href="/shell?layout=overview"
          className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[11px] border font-medium"
          style={{ borderColor: t.blue, color: t.blue, backgroundColor: t.blueSoft }}
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          工作台（对话入口）
        </Link>
        {SECTIONS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            type="button"
            onClick={() => scrollTo(id)}
            className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[11px] border transition-opacity hover:opacity-90"
            style={{ borderColor: t.border, color: t.textMuted, backgroundColor: t.chatBg }}
          >
            <Icon className="w-3.5 h-3.5" />
            {label}
          </button>
        ))}
      </nav>

      <section id="observation" className="scroll-mt-24">
        <SectionTitle title="认知观察详情" hint="系统观察 · 关键洞察 · 规律与新发现" />
        <SystemObservationPanel
          data={data}
          loading={loading}
          error={error}
          isExample={isExample}
          isEmpty={isEmpty}
          hideNarrative
        />
      </section>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 scroll-mt-24">
        <section id="memory-panel" className="min-w-0">
          <SectionTitle title="记忆索引浏览" hint="分层筛选 · 语义检索" />
          <MemoryPanel variant="overview" />
        </section>

        <section id="import" className="min-w-0">
          <SectionTitle title="高级数据写入" hint="文本 · URL · 批量" />
          <UploadPanel variant="overview" excludeDocImport />
        </section>
      </div>

      <div id="zone-execution" className="scroll-mt-24">
        <RuntimeDashboard
          data={data}
          logs={logs}
          traces={traces}
          loading={loading || traceLoading}
          refreshing={traceRefreshing}
          isEmpty={isEmpty}
          onRefresh={onRefreshTrace}
        />
      </div>

      <section id="runtime" className="scroll-mt-24">
        <SectionTitle title="运行配置与追踪" hint="运行记录 · 调度模式 · 模型 API" />
        <HomeBottomPanel
          logs={logs}
          traces={traces}
          traceLoading={traceLoading}
          traceRefreshing={traceRefreshing}
          onRefreshTrace={onRefreshTrace}
        />
      </section>
    </div>
  );
}

function SectionTitle({ title, hint }: { title: string; hint: string }) {
  const t = useMindTheme();
  return (
    <div className="flex items-end justify-between gap-3 mb-3 px-1">
      <h2 className="text-sm font-semibold" style={{ color: t.text }}>
        {title}
      </h2>
      <p className="text-[10px] shrink-0 hidden sm:block" style={{ color: t.textLight }}>
        {hint}
      </p>
    </div>
  );
}
