/** Tauri desktop bridge — float window sync, drag, position memory. */

import type { FloatStage } from "./floatingBarStorage";

export function isTauriDesktop(): boolean {
  if (typeof window === "undefined") return false;
  return Boolean((window as Window & { __TAURI__?: unknown }).__TAURI__);
}

const WINDOW_POS_KEY = "cnexus-tauri-window-position";

let tauriDesktopInitialized = false;
let tauriWinModule: typeof import("@tauri-apps/api/window") | null = null;
let tauriWin: Awaited<ReturnType<typeof import("@tauri-apps/api/window").getCurrentWindow>> | null =
  null;

function preloadTauriWindowModule(): void {
  if (!isTauriDesktop() || tauriWinModule) return;
  void import("@tauri-apps/api/window").then((mod) => {
    tauriWinModule = mod;
    if (!tauriWin) tauriWin = mod.getCurrentWindow();
  });
}

if (typeof window !== "undefined" && isTauriDesktop()) {
  preloadTauriWindowModule();
}

function installDesktopContextMenuGuard(): void {
  if (typeof window === "undefined") return;
  const blockNativeMenu = (event: Event) => {
    const target = event.target as HTMLElement | null;
    if (target?.closest("[data-allow-native-menu]")) return;
    // preventDefault only — must not stopPropagation or chat handlers never run
    event.preventDefault();
  };
  window.addEventListener("contextmenu", blockNativeMenu, { capture: true });
  document.addEventListener("contextmenu", blockNativeMenu, { capture: true });
  window.addEventListener(
    "mousedown",
    (event) => {
      if (event.button !== 2) return;
      blockNativeMenu(event);
    },
    { capture: true },
  );
}

export type WindowPosition = { x: number; y: number };

export function loadTauriWindowPosition(): WindowPosition | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(WINDOW_POS_KEY);
    if (!raw) return null;
    const p = JSON.parse(raw) as WindowPosition;
    if (typeof p.x === "number" && typeof p.y === "number") return p;
  } catch {
    /* ignore */
  }
  return null;
}

export function saveTauriWindowPosition(pos: WindowPosition): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(WINDOW_POS_KEY, JSON.stringify(pos));
}

async function ensureTauriFloatPosition(
  win: Awaited<ReturnType<typeof import("@tauri-apps/api/window").getCurrentWindow>>,
): Promise<void> {
  const { LogicalPosition } = await import("@tauri-apps/api/dpi");
  const { primaryMonitor } = await import("@tauri-apps/api/window");
  const monitor = await primaryMonitor();
  const scale = await win.scaleFactor();
  const inner = await win.innerSize();
  const w = inner.width / scale;
  const h = inner.height / scale;

  const clampToMonitor = (x: number, y: number): WindowPosition => {
    if (!monitor) return { x, y };
    const monSize = monitor.size;
    const monPos = monitor.position;
    const monW = monSize.width / scale;
    const monH = monSize.height / scale;
    const margin = 8;
    const maxX = monPos.x / scale + monW - w - margin;
    const maxY = monPos.y / scale + monH - h - margin;
    const minX = monPos.x / scale + margin;
    const minY = monPos.y / scale + margin;
    return {
      x: Math.min(Math.max(minX, x), Math.max(minX, maxX)),
      y: Math.min(Math.max(minY, y), Math.max(minY, maxY)),
    };
  };

  const saved = loadTauriWindowPosition();
  if (saved && !(saved.x === 0 && saved.y === 0)) {
    const clamped = clampToMonitor(saved.x, saved.y);
    await win.setPosition(new LogicalPosition(clamped.x, clamped.y)).catch(() => undefined);
    if (clamped.x !== saved.x || clamped.y !== saved.y) {
      saveTauriWindowPosition(clamped);
    }
    return;
  }
  if (monitor) {
    const monSize = monitor.size;
    const monPos = monitor.position;
    const monW = monSize.width / scale;
    const monH = monSize.height / scale;
    const margin = 24;
    const x = monPos.x / scale + monW - w - margin;
    const y = monPos.y / scale + monH - h - margin;
    const clamped = clampToMonitor(x, y);
    await win.setPosition(new LogicalPosition(clamped.x, clamped.y)).catch(() => undefined);
    saveTauriWindowPosition(clamped);
    return;
  }
  await win.center().catch(() => undefined);
}

