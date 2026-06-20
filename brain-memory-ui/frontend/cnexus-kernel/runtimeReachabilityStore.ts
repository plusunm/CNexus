/**
 * Synchronous external store for cross-window Runtime reachability.
 * Use with useSyncExternalStore — avoids React useEffect hydrate race.
 */

import {
  clearRuntimeReachability,
  loadRuntimeReachability,
  publishRuntimeReachability,
  subscribeRuntimeReachability,
  type RuntimeReachabilitySnapshot,
} from "./runtimeReachabilityBus";

export type ConnectionPhase = "idle" | "pending" | "booting" | "ready" | "failed";

export type RuntimeReachabilityView = {
  reachable: boolean;
  bootPhase: string | null;
  phase: ConnectionPhase;
  bootSessionId: string | null;
  source: "default" | "snapshot" | "probe" | "bus" | "ws";
  updatedAt: number;
};

const BOOT_SESSION_KEY = "cnexus-boot-session";
const PENDING_GRACE_MS = 3_000;

let currentBootSessionId: string | null = null;
let current: RuntimeReachabilityView = {
  reachable: false,
  bootPhase: null,
  phase: "idle",
  bootSessionId: null,
  source: "default",
  updatedAt: 0,
};

const listeners = new Set<() => void>();
let busSubscribed = false;
let pendingTimer: number | undefined;

function emit() {
  listeners.forEach((l) => l());
}

function schedulePendingResolve() {
  if (pendingTimer) window.clearTimeout(pendingTimer);
  pendingTimer = window.setTimeout(() => {
    pendingTimer = undefined;
    if (current.phase === "pending" && current.reachable) {
      current = { ...current, phase: "ready", updatedAt: Date.now() };
      emit();
    }
  }, PENDING_GRACE_MS);
}

