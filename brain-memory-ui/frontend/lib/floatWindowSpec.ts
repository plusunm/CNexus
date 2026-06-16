import type { FloatStage } from "./floatingBarStorage";

/** Single source of truth — keep in sync with src-tauri/src/lib.rs `float_size`. */
export const FLOAT_LAYOUT = {
  dock: { width: 56, height: 56 },
  bar: { width: 360, height: 228 },
  expanded: { width: 440, height: 640 },
} as const;

export const FLOAT_EDGE_SNAP_PX = 12;
export const FLOAT_VIEWPORT_MARGIN = 8;

export function floatShellWidth(stage: FloatStage): number {
  if (stage === "dock") return FLOAT_LAYOUT.dock.width;
  if (stage === "expanded") return FLOAT_LAYOUT.expanded.width;
  return FLOAT_LAYOUT.bar.width;
}

export function floatShellHeight(stage: FloatStage): number {
  if (stage === "dock") return FLOAT_LAYOUT.dock.height;
  if (stage === "expanded") return FLOAT_LAYOUT.expanded.height;
  return FLOAT_LAYOUT.bar.height;
}

export function snapFloatPosition(
  pos: { x: number; y: number },
  width: number,
  height: number,
): { x: number; y: number } {
  if (typeof window === "undefined") return pos;
  const margin = FLOAT_VIEWPORT_MARGIN;
  const snap = FLOAT_EDGE_SNAP_PX;
  const maxX = Math.max(margin, window.innerWidth - width - margin);
  const maxY = Math.max(margin, window.innerHeight - height - margin);
  let x = Math.min(Math.max(margin, pos.x), maxX);
  let y = Math.min(Math.max(margin, pos.y), maxY);
  if (x - margin <= snap) x = margin;
  if (maxX - x <= snap) x = maxX;
  if (y - margin <= snap) y = margin;
  if (maxY - y <= snap) y = maxY;
  return { x, y };
}

export function clampFloatPosition(
  x: number,
  y: number,
  width: number,
  height: number,
): { x: number; y: number } {
  if (typeof window === "undefined") return { x, y };
  const margin = FLOAT_VIEWPORT_MARGIN;
  const maxX = Math.max(margin, window.innerWidth - width - margin);
  const maxY = Math.max(margin, window.innerHeight - height - margin);
  return {
    x: Math.min(Math.max(margin, x), maxX),
    y: Math.min(Math.max(margin, y), maxY),
  };
}

/** Alt+Shift+M: Web = dock↔bar/expanded→dock; Tauri = reveal → dock → hide ladder. */
export const FLOAT_SHORTCUT_HINT_WEB = "Alt+Shift+M 收起/展开 · 拖动标题栏";
export const FLOAT_SHORTCUT_HINT_TAURI =
  "Alt+Shift+M 逐级收起（展开→条→Dock→托盘）· 再按显示";
