import type {
  CognitiveDiscoveryBlock,
  CognitiveInsightBlock,
  CognitiveOutput,
  CognitiveTextBlock,
} from "./cognitiveTypes";

export type ValueDetail =
  | { kind: "insight"; item: CognitiveInsightBlock }
  | { kind: "discovery"; item: CognitiveDiscoveryBlock }
  | { kind: "text"; item: CognitiveTextBlock; label: string };

export function valueScore(confidence: number, novelty = 0): number {
  return confidence * (0.55 + novelty * 0.45);
}

export function sortInsights(items: CognitiveInsightBlock[]): CognitiveInsightBlock[] {
  return [...items].sort(
    (a, b) =>
      valueScore(b.confidence, b.novelty ?? 0) - valueScore(a.confidence, a.novelty ?? 0),
  );
}

export function sortDiscoveries(items: CognitiveDiscoveryBlock[]): CognitiveDiscoveryBlock[] {
  return [...items].sort((a, b) => valueScore(b.confidence, b.novelty) - valueScore(a.confidence, a.novelty));
}

/** 洞察卡片：排除与新发现标题完全同名的项，避免左右重复 */
export function insightCardsForDisplay(
  data: CognitiveOutput,
  limit = 4,
): CognitiveInsightBlock[] {
  const discoveryTitles = new Set(
    (data.discoveries ?? []).map((d) =>
      d.title.replace(/^相较上周期新出现：/, "").trim().toLowerCase(),
    ),
  );
  const filtered = sortInsights(data.insights).filter(
    (ins) => !discoveryTitles.has(ins.title.trim().toLowerCase()),
  );
  return (filtered.length > 0 ? filtered : sortInsights(data.insights)).slice(0, limit);
}

export function isFirstSeen(novelty?: number): boolean {
  return (novelty ?? 0) >= 0.65;
}

export function topInsightCards(data: CognitiveOutput, limit = 4): CognitiveInsightBlock[] {
  return sortInsights(data.insights).slice(0, limit);
}

export function emptyCognitiveOutput(mode = "idle"): CognitiveOutput {
  return {
    summary: [],
    patterns: [],
    insights: [],
    rules: [],
    experiences: [],
    discoveries: [],
    actions: [],
    generated_at: "",
    window_size: 0,
    mode,
  };
}