export function getBootSessionId(): string {
  if (currentBootSessionId) return currentBootSessionId;
  if (typeof window !== "undefined") {
    const fromWin = (window as Window & { __CNEXUS_BOOT_SESSION__?: string })
      .__CNEXUS_BOOT_SESSION__;
    if (fromWin) {
      currentBootSessionId = fromWin;
      return fromWin;
    }
    try {
      const stored = sessionStorage.getItem(BOOT_SESSION_KEY);
      if (stored) {
        currentBootSessionId = stored;
        return stored;
      }
    } catch {
      /* ignore */
    }
  }
  const id = `boot_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
  currentBootSessionId = id;
  if (typeof window !== "undefined") {
    (window as Window & { __CNEXUS_BOOT_SESSION__?: string }).__CNEXUS_BOOT_SESSION__ = id;
    try {
      sessionStorage.setItem(BOOT_SESSION_KEY, id);
    } catch {
      /* ignore */
    }
  }
  return id;
}

export function setBootSessionId(id: string): void {
  if (!id) return;
  currentBootSessionId = id;
  if (typeof window !== "undefined") {
    (window as Window & { __CNEXUS_BOOT_SESSION__?: string }).__CNEXUS_BOOT_SESSION__ = id;
    try {
      sessionStorage.setItem(BOOT_SESSION_KEY, id);
    } catch {
      /* ignore */
    }
  }
}

export function getRuntimeReachabilitySnapshot(): RuntimeReachabilityView {
  return current;
}

function reachabilityViewKey(
  view: Pick<RuntimeReachabilityView, "reachable" | "bootPhase" | "phase" | "bootSessionId">,
): string {
  return `${view.reachable}|${view.phase}|${view.bootPhase ?? ""}|${view.bootSessionId ?? ""}`;
}

export function setRuntimeReachability(
  patch: Partial<
    Pick<RuntimeReachabilityView, "reachable" | "bootPhase" | "phase" | "source">
  >,
): void {
  const nextPhase =
    patch.phase ??
    (patch.reachable === false
      ? "failed"
      : patch.reachable
        ? current.phase === "failed"
          ? "pending"
          : current.phase === "idle"
            ? "pending"
            : current.phase
        : current.phase);

  const next: RuntimeReachabilityView = {
    ...current,
    ...patch,
    phase: nextPhase,
    bootSessionId: getBootSessionId(),
    updatedAt: Date.now(),
  };

  if (reachabilityViewKey(next) === reachabilityViewKey(current)) return;

  current = next;

  if (current.reachable) {
    publishRuntimeReachability({
      reachable: true,
      bootPhase: current.bootPhase,
      bootSessionId: current.bootSessionId,
    });
    if (current.phase === "pending") schedulePendingResolve();
  } else if (patch.reachable === false) {
    clearRuntimeReachability();
  }

  emit();
}

export function markRuntimeReachabilityBooting(bootPhase?: string | null): void {
  setRuntimeReachability({
    reachable: true,
    bootPhase: bootPhase ?? current.bootPhase,
    phase: "booting",
    source: "probe",
  });
}

export function markRuntimeReachabilityReady(bootPhase?: string | null): void {
  setRuntimeReachability({
    reachable: true,
    bootPhase: bootPhase ?? current.bootPhase,
    phase: "ready",
    source: "probe",
  });
}

export function markRuntimeReachabilityFailed(): void {
  setRuntimeReachability({
    reachable: false,
    phase: "failed",
    source: "probe",
  });
}

export function bootstrapRuntimeReachabilityFromDisk(): void {
  ensureRuntimeReachabilityBus();
  // cache layer exists only for display hint — NEVER as truth source for reachable
  // MUST be overwritten by actual probe result
  const sessionId = getBootSessionId();
  const snap = loadRuntimeReachability();
  if (!snap?.reachable) return;
  if (snap.bootSessionId && snap.bootSessionId !== sessionId) return;

  // Snapshot is only used for optimistic UI, not for enabling chat
  if (current.phase === "idle") {
    current = {
      reachable: false, // explicitly NOT reachable until probe confirms
      bootPhase: snap.bootPhase,
      phase: "pending",
      bootSessionId: sessionId,
      source: "snapshot",
      updatedAt: snap.updatedAt,
    };
    emit();
  }
}

function applyBusSnapshot(snap: RuntimeReachabilitySnapshot) {
  if (!snap.reachable) return;
  const sessionId = getBootSessionId();
  if (snap.bootSessionId && snap.bootSessionId !== sessionId) return;

  const next: RuntimeReachabilityView = {
    ...current,
    reachable: true,
    bootPhase: snap.bootPhase ?? current.bootPhase,
    phase: current.phase === "failed" ? "pending" : current.phase === "ready" ? "ready" : "pending",
    bootSessionId: sessionId,
    source: "bus",
    updatedAt: snap.updatedAt,
  };
  if (reachabilityViewKey(next) === reachabilityViewKey(current)) return;

  current = next;
  if (current.phase === "pending") schedulePendingResolve();
  emit();
}

export function ensureRuntimeReachabilityBus(): void {
  if (busSubscribed) return;
  busSubscribed = true;
  subscribeRuntimeReachability(applyBusSnapshot);
}

export function subscribeRuntimeReachabilityStore(onStoreChange: () => void): () => void {
  ensureRuntimeReachabilityBus();
  listeners.add(onStoreChange);
  return () => listeners.delete(onStoreChange);
}

/** Sync Zustand MindStore when external store updates (MindRuntimeBridge). */
export function applyExternalReachabilityToMindStore(
  setReachable: (v: boolean) => void,
  setBootPhase: (phase: string) => void,
): void {
  if (!current.reachable) return;
  setReachable(true);
  if (current.bootPhase) setBootPhase(current.bootPhase);
}

export function syncRuntimeReachabilityFromMindStore(
  reachable: boolean,
  bootPhase: string | null,
  source: RuntimeReachabilityView["source"] = "ws",
): void {
  if (!reachable) return;
  setRuntimeReachability({
    reachable: true,
    bootPhase,
    phase: current.phase === "failed" ? "pending" : "ready",
    source,
  });
}

export function resetRuntimeReachabilityStore(): void {
  if (pendingTimer) window.clearTimeout(pendingTimer);
  pendingTimer = undefined;
  clearRuntimeReachability();
  current = {
    reachable: false,
    bootPhase: null,
    phase: "idle",
    bootSessionId: getBootSessionId(),
    source: "default",
    updatedAt: Date.now(),
  };
  emit();
}
