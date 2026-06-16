import type { MindOverview } from "@/lib/runtimeTypes";
import type { LexemeTag } from "@/lib/memoryLexicon";

export type FactorEdgeKind = "chain";

export type FactorNode = {
  id: string;
  text: string;
  tag: LexemeTag;
  weight: number;
  index: number;
};

export type FactorEdge = {
  id: string;
  from: string;
  to: string;
  kind: FactorEdgeKind;
  strength: number;
};

export type FactorGraph = {
  nodes: FactorNode[];
  edges: FactorEdge[];
  brainRadius: number;
  density: number;
};

function tagWeight(tag: string): number {
  if (tag === "goal") return 1.3;
  if (tag === "belief") return 1.15;
  if (tag === "identity") return 1.1;
  if (tag === "insight") return 1.05;
  if (tag === "episode") return 0.95;
  return 1;
}

/** 仅从数据库 memory_items 构建因子链；无数据时用概览卡片/上下文作演示节点 */
export function buildFactorGraph(overview: MindOverview): FactorGraph {
  const seen = new Set<string>();
  const nodes: FactorNode[] = [];

  const pushNode = (text: string | undefined, tag: LexemeTag, id?: string) => {
    if (!text) return;
    const t = text.trim();
    if (!t || t === "—" || seen.has(t)) return;
    seen.add(t);
    nodes.push({
      id: id ?? `seed-${nodes.length}`,
      text: t,
      tag,
      weight: tagWeight(tag),
      index: nodes.length,
    });
  };

  for (const item of overview.memory_items) {
    pushNode(item.title, (item.tag as LexemeTag) || "term", item.id);
  }

  if (nodes.length === 0) {
    pushNode(overview.chat_context.goal, "goal");
    pushNode(overview.chat_context.belief, "belief");
    pushNode(overview.chat_context.identity, "identity");
    pushNode(overview.cards.goal.title, "goal", "card-goal");
    pushNode(overview.cards.belief.content, "belief", "card-belief");
    pushNode(overview.cards.identity.summary, "identity", "card-identity");
    pushNode(overview.cards.focus.title, "insight", "card-focus");
    pushNode(overview.personality?.emotion.primary_emotion_label, "insight", "emotion");
    const topIntent = overview.intent?.goals?.[0]?.description;
    pushNode(topIntent, "goal", "intent-top");
    for (const ep of overview.feeds.episodic.slice(0, 4)) {
      pushNode(ep.text, "episode", `ep-${ep.text.slice(0, 12)}`);
    }
  }

  const edges: FactorEdge[] = [];
  for (let i = 0; i < nodes.length - 1; i += 1) {
    edges.push({
      id: `chain-${nodes[i].id}-${nodes[i + 1].id}`,
      from: nodes[i].id,
      to: nodes[i + 1].id,
      kind: "chain",
      strength: 0.92,
    });
  }

  const n = nodes.length;
  const brainRadius = n <= 1 ? 56 : 64 + Math.sqrt(n) * 22;
  const density = Math.min(1, n / 20);

  return { nodes, edges, brainRadius, density };
}

export const FACTOR_TAG_LABEL: Record<LexemeTag, string> = {
  goal: "目标因子",
  belief: "信念因子",
  episode: "经历因子",
  identity: "身份因子",
  insight: "洞察因子",
  term: "术语因子",
};
