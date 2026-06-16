/**
 * CNexus Kernel — connection preference & effective mode.
 * UI only selects demo | runtime; fallback is kernel-internal.
 */

export type ConnectionPreference = "demo" | "runtime";

/** Effective data source — UI reads this, never checks API directly. */
export type EffectiveConnectionMode = "demo" | "runtime" | "fallback";

const STORAGE_KEY = "cnexus-connection-mode";

export function loadConnectionPreference(): ConnectionPreference | null {
  if (typeof window === "undefined") return null;
  const v = localStorage.getItem(STORAGE_KEY);
  if (v === "demo" || v === "runtime") return v;
  return null;
}

export function saveConnectionPreference(mode: ConnectionPreference): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(STORAGE_KEY, mode);
}

export function clearConnectionPreference(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(STORAGE_KEY);
}

export type ResolveEffectiveModeOptions = {
  /** Desktop float defaults to Live — null preference is fallback, not Demo. */
  tauriDesktop?: boolean;
};

/** Kernel-only: map user preference + runtime reachability → effective mode. */
export function resolveEffectiveMode(
  preference: ConnectionPreference | null,
  runtimeReachable: boolean,
  options?: ResolveEffectiveModeOptions,
): EffectiveConnectionMode {
  if (preference === "runtime") return runtimeReachable ? "runtime" : "fallback";
  if (preference === "demo") return "demo";
  if (options?.tauriDesktop) return runtimeReachable ? "runtime" : "fallback";
  return "demo";
}

export const CONNECTION_LABELS: Record<
  ConnectionPreference,
  { title: string; subtitle: string; badge: string }
> = {
  demo: {
    title: "CNexus Demo 模式",
    subtitle: "完全离线 · 展示 UI 与交互 · 无后端依赖",
    badge: "Demo",
  },
  runtime: {
    title: "连接 Runtime",
    subtitle: "Live 绑定 · REST /v1/mind/overview + WS /ws/state",
    badge: "Runtime",
  },
};

export const EFFECTIVE_MODE_LABELS: Record<EffectiveConnectionMode, string> = {
  demo: "Demo",
  runtime: "Live",
  fallback: "Fallback",
};

/** @deprecated use ConnectionPreference */
export type MindConnectionMode = ConnectionPreference;

export const loadConnectionMode = loadConnectionPreference;
export const saveConnectionMode = saveConnectionPreference;
export const clearConnectionMode = clearConnectionPreference;
