export type FloatStage = "dock" | "bar" | "expanded";

export type FloatPanel = "chat" | "memory" | "upload";

export type FloatPosition = { x: number; y: number };

const KEYS = {
  position: "cnexus-float-position",
  stage: "cnexus-float-stage",
  panel: "cnexus-float-active-panel",
  pinned: "cnexus-float-pinned",
} as const;

export const FLOAT_DEFAULT_POSITION: FloatPosition = { x: 24, y: 24 };

export function loadFloatPosition(): FloatPosition {
  if (typeof window === "undefined") return FLOAT_DEFAULT_POSITION;
  try {
    const raw = localStorage.getItem(KEYS.position);
    if (!raw) return defaultCornerPosition();
    const parsed = JSON.parse(raw) as FloatPosition;
    if (typeof parsed.x === "number" && typeof parsed.y === "number") return parsed;
  } catch {
    /* ignore */
  }
  return defaultCornerPosition();
}

function defaultCornerPosition(): FloatPosition {
  if (typeof window === "undefined") return FLOAT_DEFAULT_POSITION;
  return { x: Math.max(16, window.innerWidth - 380), y: Math.max(16, window.innerHeight - 120) };
}

export function saveFloatPosition(pos: FloatPosition): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(KEYS.position, JSON.stringify(pos));
}

export function loadFloatStage(): FloatStage {
  if (typeof window === "undefined") return "bar";
  const v = localStorage.getItem(KEYS.stage);
  return v === "dock" || v === "expanded" ? v : "bar";
}

export function saveFloatStage(stage: FloatStage): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(KEYS.stage, stage);
}

export function loadFloatPanel(): FloatPanel | null {
  if (typeof window === "undefined") return null;
  const v = localStorage.getItem(KEYS.panel);
  return v === "chat" || v === "memory" || v === "upload" ? v : null;
}

export function saveFloatPanel(panel: FloatPanel | null): void {
  if (typeof window === "undefined") return;
  if (panel) localStorage.setItem(KEYS.panel, panel);
  else localStorage.removeItem(KEYS.panel);
}

export function loadFloatPinned(): boolean {
  if (typeof window === "undefined") return true;
  return localStorage.getItem(KEYS.pinned) !== "false";
}

export function saveFloatPinned(pinned: boolean): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(KEYS.pinned, pinned ? "true" : "false");
}
