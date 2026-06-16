"use client";

import { createContext, useContext, type ReactNode } from "react";
import {
  useFloatRuntimeMonitor,
  type RuntimeConnectionPhase,
} from "@/hooks/useFloatRuntimeMonitor";
import type { PollTier } from "@/lib/floatRuntimeMonitorConfig";

type MonitorValue = {
  phase: RuntimeConnectionPhase;
  tier: PollTier;
  bootPhase: string | null;
  ready: boolean;
  reason: string | null;
  progress: number | null;
  isLive: boolean;
  isWarming: boolean;
  isOffline: boolean;
  isChecking: boolean;
  runProbe: () => Promise<RuntimeConnectionPhase>;
};

const FloatRuntimeMonitorContext = createContext<MonitorValue | null>(null);

export function FloatRuntimeMonitorProvider({
  children,
  isExposed,
  boost,
}: {
  children: ReactNode;
  /** Bar/expanded visible — false when dock or tray-hidden */
  isExposed: boolean;
  /** Connection dialog open */
  boost?: boolean;
}) {
  const value = useFloatRuntimeMonitor({ isExposed, boost: boost ?? false });
  return (
    <FloatRuntimeMonitorContext.Provider value={value}>{children}</FloatRuntimeMonitorContext.Provider>
  );
}

export function useFloatRuntimeMonitorContext(): MonitorValue {
  const ctx = useContext(FloatRuntimeMonitorContext);
  if (!ctx) {
    throw new Error("useFloatRuntimeMonitorContext must be used within FloatRuntimeMonitorProvider");
  }
  return ctx;
}

export function useOptionalFloatRuntimeMonitorContext(): MonitorValue | null {
  return useContext(FloatRuntimeMonitorContext);
}
