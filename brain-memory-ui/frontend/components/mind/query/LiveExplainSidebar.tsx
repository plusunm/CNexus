"use client";

import type { ExplanationFrame } from "@/hooks/useExplainStream";
import { useMindTheme } from "../MindUiProvider";

type Props = {
  frames: ExplanationFrame[];
  connected: boolean;
  stale?: boolean;
};

export function LiveExplainSidebar({ frames, connected, stale }: Props) {
  const t = useMindTheme();
  const status = connected ? (stale ? "STALE" : "LIVE") : "OFFLINE";
  const statusColor = connected ? (stale ? t.orange : t.green) : t.textMuted;

  const last = frames.slice(-8);
  const causalPulse = last.flatMap((f) =>
    (f.causal_delta?.added_edges ?? []).map(([a, b]) => `${a.slice(0, 8)}→${b.slice(0, 8)}`),
  );
  const stateLine = last
    .flatMap((f) => Object.keys(f.state_delta?.delta ?? {}))
    .slice(-3)
    .join(", ");
  const controlLine = last.find((f) => f.control_delta)?.control_delta;
  const narrative = last.map((f) => f.narrative_delta).filter(Boolean).slice(-1)[0];

  return (
    <aside
      className="hidden xl:flex w-[280px] shrink-0 flex-col border-l overflow-hidden"
      style={{ borderColor: t.border, backgroundColor: t.surface }}
    >
      <div className="px-3 py-3 border-b shrink-0" style={{ borderColor: t.border }}>
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-semibold uppercase tracking-wider" style={{ color: t.text }}>
            Live Explain
          </h3>
          <span className="text-[10px] font-mono" style={{ color: statusColor }}>
            {status}
          </span>
        </div>
        <p className="text-[10px] mt-1 opacity-60" style={{ color: t.textMuted }}>
          WS /v1/spine/explain/ws
        </p>
      </div>

      <div className="flex-1 overflow-auto p-3 space-y-3 text-[11px] font-mono">
        <Section title="Causal pulse" lines={causalPulse} empty="—" t={t} />
        <Section title="State" lines={stateLine ? [`Δ ${stateLine}`] : []} empty="—" t={t} />
        <Section
          title="Control"
          lines={
            controlLine
              ? [`${controlLine.policy ?? "?"} → ${controlLine.decision ?? "?"}`]
              : []
          }
          empty="—"
          t={t}
        />
        <Section title="Narrative" lines={narrative ? [narrative] : []} empty="waiting…" t={t} />
      </div>
    </aside>
  );
}

function Section({
  title,
  lines,
  empty,
  t,
}: {
  title: string;
  lines: string[];
  empty: string;
  t: ReturnType<typeof useMindTheme>;
}) {
  return (
    <div className="rounded border p-2" style={{ borderColor: t.border, backgroundColor: t.chatBg }}>
      <p className="text-[9px] uppercase tracking-wider opacity-50 mb-1">{title}</p>
      {lines.length ? (
        lines.map((line) => (
          <p key={line} className="opacity-90 truncate" style={{ color: t.text }}>
            {line}
          </p>
        ))
      ) : (
        <p className="opacity-40">{empty}</p>
      )}
    </div>
  );
}
