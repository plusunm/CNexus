/** Client-side runtime conflict reporting — appended to runtime-conflict-monitor.log via API. */

import { cnexusProductApi } from "@/lib/api";

let lastClientPhase: "ready" | "warming" | "offline" | null = null;

export async function reportRuntimeConflict(
  event: string,
  fields: Record<string, unknown> = {},
  level: "info" | "warn" | "error" = "warn",
): Promise<void> {
  try {
    await cnexusProductApi.reportConflictLog({ event, level, ...fields });
  } catch {
    /* best-effort — never block UI */
  }
}

export function reportClientPhaseFlip(next: "ready" | "warming" | "offline"): void {
  const prev = lastClientPhase;
  lastClientPhase = next;
  if (prev === null || prev === next) return;
  if (prev === "ready" && next === "offline") {
    void reportRuntimeConflict("UI_PHASE_FLAP", { from: prev, to: next }, "warn");
  } else if (prev === "offline" && next === "ready") {
    void reportRuntimeConflict("UI_RECOVERED", { from: prev, to: next }, "info");
  }
}

export function conflictLogPathHint(): string {
  return "%LOCALAPPDATA%\\CNexus\\data\\runtime-conflict-monitor.log";
}
