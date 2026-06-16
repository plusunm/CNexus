"use client";

import { useMemo } from "react";
import { Activity, Brain, Cpu, Loader2, RefreshCw, Shield } from "lucide-react";
import { useMindOverview } from "@/cnexus-kernel";
import type { CognitiveOutput, ExecLogEvent, ExecTraceManifest } from "@/lib/cognitiveTypes";
import { buildRuntimeDashboardModel, type RuntimeSemanticLine, type RuntimeZone } from "@/lib/runtimeSemantic";
import { useMindTheme } from "../MindUiProvider";

const ZONES: {
  id: RuntimeZone;
  label: string;
  sub: string;
  icon: typeof Cpu;
  accentKey: "blue" | "green" | "purple" | "orange";
}[] = [
  { id: "execution", label: "EXECUTION", sub: "执行层", icon: Cpu, accentKey: "blue" },
  { id: "memory", label: "MEMORY", sub: "记忆层", icon: Activity, accentKey: "green" },
  { id: "cognition", label: "COGNITION", sub: "认知层", icon: Brain, accentKey: "purple" },
  { id: "governance", label: "GOVERNANCE", sub: "治理层", icon: Shield, accentKey: "orange" },
];

type Props = {
  data: CognitiveOutput;
  logs: ExecLogEvent[];
  traces: ExecTraceManifest[];
  loading: boolean;
  refreshing?: boolean;
  isEmpty: boolean;
  onRefresh: () => void;
};

export function RuntimeDashboard({ data, logs, traces, loading, refreshing, isEmpty, onRefresh }: Props) {
  const t = useMindTheme();
  const { overview, runtimeState, isDemo, isLive } = useMindOverview();

  const model = useMemo(
    () =>
      buildRuntimeDashboardModel({
        logs,
        traces,
        data,
        overview,
        runtimeState,
        isDemo,
        isLive,
        isEmpty,
      }),
    [logs, traces, data, overview, runtimeState, isDemo, isLive, isEmpty],
  );

  return (
    <section
      className="rounded-2xl border overflow-hidden"
      style={{ borderColor: t.border, backgroundColor: t.surface }}
      aria-label="认知运行时仪表盘"
    >
      <header
        className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 px-4 py-3 border-b"
        style={{ borderColor: t.border, backgroundColor: t.chatBg }}
      >
        <div>
          <p className="text-[10px] uppercase tracking-[0.2em]" style={{ color: t.textLight, fontFamily: t.fontMono }}>
            Cognitive Runtime Dashboard
          </p>
          <h2 className="text-base font-semibold mt-0.5" style={{ color: t.text }}>
            系统可观测运行面板
          </h2>
          <p className="text-[11px] mt-1" style={{ color: t.textMuted }}>
            实时状态流 · 非对话界面
            {model.updatedAt ? ` · 更新 ${formatTime(model.updatedAt)}` : ""}
          </p>
        </div>
        <button
          type="button"
          onClick={onRefresh}
          disabled={loading}
          className="inline-flex items-center gap-2 px-3 py-2 rounded-lg text-xs border shrink-0 disabled:opacity-50"
          style={{ borderColor: t.border, color: t.textMuted, backgroundColor: t.bg }}
        >
          {loading || refreshing ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <RefreshCw className="w-3.5 h-3.5" />
          )}
          刷新状态流
        </button>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-0 divide-y md:divide-y-0 md:divide-x xl:divide-x divide-[color:var(--dash-divider)]" style={{ ["--dash-divider" as string]: t.border }}>
        {ZONES.map(({ id, label, sub, icon: Icon, accentKey }) => {
          const accent = t[accentKey];
          const soft =
            accentKey === "blue"
              ? t.blueSoft
              : accentKey === "green"
                ? t.greenSoft
                : accentKey === "purple"
                  ? t.purpleSoft
                  : t.orangeSoft;
          const items = model[id];
          return (
            <div key={id} id={`zone-${id}`} className="p-4 min-h-[220px] flex flex-col">
              <div className="flex items-center gap-2 mb-3">
                <div
                  className="w-8 h-8 rounded-lg flex items-center justify-center"
                  style={{ backgroundColor: soft, color: accent }}
                >
                  <Icon className="w-4 h-4" />
                </div>
                <div>
                  <p className="text-[10px] font-semibold tracking-wider" style={{ color: accent, fontFamily: t.fontMono }}>
                    {label}
                  </p>
                  <p className="text-[11px]" style={{ color: t.textMuted }}>
                    {sub}
                  </p>
                </div>
              </div>
              <ul className="space-y-2.5 flex-1">
                {items.map((item) => (
                  <StateLine key={item.id} item={item} accent={accent} />
                ))}
              </ul>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function StateLine({ item, accent }: { item: RuntimeSemanticLine; accent: string }) {
  const t = useMindTheme();
  const dotColor =
    item.status === "active"
      ? accent
      : item.status === "warning"
        ? t.orange
        : item.status === "completed"
          ? t.green
          : t.textLight;

  return (
    <li className="flex gap-2.5 items-start">
      <span className="relative mt-1.5 flex h-2 w-2 shrink-0">
        {item.status === "active" && (
          <span
            className="absolute inline-flex h-full w-full rounded-full opacity-40 animate-ping"
            style={{ backgroundColor: dotColor }}
          />
        )}
        <span className="relative inline-flex h-2 w-2 rounded-full" style={{ backgroundColor: dotColor }} />
      </span>
      <div className="min-w-0">
        <p className="text-[12px] leading-relaxed" style={{ color: t.text }}>
          {item.text}
        </p>
        {item.timestamp && (
          <p className="text-[10px] mt-0.5" style={{ color: t.textLight, fontFamily: t.fontMono }}>
            {formatTime(item.timestamp)}
          </p>
        )}
      </div>
    </li>
  );
}

function formatTime(iso: string): string {
  if (!iso) return "—";
  if (iso.length >= 19 && iso.includes("T")) return iso.slice(11, 19);
  try {
    return new Date(iso).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  } catch {
    return iso.slice(0, 8);
  }
}
