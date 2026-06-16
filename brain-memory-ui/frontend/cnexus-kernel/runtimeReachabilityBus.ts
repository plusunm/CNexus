/**
 * Cross-window Runtime reachability sync (Tauri float + dashboard WebViews).
 * Each WebView has its own Zustand store; localStorage + Tauri events bridge them.
 */

const STORAGE_KEY = "cnexus-runtime-reachability";
const EVENT_NAME = "cnexus:runtime-reachability";
/** Match MindStore HEALTH_FAIL_GRACE_MS — stale snapshots are ignored. */
export const REACHABILITY_TTL_MS = 120_000;

export type RuntimeReachabilitySnapshot = {
  reachable: boolean;
  bootPhase: string | null;
  bootSessionId?: string | null;
  updatedAt: number;
};

function readRaw(): RuntimeReachabilitySnapshot | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as RuntimeReachabilitySnapshot;
    if (typeof parsed.reachable !== "boolean" || typeof parsed.updatedAt !== "number") {
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

export function loadRuntimeReachability(maxAgeMs = REACHABILITY_TTL_MS): RuntimeReachabilitySnapshot | null {
  const snap = readRaw();
  if (!snap) return null;
  if (Date.now() - snap.updatedAt > maxAgeMs) return null;
  return snap;
}

export function publishRuntimeReachability(
  patch: Partial<Pick<RuntimeReachabilitySnapshot, "reachable" | "bootPhase" | "bootSessionId">>,
): boolean {
  if (typeof window === "undefined") return false;
  const prev = readRaw();
  const next: RuntimeReachabilitySnapshot = {
    reachable: patch.reachable ?? prev?.reachable ?? false,
    bootPhase: patch.bootPhase !== undefined ? patch.bootPhase : (prev?.bootPhase ?? null),
    bootSessionId:
      patch.bootSessionId !== undefined ? patch.bootSessionId : (prev?.bootSessionId ?? null),
    updatedAt: Date.now(),
  };
  if (
    prev &&
    prev.reachable === next.reachable &&
    prev.bootPhase === next.bootPhase &&
    prev.bootSessionId === next.bootSessionId
  ) {
    return false;
  }
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  } catch {
    /* quota / private mode */
  }
  void import("@/lib/tauriDesktop")
    .then(({ isTauriDesktop }) => {
      if (!isTauriDesktop()) return;
      return import("@tauri-apps/api/event");
    })
    .then((mod) => {
      if (!mod) return;
      void mod.emit(EVENT_NAME, next);
    })
    .catch(() => undefined);
  return true;
}

export function clearRuntimeReachability(): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    /* ignore */
  }
}

export function subscribeRuntimeReachability(
  onUpdate: (snap: RuntimeReachabilitySnapshot) => void,
): () => void {
  if (typeof window === "undefined") return () => undefined;

  const onStorage = (event: StorageEvent) => {
    if (event.key !== STORAGE_KEY || !event.newValue) return;
    try {
      const snap = JSON.parse(event.newValue) as RuntimeReachabilitySnapshot;
      if (typeof snap.reachable === "boolean") onUpdate(snap);
    } catch {
      /* ignore */
    }
  };

  window.addEventListener("storage", onStorage);

  let unlistenTauri: (() => void) | undefined;
  void import("@/lib/tauriDesktop")
    .then(async ({ isTauriDesktop }) => {
      if (!isTauriDesktop()) return;
      const { listen } = await import("@tauri-apps/api/event");
      return listen<RuntimeReachabilitySnapshot>(EVENT_NAME, (event) => {
        const snap = event.payload;
        if (snap && typeof snap.reachable === "boolean") onUpdate(snap);
      });
    })
    .then((fn) => {
      unlistenTauri = fn;
    })
    .catch(() => undefined);

  return () => {
    window.removeEventListener("storage", onStorage);
    unlistenTauri?.();
  };
}
