import type { EffectiveConnectionMode } from "@/cnexus-kernel";
import {
  resolveRuntimeConnectionDisplay,
  type RuntimeConnectionDisplay,
} from "@/lib/runtimeConnection";

export type CognitiveSourceMeta = {
  mode: EffectiveConnectionMode;
  label: string;
  description: string;
  badgeColor: "purple" | "blue" | "orange" | "red";
  isLive: boolean;
  isExample: boolean;
};

export function getCognitiveSourceMeta(
  mode: EffectiveConnectionMode,
  connection?: Pick<RuntimeConnectionDisplay, "badgeLabel" | "badgeColor" | "phase">,
): CognitiveSourceMeta {
  switch (mode) {
    case "demo":
      return {
        mode,
        label: "演示示例",
        description: "以下为 UI 示例数据，用于预览布局与交互，不代表真实运行结论",
        badgeColor: "purple",
        isLive: false,
        isExample: true,
      };
    case "runtime":
      return {
        mode,
        label: connection?.badgeLabel ?? "Runtime 实时",
        description:
          connection?.phase === "warming"
            ? "Runtime 正在启动，对话与导入将在完全就绪后可用"
            : connection?.phase === "live"
              ? "来自本地 Runtime 的运行历史压缩，随使用更新"
              : "正在连接本地 Runtime（127.0.0.1:8000）",
        badgeColor: connection?.badgeColor ?? "blue",
        isLive: connection?.phase === "live",
        isExample: false,
      };
    case "fallback":
      return {
        mode,
        label: "未连接 Runtime",
        description: "Runtime API 不可达 — 请在本机启动 Runtime（127.0.0.1:8000）",
        badgeColor: "orange",
        isLive: false,
        isExample: false,
      };
  }
}

export function getCognitiveSourceMetaForRuntime(input: {
  effectiveMode: EffectiveConnectionMode;
  isLive: boolean;
  isWarming: boolean;
  isDemo: boolean;
  monitorPhase?: import("@/hooks/useFloatRuntimeMonitor").RuntimeConnectionPhase | null;
}): CognitiveSourceMeta {
  const display = resolveRuntimeConnectionDisplay(input);
  return getCognitiveSourceMeta(input.effectiveMode, display);
}

export function formatGeneratedAt(iso?: string): string {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    return d.toLocaleString("zh-CN", {
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso.slice(0, 16);
  }
}
