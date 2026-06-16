"use client";

import { useMemo } from "react";
import { useOptionalFloatRuntimeMonitorContext } from "@/components/mind/floating/FloatRuntimeMonitorContext";
import { useLanguageProjection } from "@/components/mind/LanguageProjectionSwitch";
import { useMindStore } from "@/cnexus-kernel/MindStore";
import {
  extractBootStatus,
  formatRuntimeBootLabel,
  type RuntimeBootReason,
} from "@/lib/runtimeBootReason";
import type { RuntimeConnectionPhase } from "@/hooks/useFloatRuntimeMonitor";

export type RuntimeStatusSnapshot = {
  phase: RuntimeConnectionPhase;
  ready: boolean;
  reason: RuntimeBootReason;
  progress: number | null;
  label: string;
  runProbe: (() => Promise<RuntimeConnectionPhase>) | null;
};

/**
 * Read-only Runtime boot status from existing float monitor polls (no extra probes).
 * Workbench falls back to MindStore fields populated by `probeRuntimeFull`.
 */
export function useRuntimeStatus(): RuntimeStatusSnapshot {
  const monitor = useOptionalFloatRuntimeMonitorContext();
  const storeReason = useMindStore((s) => s.runtimeBootReason);
  const storeProgress = useMindStore((s) => s.runtimeBootProgress);
  const storeBootPhase = useMindStore((s) => s.runtimeBootPhase);
  const runtimeOperationalReady = useMindStore((s) => s.runtimeOperationalReady);
  const runtimeReady = useMindStore((s) => s.runtimeReady);
  const projection = useLanguageProjection();
  const locale = projection === "en" ? "en" : "zh";

  return useMemo(() => {
    const phase =
      monitor?.phase ??
      (runtimeOperationalReady ? "ready" : storeReason || runtimeReady ? "warming" : "offline");
    const reason = monitor?.reason ?? storeReason;
    const progress = monitor?.progress ?? storeProgress;
    const bootPhase = monitor?.bootPhase ?? storeBootPhase;
    const boot = extractBootStatus({
      ready: monitor?.ready ?? runtimeOperationalReady,
      reason,
      progress: progress ?? undefined,
      status: phase === "ready" ? "ready" : phase === "warming" ? "warming" : undefined,
      boot_phase: bootPhase ?? undefined,
    });
    const label =
      phase === "ready" || boot.ready
        ? formatRuntimeBootLabel(null, 100, locale)
        : formatRuntimeBootLabel(boot.reason, boot.progress, locale);

    return {
      phase,
      ready: boot.ready || phase === "ready",
      reason: boot.reason,
      progress: boot.progress,
      label,
      runProbe: monitor?.runProbe ?? null,
    };
  }, [
    locale,
    monitor?.bootPhase,
    monitor?.phase,
    monitor?.progress,
    monitor?.ready,
    monitor?.reason,
    monitor?.runProbe,
    runtimeOperationalReady,
    runtimeReady,
    storeBootPhase,
    storeProgress,
    storeReason,
  ]);
}

export { extractBootStatus, formatRuntimeBootLabel };
