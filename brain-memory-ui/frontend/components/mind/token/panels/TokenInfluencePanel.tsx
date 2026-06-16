"use client";

import { bi, biFmt, biSection, tokenL } from "@/lib/spine/labels";
import { edgeWeightColor } from "@/lib/token/format";
import type { TokenField, TokenWeightedEdge } from "@/lib/token/types";
import { useMindTheme } from "../../MindUiProvider";

type Props = {
  report: TokenField;
};

export function TokenInfluencePanel({ report }: Props) {
  const t = useMindTheme();
  const hotPaths = report.influence?.hot_paths ?? [];
  const edges = (report.causal?.edges ?? []) as TokenWeightedEdge[];
  const weighted = edges.filter((e) => e.influenced).sort((a, b) => (b.token_weight ?? 0) - (a.token_weight ?? 0));

  return (
    <div className="space-y-4">
      <div className="rounded-lg border p-3" style={{ borderColor: t.border, backgroundColor: t.chatBg }}>
        <p className="text-sm font-semibold" style={{ color: t.text }}>
          {biSection(tokenL.hotPaths)}
        </p>
        <p className="text-xs font-mono mt-1" style={{ color: t.textMuted }}>
          {bi(tokenL.maxWeight)}: {report.influence?.max_weight ?? 1}
        </p>
      </div>

      {hotPaths.length === 0 ? (
        <p className="text-xs opacity-60" style={{ color: t.textMuted }}>
          {bi(tokenL.noHotPaths)}
        </p>
      ) : (
        <div className="space-y-2">
          {hotPaths.map((hp, i) => (
            <div
              key={`${hp.from}-${hp.to}-${i}`}
              className="rounded border p-2 text-xs font-mono"
              style={{ borderColor: edgeWeightColor(hp.weight), color: edgeWeightColor(hp.weight) }}
            >
              <span className="opacity-80">{hp.from.slice(0, 10)}</span>
              <span className="mx-1 opacity-50">→</span>
              <span className="opacity-80">{hp.to.slice(0, 10)}</span>
              <span className="ml-2 opacity-70">
                {biFmt(tokenL.hotPathWeight, {
                  w: hp.weight,
                  sev: hp.severity === "HIGH" ? tokenL.severityHigh.zh : tokenL.severityMid.zh,
                })}
              </span>
            </div>
          ))}
        </div>
      )}

      <div>
        <p className="text-[10px] uppercase tracking-wider mb-2 opacity-60" style={{ color: t.textMuted }}>
          {bi(tokenL.weightedEdges)}
        </p>
        <div className="space-y-1 max-h-[320px] overflow-auto">
          {weighted.slice(0, 30).map((e, i) => (
            <div
              key={`${e.from}-${e.to}-${i}`}
              className="text-[10px] font-mono py-1 border-b"
              style={{ borderColor: t.border, color: edgeWeightColor(e.token_weight ?? 1) }}
            >
              {e.from.slice(0, 8)} → {e.to.slice(0, 8)} ·{" "}
              {biFmt(tokenL.edgeWeightLine, { base: e.base_weight ?? 1, w: e.token_weight ?? 1 })}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
