"use client";

import Link from "next/link";
import { RefreshCw, Sparkles, Activity, Terminal, GitBranch, Coins, BookOpen } from "lucide-react";
import clsx from "clsx";
import { useMindOverview } from "@/cnexus-kernel";
import { useRuntimeStatus } from "@/hooks/useRuntimeStatus";
import type { OverviewView } from "@/cnexus-kernel/shellTypes";
import { MindModeSwitch } from "../MindModeSwitch";
import { LanguageProjectionSwitch, useLanguageProjection } from "../LanguageProjectionSwitch";
import { useMindConnection } from "../MindConnectionProvider";
import { useMindTheme } from "../MindUiProvider";
import { bi, biSection, navL, projectBiSection, projectLabel } from "@/lib/spine/labels";
import { CnexusAvatarIcon } from "../CnexusAvatarIcon";
import { OllamaConnectionBadge } from "../OllamaConnectionBadge";

const VIEW_DEFS: {
  id: OverviewView;
  labelKey?: keyof typeof navL;
  subKey?: keyof typeof navL;
  label?: { en: string; zh: string };
  sub?: { en: string; zh: string };
  href: string;
  icon: typeof Activity;
}[] = [
  {
    id: "learn",
    labelKey: "learnMode",
    subKey: "learnModeSub",
    href: "/shell?layout=overview",
    icon: BookOpen,
  },
  {
    id: "debugger",
    labelKey: "debuggerLegacy",
    subKey: "debuggerSub",
    href: "/shell?layout=overview&view=debugger",
    icon: Activity,
  },
  {
    id: "flow",
    labelKey: "flow",
    subKey: "flowSub",
    href: "/shell?layout=overview&view=flow",
    icon: GitBranch,
  },
  {
    id: "token",
    labelKey: "tokenObservatory",
    subKey: "tokenObservatorySub",
    href: "/shell?layout=overview&view=token",
    icon: Coins,
  },
  {
    id: "summary",
    labelKey: "summaryMode",
    subKey: "summaryModeSub",
    href: "/shell?layout=overview&view=summary",
    icon: Sparkles,
  },
  {
    id: "workbench",
    labelKey: "workbench",
    subKey: "workbenchSub",
    href: "/shell?layout=overview&view=workbench",
    icon: Terminal,
  },
];

type Props = {
  onRefresh: () => void;
  loading: boolean;
  activeView: OverviewView;
};

export function HomeSidebar({ onRefresh, loading, activeView }: Props) {
  const t = useMindTheme();
  const projection = useLanguageProjection();
  const { disconnect } = useMindConnection();
  const { overview, isDemo, isLive, isWarming } = useMindOverview();
  const runtimeStatus = useRuntimeStatus();

  const statusText = isDemo
    ? projectLabel(navL.demoMode, projection)
    : isLive
      ? projectLabel(navL.connectedRuntime, projection)
      : isWarming
        ? projectLabel(navL.warmingUp, projection)
        : projectLabel(navL.notConnected, projection);
  const statusColor = isDemo ? t.orange : isLive ? t.green : isWarming ? t.orange : t.red;

  return (
    <aside
      className="hidden lg:flex w-[220px] shrink-0 flex-col border-r px-4 py-5 gap-5 overflow-y-auto max-h-screen"
      style={{ borderColor: t.border, backgroundColor: t.surface }}
    >
      <div className="flex items-center gap-3">
        <CnexusAvatarIcon size={40} rounded="xl" />
        <div>
          <p className="text-sm font-semibold" style={{ color: t.text }}>
            CNexus
          </p>
          <p className="text-[11px]" style={{ color: t.textMuted }}>
            {projectLabel(navL.runtimeReader, projection)}
          </p>
        </div>
      </div>

      <div className="rounded-xl p-3 border" style={{ borderColor: t.border, backgroundColor: t.chatBg }}>
        <div className="flex items-center gap-1.5 min-w-0 mb-2 overflow-hidden">
          <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: statusColor }} />
          <span className="text-xs font-medium shrink-0" style={{ color: t.text }}>{statusText}</span>
          <span className="text-[10px] shrink-0" style={{ color: t.textLight }}>·</span>
          <OllamaConnectionBadge inline />
        </div>
        <p className="text-[11px] leading-relaxed" style={{ color: t.textMuted }}>
          {projectLabel(navL.systemHealth, projection)}:{" "}
          {isWarming
            ? runtimeStatus.label
            : overview.system.health_label}
        </p>
      </div>

      <div className="space-y-2">
        <p className="text-[10px] uppercase tracking-wider" style={{ color: t.textLight }}>
          {projectLabel(navL.views, projection)}
        </p>
        <div className="space-y-1">
          {VIEW_DEFS.map(({ id, labelKey, subKey, label: labelOverride, sub: subOverride, href, icon: Icon }) => {
            const active = activeView === id;
            const labelSrc = labelOverride ?? (labelKey ? navL[labelKey] : navL.learnMode);
            const subSrc = subOverride ?? (subKey ? navL[subKey] : navL.learnModeSub);
            const label = projectBiSection(labelSrc as { en: string; zh: string }, projection);
            const sub = projectBiSection(subSrc as { en: string; zh: string }, projection);
            return (
              <Link
                key={id}
                href={href}
                className={clsx(
                  "w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-left transition",
                  active ? "font-medium" : "opacity-80 hover:opacity-100",
                )}
                style={{
                  backgroundColor: active ? t.sidebarActive : "transparent",
                  color: active ? "#5eead4" : t.textMuted,
                  border: active ? `1px solid ${t.border}` : "1px solid transparent",
                }}
              >
                <Icon className="w-4 h-4 shrink-0" />
                <span className="min-w-0">
                  <span className="block text-xs leading-tight">{label}</span>
                  <span className="block text-[10px] leading-tight" style={{ color: t.textLight }}>{sub}</span>
                </span>
              </Link>
            );
          })}
        </div>
      </div>

      <div className="space-y-2">
        <p className="text-[10px] uppercase tracking-wider" style={{ color: t.textLight }}>
          {projectLabel(navL.quickActions, projection)}
        </p>
        <button
          type="button"
          onClick={onRefresh}
          disabled={loading}
          className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-medium disabled:opacity-50"
          style={{ backgroundColor: t.blue, color: "#fff" }}
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          {bi(navL.refresh)}
        </button>
        <button
          type="button"
          onClick={disconnect}
          className="w-full py-2 rounded-lg text-xs border"
          style={{ borderColor: t.border, color: t.textMuted }}
        >
          {bi(navL.switchDataSource)}
        </button>
      </div>

      <div className="mt-auto space-y-3">
        <div className="flex items-start gap-2 text-[11px]" style={{ color: t.textLight }}>
          <Sparkles className="w-3.5 h-3.5 shrink-0 mt-0.5" style={{ color: "#5eead4" }} />
          <span>
            {activeView === "learn"
              ? projectLabel(navL.learnHint, projection)
              : activeView === "summary"
                ? projectLabel(navL.summaryHint, projection)
              : activeView === "workbench"
                ? projectLabel(navL.workbenchHint, projection)
              : activeView === "debugger"
                ? projectLabel(navL.debuggerHint, projection)
              : activeView === "flow"
                ? projectLabel(navL.flowHint, projection)
              : activeView === "token"
                ? projectLabel(navL.tokenPageHint, projection)
                : projectLabel(navL.learnHint, projection)}
          </span>
        </div>
        <LanguageProjectionSwitch compact />
        <MindModeSwitch compact />
      </div>
    </aside>
  );
}
