import type { MindOverview } from "@/lib/runtimeTypes";

/** Canonical Product signals — Runtime output must map into this shape. */
export type MindGoalSignal = {
  title: string;
  progress: number;
  progressLabel: string;
  alignment?: number;
  priorityLabel?: string;
};

export type MindConflictSignal = {
  count: number;
  label: string;
  hasConflict: boolean;
};

export type MindHealthSignal = {
  score: number;
  label: string;
  source: "demo" | "runtime" | "fallback";
  connectionLabel: string;
};

export type MindMemorySignal = {
  itemCount: number;
  capacityPct: number;
  items: MindOverview["memory_items"];
};

export type MindSignals = {
  goal: MindGoalSignal;
  conflict: MindConflictSignal;
  health: MindHealthSignal;
  memory: MindMemorySignal;
};

const REQUIRED_TOP = [
  "schema_version",
  "generated_at",
  "cards",
  "feeds",
  "system",
  "chat_context",
  "memory_items",
] as const;

const REQUIRED_CARDS = ["goal", "identity", "belief", "focus"] as const;
const REQUIRED_FEEDS = ["episodic", "reflections", "changes"] as const;
const REQUIRED_SYSTEM = [
  "health_score",
  "health_label",
  "memory_capacity_pct",
  "governance_label",
  "last_update_ago",
] as const;

export function assertMindOverviewContract(
  overview: Record<string, unknown>,
  label = "MindOverview",
): void {
  for (const key of REQUIRED_TOP) {
    if (!(key in overview)) throw new Error(`${label}: missing top-level key "${key}"`);
  }
  const cards = overview.cards as Record<string, unknown>;
  if (!cards || typeof cards !== "object") throw new Error(`${label}: cards must be object`);
  for (const key of REQUIRED_CARDS) {
    if (!(key in cards)) throw new Error(`${label}: cards missing "${key}"`);
  }
  const feeds = overview.feeds as Record<string, unknown>;
  if (!feeds || typeof feeds !== "object") throw new Error(`${label}: feeds must be object`);
  for (const key of REQUIRED_FEEDS) {
    if (!(key in feeds)) throw new Error(`${label}: feeds missing "${key}"`);
  }
  const system = overview.system as Record<string, unknown>;
  if (!system || typeof system !== "object") throw new Error(`${label}: system must be object`);
  for (const key of REQUIRED_SYSTEM) {
    if (!(key in system)) throw new Error(`${label}: system missing "${key}"`);
  }
  const chatContext = overview.chat_context as Record<string, unknown>;
  if (!chatContext?.goal || !chatContext?.belief || !chatContext?.identity) {
    throw new Error(`${label}: chat_context must include goal, belief, identity`);
  }
  if (!Array.isArray(overview.memory_items)) {
    throw new Error(`${label}: memory_items must be array`);
  }
}

export function extractMindSignals(
  overview: MindOverview,
  source: "demo" | "runtime" | "fallback",
): MindSignals {
  const goalCard = overview.cards.goal;
  const conflicts = overview.system.governance_conflicts ?? 0;

  return {
    goal: {
      title: goalCard.title ?? "—",
      progress: goalCard.progress ?? 0,
      progressLabel: goalCard.progress_label ?? "—",
      alignment: goalCard.alignment,
      priorityLabel: goalCard.priority_label,
    },
    conflict: {
      count: conflicts,
      label: conflicts > 0 ? `${conflicts} 项冲突` : "无冲突",
      hasConflict: conflicts > 0,
    },
    health: {
      score: overview.system.health_score ?? 0,
      label: overview.system.health_label ?? "—",
      source,
      connectionLabel:
        source === "demo"
          ? "Demo"
          : source === "runtime"
            ? "Live"
            : "Fallback",
    },
    memory: {
      itemCount: overview.memory_items.length,
      capacityPct: overview.system.memory_capacity_pct ?? 0,
      items: overview.memory_items,
    },
  };
}

export function healthColor(label: string): string {
  if (label === "良好" || label === "Demo" || label === "OK") return "#22C55E";
  if (label === "降级" || label === "同步中" || label === "正在启动" || label === "正在初始化" || label === "Fallback")
    return "#F59E0B";
  if (label === "离线" || label === "临界") return "#EF4444";
  return "#6B7280";
}
