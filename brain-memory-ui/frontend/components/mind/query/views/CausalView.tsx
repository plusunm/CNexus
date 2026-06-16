"use client";

import type { SpineQueryResponse } from "@/lib/spineQueryTypes";

type Props = {
  edges?: { from: string; to: string; kind: string }[];
  subgraph?: SpineQueryResponse["subgraph"];
  causal?: SpineQueryResponse["causal"];
};

export function CausalView({ edges, subgraph, causal }: Props) {
  const displayEdges = subgraph?.edges?.length ? subgraph.edges : edges;
  const nodes = subgraph?.nodes ?? [];

  if (!displayEdges?.length && !nodes.length) {
    return <p className="text-sm opacity-70">No causal subgraph.</p>;
  }

  return (
    <div className="space-y-3">
      {causal?.roots?.length ? (
        <p className="text-xs font-mono opacity-80">
          roots: {causal.roots.join(" → ")} · chains: {causal.chains?.length ?? 0}
        </p>
      ) : null}
      <pre className="text-xs overflow-auto max-h-[32vh] p-3 rounded-lg border border-white/10 bg-black/20">
        {JSON.stringify({ nodes: nodes.length, edges: displayEdges }, null, 2)}
      </pre>
      <div
        id="graph"
        className="min-h-[200px] rounded-lg border border-dashed border-white/15 flex items-center justify-center text-xs opacity-60"
      >
        Subgraph from backend ({nodes.length} nodes, {displayEdges?.length ?? 0} edges)
      </div>
    </div>
  );
}
