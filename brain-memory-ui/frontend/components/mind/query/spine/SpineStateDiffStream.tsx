"use client";

import type { SpineFrontContractV1, StatePatchView } from "@/lib/spine/contract";
import { bi, biSection, spineL } from "@/lib/spine/labels";
import { useMindTheme } from "../../MindUiProvider";

type Props = { contract: SpineFrontContractV1 };

function renderChanges(step: StatePatchView) {
  const lines: string[] = [];
  const changes = step.changes ?? [];
  for (const raw of changes) {
    if (!raw || typeof raw !== "object") continue;
    const c = raw as { field?: string; before?: unknown; after?: unknown };
    const field = String(c.field ?? "field");
    const leaf = field.split(".").pop() ?? field;
    if (c.before !== undefined && c.after !== undefined) {
      lines.push(`  ${leaf}: ${String(c.before)} → ${String(c.after)}`);
    } else if (c.after !== undefined) {
      lines.push(`  + ${leaf}: ${String(c.after)}`);
    } else if (c.before !== undefined) {
      lines.push(`  - ${leaf}: ${String(c.before)}`);
    }
  }
  if (!lines.length && step.change_count) {
    lines.push(`  Δ ${step.change_count} fields`);
  }
  return lines;
}

export function SpineStateDiffStream({ contract }: Props) {
  const t = useMindTheme();
  const timeline = contract.state.timeline;

  return (
    <div className="h-full flex flex-col min-h-0">
      <h3 className="text-[10px] uppercase tracking-wider mb-2 opacity-60 shrink-0" style={{ color: t.textMuted }}>
        {biSection(spineL.stateDiffStream)}
      </h3>
      <p className="text-[10px] font-mono mb-2 opacity-50 shrink-0" style={{ color: t.textMuted }}>
        state / tier-a
      </p>
      {timeline.length === 0 ? (
        <p className="text-xs opacity-60" style={{ color: t.textMuted }}>
          {bi(spineL.noStateTrajectory)}
        </p>
      ) : (
        <div className="flex-1 overflow-auto space-y-2 text-[10px] font-mono">
          {timeline.slice(0, 12).map((step, i) => {
            const lines = renderChanges(step);
            return (
              <div
                key={step.event_id ?? i}
                className="rounded border px-2 py-1.5"
                style={{ borderColor: t.border, backgroundColor: t.chatBg }}
              >
                <div style={{ color: "#2dd4bf" }}>
                  {step.mutation_label ?? "patch"} · {step.event_id?.slice(0, 10) ?? i}
                </div>
                {lines.map((line) => (
                  <div key={line} className="opacity-80" style={{ color: t.text }}>
                    {line}
                  </div>
                ))}
              </div>
            );
          })}
          {contract.explanation.state_story?.slice(0, 2).map((line) => (
            <p key={line} className="opacity-70 text-[10px]" style={{ color: t.textMuted }}>
              {line}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}
