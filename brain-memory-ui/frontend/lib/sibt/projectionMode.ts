/** SIBT v1 — frontend language projection mode (reduces bilingual UI clutter). */

export type LanguageProjectionMode = "both" | "en" | "zh";

const STORAGE_KEY = "cnexus.language_projection";

export function loadLanguageProjection(): LanguageProjectionMode {
  if (typeof window === "undefined") return "zh";
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw === "en" || raw === "zh" || raw === "both") return raw;
  } catch {
    /* ignore */
  }
  return "zh";
}

export function saveLanguageProjection(mode: LanguageProjectionMode): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(STORAGE_KEY, mode);
  } catch {
    /* ignore */
  }
}

export const PROJECTION_LABELS: Record<
  LanguageProjectionMode,
  { title: string; subtitle: string }
> = {
  both: { title: "双语", subtitle: "EN · 中文" },
  en: { title: "EN", subtitle: "English only" },
  zh: { title: "中文", subtitle: "仅中文" },
};
