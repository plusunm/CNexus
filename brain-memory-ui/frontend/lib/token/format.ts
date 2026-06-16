import type { CostLevel } from "./types";

export const COST_COLOR: Record<CostLevel, string> = {
  spike: "#ef4444",
  high: "#f97316",
  mid: "#94a3b8",
  low: "#22c55e",
};

export const SOURCE_COLOR: Record<string, string> = {
  llm_generate: "#60a5fa",
  recall: "#5eead4",
  explain_v3: "#c084fc",
  causal_expand: "#fbbf24",
  control_decision: "#fb7185",
  identity_hash: "#a78bfa",
};

export const PHASE_COLOR: Record<string, string> = {
  EXEC: "#60a5fa",
  EXPLAIN: "#c084fc",
  RECALL: "#5eead4",
  CONTROL: "#fb7185",
};

export function edgeWeightColor(weight: number): string {
  if (weight > 2.5) return "#ef4444";
  if (weight >= 1.5) return "#f97316";
  return "#94a3b8";
}

export function costBarWidth(cost: number, max: number): string {
  if (max <= 0) return "4%";
  return `${Math.max(4, Math.min(100, (cost / max) * 100))}%`;
}

export function groupByMode<T extends { mode?: string; source?: string; total: number }>(rows: T[]) {
  const map: Record<string, number> = {};
  for (const d of rows) {
    const key = d.mode || d.source || "unknown";
    map[key] = (map[key] || 0) + d.total;
  }
  return Object.entries(map)
    .map(([mode, totalTokens]) => ({ mode, totalTokens }))
    .sort((a, b) => b.totalTokens - a.totalTokens);
}

export function groupByPhase(rows: { phase?: string; total: number }[]) {
  const map: Record<string, number> = {};
  for (const d of rows) {
    const key = d.phase || "EXEC";
    map[key] = (map[key] || 0) + d.total;
  }
  return Object.entries(map).sort((a, b) => b[1] - a[1]);
}
