"use client";

import type { DriftSummaryView } from "@/lib/spine/contract";
import { bi, biSection, spineL } from "@/lib/spine/labels";
import { useMindTheme } from "../../MindUiProvider";

type Props = {
  drift: DriftSummaryView | null | undefined;
};

function syncColor(status: string | undefined, t: ReturnType<typeof useMindTheme>): string {
  if (status === "synced") return t.green;
  if (status === "drifted") return t.red;
  return t.orange;
}

export function SpineDriftPanel({ drift }: Props) {
  const t = useMindTheme();

  if (!drift) {
    return (
      <section className="px-4 py-2 border-b text-[11px]" style={{ borderColor: t.border, color: t.textMuted }}>
        {bi(spineL.noDriftData)}
      </section>
    );
  }

  const scorePct = Math.round((drift.score ?? 0) * 100);
  const scoreColor = scorePct >= 90 ? t.green : scorePct >= 70 ? t.orange : t.red;

  return (
    <section
      className="px-4 py-2.5 border-b flex flex-wrap items-center gap-x-4 gap-y-1 text-[10px] font-mono"
      style={{ borderColor: t.border, backgroundColor: `${t.red}08` }}
    >
      <span className="font-semibold uppercase tracking-wider" style={{ color: t.textMuted }}>
        {biSection(spineL.driftPanel)}
      </span>
      <span style={{ color: scoreColor }}>
        {bi(spineL.driftScore)}: {scorePct}%
      </span>
      <span style={{ color: t.red }}>
        {bi(spineL.driftMissing)}: {drift.missing_count ?? 0}
      </span>
      <span style={{ color: t.orange }}>
        {bi(spineL.driftExtra)}: {drift.extra_count ?? 0}
      </span>
      <span style={{ color: "#fb923c" }}>
        {bi(spineL.driftMismatch)}: {drift.mismatch_count ?? 0}
      </span>
      <span style={{ color: syncColor(drift.spine_sync_status, t) }}>
        {bi(spineL.driftSync)}: {drift.spine_sync_status}
      </span>
    </section>
  );
}
