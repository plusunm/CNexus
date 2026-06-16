"use client";

import { useMemo } from "react";
import { useMindConnection } from "./MindConnectionProvider";
import { extractMindSignals } from "./MindOverviewContract";
import { useMindStore } from "./MindStore";
import type { MindOverview } from "@/lib/runtimeTypes";
import type { MindSignals } from "./MindOverviewContract";
import type { EffectiveConnectionMode } from "./connectionMode";

/** Single hook for all UI — overview + contract signals only. */
export function useMindOverview() {
  const { effectiveMode, preference } = useMindConnection();
  const runtimeState = useMindStore((s) => s.runtimeState);
  const runtimeLogs = useMindStore((s) => s.runtimeLogs);
  const runtimeReady = useMindStore((s) => s.runtimeReady);
  const runtimeReachable = useMindStore((s) => s.runtimeReachable);
  const runtimeOperationalReady = useMindStore((s) => s.runtimeOperationalReady);
  const runtimeCapabilities = useMindStore((s) => s.runtimeCapabilities);
  const overview = useMindStore((s) => s.getOverview());

  const signals = useMemo(
    () => extractMindSignals(overview, effectiveMode),
    [overview, effectiveMode],
  );

  const isLive =
    effectiveMode === "runtime" && (runtimeOperationalReady || runtimeCapabilities.chat);
  const isWarming =
    effectiveMode === "runtime" && runtimeReachable && !isLive;
  const canWriteMemory =
    effectiveMode === "demo" ||
    (effectiveMode === "runtime" && (runtimeCapabilities.upload || runtimeReady));

  return {
    overview,
    signals,
    source: effectiveMode as EffectiveConnectionMode,
    preference,
    isDemo: effectiveMode === "demo",
    isLive,
    isWarming,
    canWriteMemory,
    isFallback: effectiveMode === "fallback",
    runtimeState: effectiveMode === "demo" ? null : runtimeState,
    runtimeLogs: effectiveMode === "demo" ? [] : runtimeLogs,
  };
}
export type { MindOverview, MindSignals };
