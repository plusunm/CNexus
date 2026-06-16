"use client";

import { useEffect } from "react";
import { bi, bootL } from "@/lib/spine/labels";
import {
  BOOT_STATE_NAMES,
  emitBootHeartbeat,
  type BootShellPhase,
} from "@/lib/bootProtocol";

type Props = {
  phase: BootShellPhase;
  rustBootState?: number;
  detail?: string;
};

const PHASE_LABEL: Record<BootShellPhase, string> = {
  config: bi(bootL.config),
  hydrating: bi(bootL.hydrating),
  sync: bi(bootL.sync),
  "float-pending": bi(bootL.floatPending),
  float: bi(bootL.float),
  degraded: bi(bootL.degraded),
};

/** Invariant A — root is never empty; visible heartbeat UI in Tauri float window. */
export function BootShell({ phase, rustBootState = 0, detail }: Props) {
  useEffect(() => {
    void emitBootHeartbeat({
      phase,
      rustBootState,
      mounted: true,
      detail,
    });
  }, [phase, rustBootState, detail]);

  const stateName = BOOT_STATE_NAMES[rustBootState] ?? "Unknown";

  return (
    <div
      className="w-full h-full min-h-[228px] flex flex-col items-center justify-center gap-2 select-none"
      data-cnexus-boot-shell={phase}
      data-cnexus-boot-state={rustBootState}
      style={{
        background: "linear-gradient(160deg, #1e1e24 0%, #121216 100%)",
        color: "#a1a1aa",
        fontFamily: "system-ui, sans-serif",
      }}
    >
      <div
        className="w-8 h-8 rounded-full border-2 border-t-transparent animate-spin"
        style={{ borderColor: "#6366f1", borderTopColor: "transparent" }}
        aria-hidden
      />
      <p className="text-sm font-medium text-zinc-300">CNexus</p>
      <p className="text-xs text-zinc-500">
        {detail ?? PHASE_LABEL[phase]} · {stateName}
      </p>
    </div>
  );
}
