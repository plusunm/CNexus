"use client";

import { bi, biSection, tokenL } from "@/lib/spine/labels";
import { COST_COLOR } from "@/lib/token/format";
import type { TokenField, TokenTrace } from "@/lib/token/types";
import { useMindTheme } from "../../MindUiProvider";

type Props = {
  report: TokenField | null;
  traceSummary: TokenTrace | null;
};

export function TokenIdentityPanel({ report, traceSummary }: Props) {
  const t = useMindTheme();

  if (!report && !traceSummary) {
    return (
      <p className="text-xs opacity-60 p-4" style={{ color: t.textMuted }}>
        {bi(tokenL.selectTrace)}
      </p>
    );
  }

  const identityId = report?.identity_id;
  const cost = report?.total_cost ?? traceSummary?.total ?? 0;
  const costLevel = traceSummary?.cost_level ?? "mid";

  return (
    <div className="space-y-4">
      <div
        className="rounded-xl border p-4"
        style={{ borderColor: t.border, backgroundColor: t.surface }}
      >
        <p className="text-[10px] uppercase tracking-wider opacity-60 mb-2" style={{ color: t.textMuted }}>
          {biSection(tokenL.identityOverlay)}
        </p>
        <p className="text-sm font-mono font-semibold" style={{ color: t.text }}>
          {identityId ?? "—"}
        </p>
      </div>

      <div className="rounded-lg border overflow-hidden" style={{ borderColor: t.border }}>
        <table className="w-full text-xs">
          <thead>
            <tr style={{ backgroundColor: t.chatBg, color: t.textMuted }}>
              <th className="text-left px-3 py-2 font-medium">{bi(tokenL.dimension)}</th>
              <th className="text-right px-3 py-2 font-medium">{bi(tokenL.value)}</th>
            </tr>
          </thead>
          <tbody className="font-mono" style={{ color: t.text }}>
            <Row label="trace_id" value={report?.trace_id ?? traceSummary?.trace_id ?? "—"} border={t.border} />
            <Row label="identity_id" value={identityId ?? "—"} border={t.border} />
            <Row label="total_cost" value={String(cost)} border={t.border} accent={COST_COLOR[costLevel]} />
            <Row label="cost_level" value={costLevel} border={t.border} accent={COST_COLOR[costLevel]} />
            <Row label="tokens_in" value={String(traceSummary?.tokens_in ?? "—")} border={t.border} />
            <Row label="tokens_out" value={String(traceSummary?.tokens_out ?? "—")} border={t.border} />
            <Row label="mode" value={traceSummary?.mode ?? "—"} border={t.border} />
            <Row label="entry" value={traceSummary?.entry ?? "—"} border={t.border} />
          </tbody>
        </table>
      </div>

      {report?.by_phase ? (
        <div className="rounded-lg border p-3" style={{ borderColor: t.border }}>
          <p className="text-[10px] uppercase tracking-wider mb-2 opacity-60" style={{ color: t.textMuted }}>
            {bi(tokenL.identityCostBreakdown)}
          </p>
          {Object.entries(report.by_phase).map(([phase, v]) => (
            <div key={phase} className="flex justify-between text-xs font-mono py-1 border-b" style={{ borderColor: t.border, color: t.text }}>
              <span>{phase}</span>
              <span>{v}</span>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function Row({
  label,
  value,
  border,
  accent,
}: {
  label: string;
  value: string;
  border: string;
  accent?: string;
}) {
  return (
    <tr style={{ borderTop: `1px solid ${border}` }}>
      <td className="px-3 py-2 opacity-60">{label}</td>
      <td className="px-3 py-2 text-right truncate max-w-[200px]" style={{ color: accent }}>
        {value}
      </td>
    </tr>
  );
}
