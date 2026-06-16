/** Unified theme shape — overview (mockup) vs cognitive (attention gravity). */

export type MindUiMode = "overview" | "cognitive" | "float";

export type MindTheme = {
  mode: MindUiMode;
  bg: string;
  surface: string;
  border: string;
  text: string;
  textMuted: string;
  textLight: string;
  /** Goal / system truth */
  blue: string;
  blueSoft: string;
  /** Meta-cognition / reflection */
  purple: string;
  purpleSoft: string;
  /** Resolved memory / belief locked */
  green: string;
  greenSoft: string;
  /** Pending synthesis / focus */
  orange: string;
  orangeSoft: string;
  /** Structural conflict */
  red: string;
  sidebarActive: string;
  /** Cognitive-only */
  goalGlow: string;
  chatBg: string;
  fontSans: string;
  fontMono: string;
};

export const MODE_LABELS: Record<MindUiMode, { title: string; subtitle: string }> = {
  overview: {
    title: "Home 模式",
    subtitle: "认知压缩器 · 决策输出为主视图",
  },
  cognitive: {
    title: "认知模式",
    subtitle: "注意力引力场 · Dark Cognitive",
  },
  float: {
    title: "悬浮模式",
    subtitle: "轻量悬浮条 · 随时唤起",
  },
};

const STORAGE_KEY = "cnexus-mind-ui-mode";

export function loadMindUiMode(): MindUiMode {
  if (typeof window === "undefined") return "overview";
  const v = localStorage.getItem(STORAGE_KEY);
  if (v === "cognitive" || v === "float") return v;
  return "overview";
}

export function saveMindUiMode(mode: MindUiMode): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(STORAGE_KEY, mode);
}
