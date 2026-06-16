"use client";

import { Loader2, Sparkles } from "lucide-react";
import { isReleaseBuild } from "@/lib/releaseBuild";
import { floatTy } from "@/lib/floatTypography";
import { useMindTheme } from "../MindUiProvider";
import { useCognitiveSynthesis } from "@/hooks/useCognitiveSynthesis";
import { getCognitiveSourceMetaForRuntime } from "@/lib/cognitiveSource";
import { displayAction } from "@/lib/cognitiveDisplay";
import { useMindConnection } from "../MindConnectionProvider";
import { useMindOverview } from "@/cnexus-kernel";
import { useFloatRuntimeMonitorContext } from "./FloatRuntimeMonitorContext";

/** 悬浮窗展开区 — 数据源溯源 + 今日建议（只读） */
export function FloatingCognitiveHints() {
  const t = useMindTheme();
  const { effectiveMode } = useMindConnection();
  const { isLive, isWarming, isDemo } = useMindOverview();
  const monitor = useFloatRuntimeMonitorContext();
  const meta = getCognitiveSourceMetaForRuntime({
    effectiveMode,
    isLive,
    isWarming,
    isDemo,
    monitorPhase: monitor.phase,
  });
  const pollMs = 0;
  const { data, loading, refreshing, error } = useCognitiveSynthesis(pollMs, {
    requireOperational: true,
    monitorPhase: monitor.phase,
  });

  const actions = (data.top_actions?.length ? data.top_actions : data.actions).slice(0, 1);
  const hero = actions[0] ? displayAction(actions[0]) : null;

  const badgeBg =
    meta.badgeColor === "purple"
      ? t.purpleSoft
      : meta.badgeColor === "blue"
        ? t.blueSoft
        : t.orangeSoft;
  const badgeFg =
    meta.badgeColor === "purple"
      ? t.purple
      : meta.badgeColor === "blue"
        ? t.blue
        : t.orange;

  return (
    <div className="px-3 pt-2 pb-1.5 shrink-0 space-y-1.5 border-b" style={{ borderColor: t.border }} data-no-drag>
      <div className="flex items-center gap-1.5 min-w-0 flex-wrap">
        <span
          className={`${floatTy.caption} font-semibold px-2 py-0.5 rounded-full shrink-0`}
          style={{ backgroundColor: badgeBg, color: badgeFg }}
        >
          {meta.label}
        </span>
        {meta.isExample && !isReleaseBuild && (
          <span className={`${floatTy.caption} truncate`} style={{ color: t.textLight }}>
            非真实运行
          </span>
        )}
      </div>

      <div className="flex items-start gap-1.5 min-w-0">
        {loading || refreshing ? (
          <Loader2 className="w-3 h-3 mt-0.5 animate-spin shrink-0" style={{ color: t.blue }} />
        ) : (
          <Sparkles className="w-3 h-3 mt-0.5 shrink-0" style={{ color: t.blue }} />
        )}
        <p className={`${floatTy.body} min-w-0`} style={{ color: t.textMuted }}>
          <span style={{ color: t.blue }}>今日建议 · </span>
          {error
            ? error
            : hero?.title ?? (meta.isExample && !isReleaseBuild ? "以下为 UI 示例结论" : "使用对话或分析后，系统会压缩出可执行建议")}
        </p>
      </div>
    </div>
  );
}
