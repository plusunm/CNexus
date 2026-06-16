import type { EffectiveConnectionMode } from "@/cnexus-kernel";
import type { RuntimeConnectionPhase } from "@/hooks/useFloatRuntimeMonitor";

export type RuntimeConnectionDisplay = {
  /** Sidebar / float subtitle */
  connectionLabel: string;
  /** Badge text (float hints, source bar) */
  badgeLabel: string;
  badgeColor: "purple" | "blue" | "orange" | "red";
  /** Same gate as memory ingest + chat */
  canUseRuntimeApi: boolean;
  phase: "demo" | "live" | "warming" | "offline" | "fallback";
};

export function resolveRuntimeConnectionDisplay(input: {
  effectiveMode: EffectiveConnectionMode;
  isLive: boolean;
  isWarming: boolean;
  isDemo: boolean;
  monitorPhase?: RuntimeConnectionPhase | null;
}): RuntimeConnectionDisplay {
  const { effectiveMode, isLive, isWarming, isDemo, monitorPhase } = input;

  if (isDemo || effectiveMode === "demo") {
    return {
      connectionLabel: "演示模式",
      badgeLabel: "演示示例",
      badgeColor: "purple",
      canUseRuntimeApi: true,
      phase: "demo",
    };
  }

  if (effectiveMode === "fallback") {
    return {
      connectionLabel: "未连接",
      badgeLabel: "未连接 Runtime",
      badgeColor: "orange",
      canUseRuntimeApi: false,
      phase: "fallback",
    };
  }

  const monitorWarming =
    monitorPhase === "warming" || monitorPhase === "checking" || monitorPhase === "offline";
  const monitorReady = monitorPhase === "ready";

  if (isLive && (!monitorPhase || monitorReady)) {
    return {
      connectionLabel: "上线",
      badgeLabel: "Runtime 实时",
      badgeColor: "blue",
      canUseRuntimeApi: true,
      phase: "live",
    };
  }

  if (isWarming || monitorWarming || (isLive && monitorWarming)) {
    return {
      connectionLabel: "正在启动",
      badgeLabel: "Runtime 正在启动",
      badgeColor: "orange",
      canUseRuntimeApi: false,
      phase: "warming",
    };
  }

  return {
    connectionLabel: "未连接",
    badgeLabel: "未连接 Runtime",
    badgeColor: "orange",
    canUseRuntimeApi: false,
    phase: "offline",
  };
}
