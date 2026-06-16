"use client";

import type { SpineFrontContractV1 } from "@/lib/spine/contract";
import { bi, biSection, spineL } from "@/lib/spine/labels";
import { useMindTheme } from "../../MindUiProvider";

type Props = { contract: SpineFrontContractV1 };

function decisionColor(decision: string, t: ReturnType<typeof useMindTheme>) {
  if (decision === "REJECT") return t.red;
  if (decision === "WARN") return t.orange;
  return t.green;
}

export function SpineControlOverlay({ contract }: Props) {
  const t = useMindTheme();
  const decisions = contract.control.decisions;

  return (
    <section className="p-4 border-b" style={{ borderColor: t.border }}>
      <h3 className="text-[10px] uppercase tracking-wider mb-3 opacity-60" style={{ color: t.textMuted }}>
        {biSection(spineL.controlDecision)}
      </h3>
      {decisions.length === 0 ? (
        <p className="text-sm opacity-60" style={{ color: t.textMuted }}>
          {bi(spineL.noControl)}
        </p>
      ) : (
        <div className="space-y-2">
          {decisions.map((d) => (
            <div
              key={d.event_id}
              className="rounded-lg border px-3 py-2 text-[11px] font-mono"
              style={{ borderColor: t.border, backgroundColor: t.chatBg }}
            >
              <span className="font-semibold" style={{ color: decisionColor(d.decision, t) }}>
                [{d.decision}]
              </span>
              <span className="opacity-70 ml-2">{d.rule ?? d.entry ?? "—"}</span>
              {d.entry ? (
                <p className="mt-1 opacity-50">
                  {bi(spineL.entry)}: {d.entry}
                </p>
              ) : null}
              {d.caller ? (
                <p className="opacity-50">
                  {bi(spineL.caller)}: {d.caller}
                </p>
              ) : null}
            </div>
          ))}
          {contract.explanation.control_story?.slice(0, 2).map((line) => (
            <p key={line} className="text-[11px] opacity-80" style={{ color: t.textMuted }}>
              {line}
            </p>
          ))}
        </div>
      )}
    </section>
  );
}
