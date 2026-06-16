import type { MindTheme } from "./types";
import { cognitiveTheme } from "./cognitiveTheme";

/** 悬浮条 — 半透明 Dark Cognitive，弱视觉干扰 */
export const floatTheme: MindTheme = {
  ...cognitiveTheme,
  mode: "float",
  bg: "rgba(11, 15, 26, 0.85)",
  surface: "rgba(26, 31, 44, 0.92)",
  border: "rgba(42, 49, 68, 0.75)",
  chatBg: "rgba(18, 24, 38, 0.95)",
  sidebarActive: "rgba(47, 107, 255, 0.2)",
  goalGlow: "0 0 20px rgba(47, 107, 255, 0.28)",
};
