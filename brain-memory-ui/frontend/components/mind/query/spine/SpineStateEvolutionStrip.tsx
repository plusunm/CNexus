"use client";

import type { SpineFrontContractV1, StatePatchView } from "@/lib/spine/contract";
import { bi, biSection, spineL } from "@/lib/spine/labels";
import { useMindTheme } from "../../MindUiProvider";

type Props = { contract: SpineFrontContractV1 };

type ChangeRow = { field: string; values: string[] };

function collectFieldSeries(timeline: StatePatchView[]): ChangeRow[] {
  const byField = new Map<string, string[]>();
  for (const step of timeline) {
    const changes = step.changes ?? [];
    for (const raw of changes) {
      if (!raw || typeof raw !== "object") continue;
      const c = raw as { field?: string; before?: unknown; after?: unknown };
      const field = String(c.field ?? "");
      if (!field) continue;
      const series = byField.get(field) ?? [];
      if (series.length === 0 && c.before !== undefined) {
        series.push(String(c.before));
      }
      if (c.after !== undefined) {
        series.push(String(c.after));
      }
      byField.set(field, series);
    }
  }
  return Array.from(byField.entries())
    .map(([field, values]) => ({ field, values }))
    .slice(0, 6);
}

export function SpineStateEvolutionStrip({ contract }: Props) {
  const t = useMindTheme();
  const series = collectFieldSeries(contract.state.timeline);

  return (
    <section className="p-4 border-b" style={{ borderColor: t.border }}>
      <h3 className="text-[10px] uppercase tracking-wider mb-3 opacity-60" style={{ color: t.textMuted }}>
        {biSection(spineL.stateEvolution)}
      </h3>
      {series.length === 0 ? (
        <p className="text-sm opacity-60" style={{ color: t.textMuted }}>
          {bi(spineL.noStateTrajectory)}
        </p>
      ) : (
        <div className="space-y-2">
          {series.map(({ field, values }) => (
            <div key={field} className="text-[11px] font-mono">
              <span className="opacity-60">{field.split(".").pop()}: </span>
              <span style={{ color: t.text }}>{values.join(" → ")}</span>
            </div>
          ))}
          {contract.explanation.state_story?.slice(0, 2).map((line) => (
            <p key={line} className="text-[11px] opacity-80" style={{ color: t.textMuted }}>
              {line}
            </p>
          ))}
        </div>
      )}
    </section>
  );
}
