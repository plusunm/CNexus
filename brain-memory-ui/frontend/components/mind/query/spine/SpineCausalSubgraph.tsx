"use client";

import type { SpineFrontContractV1 } from "@/lib/spine/contract";
import { bi, biSection, spineL } from "@/lib/spine/labels";
import { useMindTheme } from "../../MindUiProvider";

type Props = { contract: SpineFrontContractV1 };

export function SpineCausalSubgraph({ contract }: Props) {
  const t = useMindTheme();
  const dag = contract.execution.dag;
  const edges = dag.edges.length ? dag.edges : contract.edges;
  const nodes = dag.nodes;

  return (
    <div className="h-full flex flex-col min-h-0">
      <h3 className="text-[10px] uppercase tracking-wider mb-2 opacity-60 shrink-0" style={{ color: t.textMuted }}>
        {biSection(spineL.causalSubgraph)}
      </h3>
      {!edges.length ? (
        <p className="text-xs opacity-60" style={{ color: t.textMuted }}>
          {bi(spineL.noCausal)}
        </p>
      ) : (
        <div className="flex-1 overflow-auto space-y-1 text-[10px] font-mono">
          {nodes.slice(0, 12).map((n) => (
            <div
              key={n.event_id}
              className="px-2 py-1 rounded border"
              style={{ borderColor: t.border, backgroundColor: t.chatBg }}
            >
              <span style={{ color: "#5eead4" }}>{n.phase}</span>
              <span className="opacity-60"> · {n.event_type}</span>
              <div className="opacity-50 truncate">{n.event_id.slice(0, 14)}</div>
            </div>
          ))}
          <div className="pt-2 opacity-70" style={{ color: t.textMuted }}>
            {bi(spineL.causalEdges)}:
          </div>
          {edges.slice(0, 16).map((e, i) => (
            <p key={`${e.from}-${e.to}-${i}`} className="pl-2 truncate" style={{ color: t.text }}>
              <span style={{ color: "#fbbf24" }}>{e.kind}</span> · {e.from.slice(0, 8)} → {e.to.slice(0, 8)}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}
