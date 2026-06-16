"use client";

import type { CausalChainView, SpineEdgeView, SpineEventView } from "@/lib/spine/contract";
import { useMindTheme } from "../../MindUiProvider";

type Props = {
  roots: string[];
  chains: CausalChainView[];
  stream: Array<{ from: string; to: string; relation: string; label?: string }>;
  events: SpineEventView[];
};

function typeOf(events: SpineEventView[], id: string) {
  return events.find((e) => e.event_id === id)?.type ?? id.slice(0, 12);
}

export function CausalStreamView({ roots, chains, stream, events }: Props) {
  const t = useMindTheme();

  if (!stream.length && !chains.length && !roots.length) {
    return <p className="text-sm opacity-70">No semantic causal stream from backend.</p>;
  }

  return (
    <div className="space-y-4 max-h-[65vh] overflow-auto">
      {roots.length ? (
        <div>
          <h4 className="text-[10px] uppercase tracking-wider opacity-60 mb-2">Roots</h4>
          <p className="text-xs font-mono" style={{ color: t.text }}>
            {roots.join(" · ")}
          </p>
        </div>
      ) : null}

      {stream.length ? (
        <div>
          <h4 className="text-[10px] uppercase tracking-wider opacity-60 mb-2">Causal stream</h4>
          <div className="space-y-2 font-mono text-xs">
            {stream.map((edge, i) => (
              <div key={`${edge.from}-${edge.to}-${i}`} className="pl-2 border-l-2" style={{ borderColor: t.border }}>
                <div style={{ color: t.textMuted }}>{typeOf(events, edge.from)}</div>
                <div className="py-0.5 opacity-70" style={{ color: "#5eead4" }}>
                  ↓ {edge.relation}
                </div>
                <div style={{ color: t.text }}>{typeOf(events, edge.to)}</div>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {chains.length ? (
        <div>
          <h4 className="text-[10px] uppercase tracking-wider opacity-60 mb-2">Root chains</h4>
          <ul className="text-xs font-mono space-y-1">
            {chains.map((c, i) => (
              <li key={`${c.root}-${i}`}>
                {c.root} → {c.path.join(" → ") || "—"}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
