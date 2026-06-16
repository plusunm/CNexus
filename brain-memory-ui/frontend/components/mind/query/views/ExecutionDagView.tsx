"use client";

import type { ExecutionDagView } from "@/lib/spine/contract";
import { useMindTheme } from "../../MindUiProvider";

type Props = {
  dag: ExecutionDagView;
};

export function ExecutionDagView({ dag }: Props) {
  const t = useMindTheme();

  if (!dag.edges.length && !dag.nodes.length) {
    return (
      <p className="text-sm opacity-70">
        No execution DAG — run a trace with dispatch → control → execution semantics.
      </p>
    );
  }

  const nodeById = new Map(dag.nodes.map((n) => [n.event_id, n]));

  return (
    <div className="space-y-4">
      {dag.roots.length ? (
        <p className="text-[10px] font-mono opacity-60">
          roots: {dag.roots.join(" · ")} · {dag.version ?? "execution-spine-v1"}
        </p>
      ) : null}

      <div className="space-y-2 font-mono text-xs max-h-[50vh] overflow-auto">
        {dag.edges.map((edge, i) => {
          const from = nodeById.get(edge.from);
          const to = nodeById.get(edge.to);
          return (
            <div
              key={`${edge.from}-${edge.to}-${i}`}
              className="rounded border px-3 py-2"
              style={{ borderColor: t.border, backgroundColor: t.chatBg }}
            >
              <span style={{ color: "#5eead4" }}>
                {from ? `${from.phase}:${from.event_type}` : edge.from.slice(0, 12)}
              </span>
              <span className="opacity-60 mx-2">→ [{edge.kind}] →</span>
              <span style={{ color: t.text }}>
                {to ? `${to.phase}:${to.event_type}` : edge.to.slice(0, 12)}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
