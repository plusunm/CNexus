/** Cognitive UI palette — attention hierarchy & psychological affordance. */

export const cognitiveColors = {
  /** Core goal / top-down direction (Goal Synthesis canonical) */
  coreGoal: "#2F6BFF",
  /** Meta-cognition, reflection, inner loop */
  reflection: "#8A5CFF",
  /** Consolidated, trusted memory */
  stableMemory: "#2ED47A",
  /** Awaiting synthesis / weak salience */
  pending: "#FFCC00",
  /** Goal conflict, drift, governance flag */
  conflict: "#FF4D4F",
  background: "#0B0F1A",
  panel: "#1A1F2C",
  textPrimary: "#E8ECF5",
  textSecondary: "#AAB4C5",
  textMeta: "#6B7280",
} as const;

export type MemoryLayer = "stable" | "reflection" | "pending" | "conflict";

export function memoryLayerColor(layer: MemoryLayer): string {
  switch (layer) {
    case "stable":
      return cognitiveColors.stableMemory;
    case "reflection":
      return cognitiveColors.reflection;
    case "pending":
      return cognitiveColors.pending;
    case "conflict":
      return cognitiveColors.conflict;
    default:
      return cognitiveColors.textSecondary;
  }
}