export async function initTauriDesktop(): Promise<void> {
  if (!isTauriDesktop() || tauriDesktopInitialized) return;
  tauriDesktopInitialized = true;
  document.documentElement.classList.add("cnexus-desktop");
  document.body.classList.add("cnexus-desktop");
  installDesktopContextMenuGuard();
  const { getCurrentWindow } = await import("@tauri-apps/api/window");
  const win = getCurrentWindow();
  tauriWin = win;
  await ensureTauriFloatPosition(win);
  await win.onMoved(async () => {
    const pos = await win.outerPosition();
    const scale = await win.scaleFactor();
    saveTauriWindowPosition({ x: pos.x / scale, y: pos.y / scale });
  });
}

export async function syncTauriFloatWindow(stage: FloatStage, pinned: boolean): Promise<void> {
  if (!isTauriDesktop()) return;
  const { invoke } = await import("@tauri-apps/api/core");
  await invoke("sync_float_window", { stage, pinned });
}

/** Must run synchronously inside pointerdown — Windows rejects delayed startDragging. */
export function startTauriWindowDrag(): void {
  if (!isTauriDesktop()) return;
  if (!tauriWin && tauriWinModule) {
    tauriWin = tauriWinModule.getCurrentWindow();
  }
  const win = tauriWin;
  if (win) {
    void win.startDragging();
    return;
  }
  preloadTauriWindowModule();
  if (tauriWinModule) {
    tauriWin = tauriWinModule.getCurrentWindow();
    void tauriWin.startDragging();
  }
}

export async function listenTauriFloatToggle(onToggle: () => void): Promise<() => void> {
  if (!isTauriDesktop()) return () => undefined;
  const { listen } = await import("@tauri-apps/api/event");
  const unlisten = await listen("float-toggle", onToggle);
  return unlisten;
}

export async function openTauriDashboard(
  route = "/shell?layout=overview",
): Promise<void> {
  if (!isTauriDesktop()) return;
  const { invoke } = await import("@tauri-apps/api/core");
  await invoke("open_dashboard", { route });
}

export async function hideTauriFloatWindow(): Promise<void> {
  if (!isTauriDesktop()) return;
  const { invoke } = await import("@tauri-apps/api/core");
  await invoke("hide_float_window");
}

export function quitTauriApp(): void {
  if (!isTauriDesktop()) return;
  void import("@tauri-apps/api/core").then(({ invoke }) => invoke("quit_app"));
}

export async function openTauriSettings(): Promise<void> {
  if (!isTauriDesktop()) return;
  const { invoke } = await import("@tauri-apps/api/core");
  await invoke("emit_open_settings");
}

export async function listenTauriOpenSettings(onOpen: () => void): Promise<() => void> {
  if (!isTauriDesktop()) return () => undefined;
  const { listen } = await import("@tauri-apps/api/event");
  return listen("open-settings", onOpen);
}

export async function saveEnterpriseLicense(license: string): Promise<void> {
  if (!isTauriDesktop()) return;
  const { invoke } = await import("@tauri-apps/api/core");
  await invoke("save_enterprise_license", { license });
}

export async function listenRuntimeReady(onReady: () => void): Promise<() => void> {
  if (!isTauriDesktop()) return () => undefined;
  const { listen } = await import("@tauri-apps/api/event");
  return listen("cnexus:runtime-ready", onReady);
}

export async function listenRuntimeBootTimeout(onTimeout: () => void): Promise<() => void> {
  if (!isTauriDesktop()) return () => undefined;
  const { listen } = await import("@tauri-apps/api/event");
  return listen("cnexus:runtime-boot-timeout", onTimeout);
}

export async function listenRuntimeBundleMissing(onMissing: () => void): Promise<() => void> {
  if (!isTauriDesktop()) return () => undefined;
  const { listen } = await import("@tauri-apps/api/event");
  return listen("cnexus:runtime-bundle-missing", onMissing);
}

