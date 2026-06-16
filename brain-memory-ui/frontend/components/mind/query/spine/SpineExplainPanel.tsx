"use client";

import type { SpineFrontContractV1 } from "@/lib/spine/contract";
import { bi, biSection, spineL } from "@/lib/spine/labels";
import { useMindTheme } from "../../MindUiProvider";

type Props = { contract: SpineFrontContractV1 };

export function SpineExplainPanel({ contract }: Props) {
  const t = useMindTheme();
  const { explanation } = contract;

  const unified =
    explanation.v3_summary ||
    explanation.explain_v3?.summary ||
    explanation.execution_narrative ||
    [
      explanation.narrative,
      explanation.causal_story?.[0],
      explanation.state_story?.[0],
      explanation.control_story?.[0],
    ]
      .filter(Boolean)
      .join(" ");

  return (
    <section className="p-4">
      <h3 className="text-[10px] uppercase tracking-wider mb-3 opacity-60" style={{ color: t.textMuted }}>
        {biSection(spineL.explanation)}
      </h3>
      <p className="text-sm leading-relaxed" style={{ color: t.text }}>
        {unified || bi(spineL.noExplanation)}
      </p>
      {explanation.explain_v3?.epistemic_score != null ? (
        <p className="text-[10px] font-mono mt-2" style={{ color: t.orange }}>
          {bi(spineL.epistemicScore)}: {(explanation.explain_v3.epistemic_score * 100).toFixed(0)}%
        </p>
      ) : null}
      {explanation.explain_v3?.caveats?.length ? (
        <ul className="mt-2 space-y-1 text-[10px]" style={{ color: t.red }}>
          <li className="opacity-70">{bi(spineL.explainCaveats)}:</li>
          {explanation.explain_v3.caveats.map((c, i) => (
            <li key={i}>· {c}</li>
          ))}
        </ul>
      ) : null}
      {explanation.execution_path_labels?.length ? (
        <p className="text-[10px] font-mono mt-3 opacity-70" style={{ color: t.textMuted }}>
          {bi(spineL.path)}: {explanation.execution_path_labels.join(" → ")}
        </p>
      ) : null}
    </section>
  );
}
