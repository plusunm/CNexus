import type { FactorGraph, FactorNode } from "./factorGraphModel";

export type GraphGroupId = "goal" | "belief" | "episode" | "identity" | "insight" | "term" | "halo";

export type GraphViewNode = {
  id: string;
  label: string;
  group: GraphGroupId;
  weight: number;
  x: number;
  y: number;
  vx: number;
  vy: number;
  fixed?: boolean;
};

export type GraphViewLink = {
  id: string;
  source: string;
  target: string;
  strength: number;
};

export type GraphViewModel = {
  nodes: GraphViewNode[];
  links: GraphViewLink[];
};

export type GraphViewSettings = {
  centerForce: number;
  repelForce: number;
  linkForce: number;
  linkDistance: number;
  nodeSize: number;
  linkThickness: number;
  textFade: number;
  animate: boolean;
  showArrows: boolean;
  search: string;
  tagsOnly: boolean;
  orphansOnly: boolean;
};

export const DEFAULT_GRAPH_SETTINGS: GraphViewSettings = {
  centerForce: 0.08,
  repelForce: 120,
  linkForce: 0.04,
  linkDistance: 72,
  nodeSize: 1,
  linkThickness: 1,
  textFade: 0.35,
  animate: true,
  showArrows: false,
  search: "",
  tagsOnly: true,
  orphansOnly: false,
};

/** Float compact factor graph — tuned for ~400×280 viewport */
export const FLOAT_COMPACT_GRAPH_SETTINGS: GraphViewSettings = {
  ...DEFAULT_GRAPH_SETTINGS,
  centerForce: 0.1,
  repelForce: 85,
  linkForce: 0.05,
  linkDistance: 52,
  nodeSize: 0.92,
  linkThickness: 0.85,
  textFade: 0.42,
};

const GROUP_FOR_TAG: Record<FactorNode["tag"], GraphGroupId> = {
  goal: "goal",
  belief: "belief",
  episode: "episode",
  identity: "identity",
  insight: "insight",
  term: "term",
};

export function buildGraphViewModel(graph: FactorGraph): GraphViewModel {
  const nodes: GraphViewNode[] = graph.nodes.map((n, i) => {
    const angle = (i / Math.max(graph.nodes.length, 1)) * Math.PI * 2;
    const onRing = n.weight < 1.05 || i % 3 === 0;
    const r = onRing ? 220 + (i % 5) * 18 : 40 + Math.random() * 80;
    return {
      id: n.id,
      label: n.text,
      group: GROUP_FOR_TAG[n.tag] ?? "term",
      weight: n.weight,
      x: Math.cos(angle) * r,
      y: Math.sin(angle) * r,
      vx: 0,
      vy: 0,
    };
  });

  const links: GraphViewLink[] = graph.edges.map((e) => ({
    id: e.id,
    source: e.from,
    target: e.to,
    strength: e.strength,
  }));

  const byGroup = new Map<GraphGroupId, string[]>();
  for (const n of nodes) {
    const list = byGroup.get(n.group) ?? [];
    list.push(n.id);
    byGroup.set(n.group, list);
  }
  for (const ids of byGroup.values()) {
    for (let i = 0; i < ids.length - 1; i += 1) {
      for (let j = i + 1; j < Math.min(i + 3, ids.length); j += 1) {
        const a = ids[i];
        const b = ids[j];
        if (links.some((l) => (l.source === a && l.target === b) || (l.source === b && l.target === a))) continue;
        links.push({ id: `tag-${a}-${b}`, source: a, target: b, strength: 0.35 });
      }
    }
  }

  if (nodes.length < 28) {
    const haloCount = Math.max(12, 28 - nodes.length);
    for (let i = 0; i < haloCount; i += 1) {
      const angle = (i / haloCount) * Math.PI * 2;
      const id = `halo-${i}`;
      nodes.push({
        id,
        label: "",
        group: "halo",
        weight: 0.35 + (i % 3) * 0.08,
        x: Math.cos(angle) * (260 + (i % 4) * 12),
        y: Math.sin(angle) * (260 + (i % 4) * 12),
        vx: 0,
        vy: 0,
      });
      const anchor = nodes[i % Math.max(graph.nodes.length, 1)]?.id;
      if (anchor) {
        links.push({ id: `halo-link-${i}`, source: id, target: anchor, strength: 0.06 });
      }
      const nextHalo = `halo-${(i + 1) % haloCount}`;
      if (i < haloCount - 1) {
        links.push({ id: `halo-ring-${i}`, source: id, target: nextHalo, strength: 0.04 });
      }
    }
  }

  return { nodes, links };
}

export function filterGraphModel(model: GraphViewModel, settings: GraphViewSettings): GraphViewModel {
  let nodes = model.nodes;
  const q = settings.search.trim().toLowerCase();
  if (q) {
    nodes = nodes.filter((n) => n.label.toLowerCase().includes(q) || n.group.includes(q));
  }
  if (settings.orphansOnly) {
    const linked = new Set<string>();
    for (const l of model.links) {
      linked.add(l.source);
      linked.add(l.target);
    }
    nodes = nodes.filter((n) => n.group === "halo" || !linked.has(n.id));
  }
  if (settings.tagsOnly) {
    nodes = nodes.filter((n) => n.group === "halo" || n.group !== "term");
  }
  const ids = new Set(nodes.map((n) => n.id));
  const links = model.links.filter((l) => ids.has(l.source) && ids.has(l.target));
  return { nodes, links };
}
