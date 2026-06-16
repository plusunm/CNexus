import type { CognitiveOutput } from "@/lib/cognitiveTypes";
import type { FlowStreamId } from "@/lib/dataFlowModel";
import type { MindOverview } from "@/lib/runtimeTypes";

export type LexemeTag = "goal" | "belief" | "episode" | "identity" | "insight" | "term";

export type MemoryLexeme = {
  id: string;
  text: string;
  tag: LexemeTag;
  stream: FlowStreamId;
  weight: number;
};

function tagToStream(tag: string): FlowStreamId {
  if (tag === "goal") return "synthesis";
  if (tag === "belief") return "governance";
  if (tag === "identity") return "browse";
  if (tag === "episode") return "import";
  return "chat";
}

function truncate(text: string, max: number): string {
  const s = text.trim();
  if (s.length <= max) return s;
  return `${s.slice(0, max - 1)}…`;
}

function pushUnique(map: Map<string, MemoryLexeme>, item: MemoryLexeme) {
  const key = item.text.toLowerCase();
  if (!key || map.has(key)) return;
  map.set(key, item);
}

/** 从 Mind 概览 / CSE 提取可在 3D 流中展示的记忆词条 */
export function buildMemoryLexicon(overview: MindOverview, data: CognitiveOutput): MemoryLexeme[] {
  const map = new Map<string, MemoryLexeme>();

  for (const item of overview.memory_items) {
    pushUnique(map, {
      id: item.id,
      text: truncate(item.title, 28),
      tag: (item.tag as LexemeTag) || "term",
      stream: tagToStream(item.tag),
      weight: item.tag === "goal" ? 1.2 : 1,
    });
  }

  const { goal, identity, belief, focus } = overview.cards;
  if (goal.title) {
    pushUnique(map, {
      id: "card-goal",
      text: truncate(goal.title, 28),
      tag: "goal",
      stream: "synthesis",
      weight: 1.3,
    });
  }
  if (identity.summary) {
    pushUnique(map, {
      id: "card-identity",
      text: truncate(identity.summary, 28),
      tag: "identity",
      stream: "browse",
      weight: 1.1,
    });
  }
  if (belief.content) {
    pushUnique(map, {
      id: "card-belief",
      text: truncate(belief.content, 28),
      tag: "belief",
      stream: "governance",
      weight: 1.15,
    });
  }
  if (focus.title && focus.title !== "—") {
    pushUnique(map, {
      id: "card-focus",
      text: truncate(focus.title, 28),
      tag: "term",
      stream: "synthesis",
      weight: 1,
    });
  }

  for (const row of overview.feeds.episodic.slice(0, 4)) {
    pushUnique(map, {
      id: `ep-${row.text.slice(0, 8)}`,
      text: truncate(row.text, 22),
      tag: "episode",
      stream: "import",
      weight: 0.9,
    });
  }

  for (const ins of data.insights.slice(0, 4)) {
    pushUnique(map, {
      id: `ins-${ins.source}`,
      text: truncate(ins.title, 24),
      tag: "insight",
      stream: "synthesis",
      weight: 1.05,
    });
  }

  for (const block of data.summary.slice(0, 2)) {
    const chunk = block.text.split(/[，。；]/)[0]?.trim();
    if (chunk) {
      pushUnique(map, {
        id: `sum-${block.source}`,
        text: truncate(chunk, 26),
        tag: "term",
        stream: "synthesis",
        weight: 0.85,
      });
    }
  }

  const list = [...map.values()].sort((a, b) => b.weight - a.weight);
  return list.slice(0, 36);
}

export const LEXEME_TAG_LABEL: Record<LexemeTag, string> = {
  goal: "目标",
  belief: "信念",
  episode: "经历",
  identity: "身份",
  insight: "洞察",
  term: "术语",
};
