/**
 * BootShell protocol — JS heartbeat layer (Invariant A observability).
 * Rust boot_state = source of truth; this layer mirrors + reports TTFV.
 */

import { isTauriDesktop } from "@/lib/tauriDesktop";

/** UI presentation phase (does not replace Rust BootState). */
export type BootShellPhase =
  | "config"
  | "hydrating"
  | "sync"
  | "float-pending"
  | "float"
  | "degraded";

export type BootHeartbeat = {
  phase: BootShellPhase;
  rustBootState: number;
  mounted: boolean;
  ts: number;
  detail?: string;
};

export const BOOT_STATE_NAMES: Record<number, string> = {
  0: "Init",
  1: "RuntimeSpawning",
  2: "RuntimeReady",
  3: "UiRenderAllowed",
  4: "FloatWindowShown",
};

export function bootPhaseFromRustState(
  rustState: number,
  opts?: { degraded?: boolean; floatContent?: boolean },
): BootShellPhase {
  if (opts?.degraded) return "degraded";
  if (opts?.floatContent || rustState >= 4) return "float";
  if (rustState >= 3) return "float-pending";
  if (rustState >= 1) return "sync";
  return "hydrating";
}

let firstHeartbeatMs: number | null = null;

export function getBootShellTtfvMs(): number | null {
  return firstHeartbeatMs;
}

/** Emit heartbeat to DOM (tests) + Rust (persistence / smoke). */
export async function emitBootHeartbeat(
  payload: Omit<BootHeartbeat, "ts">,
): Promise<void> {
  const heartbeat: BootHeartbeat = { ...payload, ts: Date.now() };
  if (firstHeartbeatMs === null && payload.mounted) {
    firstHeartbeatMs = heartbeat.ts;
  }

  if (typeof window !== "undefined") {
    window.dispatchEvent(
      new CustomEvent("cnexus:ui-heartbeat", { detail: heartbeat }),
    );
  }

  if (!isTauriDesktop()) return;

  try {
    const { invoke } = await import("@tauri-apps/api/core");
    await invoke("report_ui_heartbeat_command", { payload: heartbeat });
  } catch {
    /* offline / dev web */
  }
}

export function parseBootHeartbeat(raw: unknown): BootHeartbeat | null {
  if (!raw || typeof raw !== "object") return null;
  const o = raw as Record<string, unknown>;
  const phase = o.phase;
  if (typeof phase !== "string") return null;
  if (typeof o.rustBootState !== "number") return null;
  if (typeof o.mounted !== "boolean") return null;
  if (typeof o.ts !== "number") return null;
  return {
    phase: phase as BootShellPhase,
    rustBootState: o.rustBootState,
    mounted: o.mounted,
    ts: o.ts,
    detail: typeof o.detail === "string" ? o.detail : undefined,
  };
}