export async function listenRuntimeInitFailed(
  onFailed: (message: string) => void,
): Promise<() => void> {
  if (!isTauriDesktop()) return () => undefined;
  const { listen } = await import("@tauri-apps/api/event");
  return listen<string>("cnexus:runtime-init-failed", (event) => {
    const msg = typeof event.payload === "string" ? event.payload : "";
    onFailed(msg);
  });
}

export async function listenRuntimeSpawnFailed(
  onFailed: (message: string) => void,
): Promise<() => void> {
  if (!isTauriDesktop()) return () => undefined;
  const { listen } = await import("@tauri-apps/api/event");
  return listen<string>("cnexus:runtime-spawn-failed", (event) => {
    const msg = typeof event.payload === "string" ? event.payload : "";
    onFailed(msg);
  });
}

export async function getRuntimeBootFailure(): Promise<string | null> {
  if (!isTauriDesktop()) return null;
  const { invoke } = await import("@tauri-apps/api/core");
  return invoke<string | null>("get_runtime_boot_failure_command");
}

export type RuntimeWarmHealth = {
  init_error?: string | null;
  in_cooldown?: boolean;
  warming?: boolean;
};

export async function fetchRuntimeWarmHealth(): Promise<RuntimeWarmHealth | null> {
  try {
    const { getApiBase } = await import("./cnexusConfig");
    const res = await fetch(`${getApiBase()}/health`, {
      signal: AbortSignal.timeout(3000),
    });
    if (!res.ok) return null;
    const data = (await res.json()) as { runtime_warm?: RuntimeWarmHealth };
    return data.runtime_warm ?? null;
  } catch {
    return null;
  }
}

export async function grantUiRender(): Promise<void> {
  if (!isTauriDesktop()) return;
  const { invoke } = await import("@tauri-apps/api/core");
  await invoke("grant_ui_render_command");
}

export async function bootFallbackDemo(): Promise<void> {
  if (!isTauriDesktop()) return;
  const { invoke } = await import("@tauri-apps/api/core");
  await invoke("boot_fallback_demo_command");
}

export async function getBootState(): Promise<number> {
  if (!isTauriDesktop()) return 0;
  const { invoke } = await import("@tauri-apps/api/core");
  return invoke<number>("get_boot_state_command");
}

export async function isRuntimeBootTimedOut(): Promise<boolean> {
  if (!isTauriDesktop()) return false;
  const { invoke } = await import("@tauri-apps/api/core");
  return invoke<boolean>("runtime_boot_timed_out_command");
}

export async function revealTauriFloatWindow(): Promise<void> {
  if (!isTauriDesktop()) return;
  const { invoke } = await import("@tauri-apps/api/core");
  await invoke("reveal_float_window_command");
  const win = tauriWin ?? (await import("@tauri-apps/api/window")).getCurrentWindow();
  if (!tauriWin) tauriWin = win;
  await ensureTauriFloatPosition(win);
}

export async function showTauriFloatWindow(): Promise<void> {
  if (!isTauriDesktop()) return;
  const { invoke } = await import("@tauri-apps/api/core");
  await invoke("show_float_window");
}

export async function listenFloatRevealed(onRevealed: () => void): Promise<() => void> {
  if (!isTauriDesktop()) return () => undefined;
  const { listen } = await import("@tauri-apps/api/event");
  return listen("cnexus:float-revealed", onRevealed);
}

export async function listenDashboardNavigate(
  onNavigate: (path: string) => void,
): Promise<() => void> {
  if (!isTauriDesktop()) return () => undefined;
  const { listen } = await import("@tauri-apps/api/event");
  return listen<string>("cnexus:navigate-shell", (event) => {
    const path = event.payload;
    if (typeof path === "string" && path.startsWith("/")) {
      onNavigate(path);
    }
  });
}

export async function listenDashboardOpened(onOpen: () => void): Promise<() => void> {
  if (!isTauriDesktop()) return () => undefined;
  const { listen } = await import("@tauri-apps/api/event");
  return listen("cnexus:dashboard-opened", onOpen);
}

export async function listenBootSession(onSession: (id: string) => void): Promise<() => void> {
  if (!isTauriDesktop()) return () => undefined;
  const { listen } = await import("@tauri-apps/api/event");
  return listen<string>("cnexus:boot-session", (event) => {
    const id = event.payload;
    if (typeof id === "string" && id.length > 0) onSession(id);
  });
}
