"use client";

import type { SpineFrontContractV1 } from "@/lib/spine/contract";
import { bi, biSection, spineL } from "@/lib/spine/labels";
import { useMindTheme } from "../../MindUiProvider";

type Props = { contract: SpineFrontContractV1 };

export function SpineCausalLens({ contract }: Props) {
  const t = useMindTheme();
  const { causal, explanation } = contract;
  const root = causal.roots[0] ?? explanation.root_causes[0];

  return (
    <section className="p-4 border-b" style={{ borderColor: t.border }}>
      <h3 className="text-[10px] uppercase tracking-wider mb-3 opacity-60" style={{ color: t.textMuted }}>
        {biSection(spineL.causalLens)}
      </h3>
      {!root && !causal.stream.length ? (
        <p className="text-sm opacity-60" style={{ color: t.textMuted }}>
          {bi(spineL.noCausal)}
        </p>
      ) : (
        <div className="space-y-3 text-xs font-mono leading-relaxed">
          {root ? (
            <p style={{ color: t.text }}>
              <span className="opacity-60">{bi(spineL.rootCause)}: </span>
              <span style={{ color: "#fbbf24" }}>{root}</span>
            </p>
          ) : null}
          {causal.stream.slice(0, 8).map((edge, i) => (
            <p key={`${edge.from}-${edge.to}-${i}`} style={{ color: t.textMuted }}>
              → <span style={{ color: "#5eead4" }}>{edge.relation}</span> · {edge.label ?? `${edge.from} → ${edge.to}`}
            </p>
          ))}
          {causal.chains.slice(0, 4).map((c, i) => (
            <p key={`${c.root}-${i}`} style={{ color: t.textMuted }}>
              {c.path.join(" → ")} → <span style={{ color: t.text }}>{c.root}</span>
            </p>
          ))}
          {explanation.causal_story?.slice(0, 3).map((line) => (
            <p key={line} style={{ color: t.text }}>
              {line}
            </p>
          ))}
        </div>
      )}
    </section>
  );
}
