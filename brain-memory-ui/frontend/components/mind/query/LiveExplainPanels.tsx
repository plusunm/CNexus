"use client";

import type { ExplanationFrame } from "@/hooks/useExplainStream";
import { useMindTheme } from "../MindUiProvider";

type Props = {
  frames: ExplanationFrame[];
  snapshot: Record<string, unknown> | null;
  connected: boolean;
};

function Column({
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
    <div
      className="rounded-lg border p-3 min-h-[160px] flex flex-col"
      style={{ borderColor: t.border, backgroundColor: t.chatBg }}
    >
      <h4 className="text-[10px] uppercase tracking-wider mb-2 opacity-60">{title}</h4>
      <div className="flex-1 overflow-auto text-[11px] font-mono space-y-1 opacity-90">
        {lines.length ? lines.map((line) => <div key={line}>{line}</div>) : <div className="opacity-50">{empty}</div>}
      </div>
    </div>
  );
}

export function LiveExplainPanels({ frames, snapshot, connected }: Props) {
  const t = useMindTheme();

  const causalLines = frames.flatMap((f) =>
    (f.causal_delta?.added_edges ?? []).map(([a, b]) => `${a} → ${b}`),
  );
  const stateLines = frames.flatMap((f) => {
    const delta = f.state_delta?.delta ?? {};
    return Object.entries(delta).map(([k, v]) => `${k}: ${JSON.stringify(v)}`);
  });
  const controlLines = frames
    .filter((f) => f.control_delta)
    .map((f) => `${f.control_delta?.policy} → ${f.control_delta?.decision}`);
  const narrativeLines = frames.map((f) => f.narrative_delta).filter(Boolean) as string[];
  const feedbackLines = frames.flatMap((f) => {
    const fb = f.feedback;
    if (!fb) return [];
    const parts = [`score=${fb.evaluation?.score ?? "?"} ${fb.evaluation?.quality ?? ""}`];
    if (fb.drift && Object.keys(fb.drift).length) {
      parts.push(`drift: ${Object.keys(fb.drift).join(", ")}`);
    }
    return parts;
  });

  return (
    <div className="space-y-3 mt-4 pt-4 border-t" style={{ borderColor: t.border }}>
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold" style={{ color: t.text }}>
          Live Explanation Stream
        </h3>
        <span className="text-[10px] font-mono" style={{ color: connected ? t.green : t.textMuted }}>
          {connected ? "LIVE" : "OFFLINE"} · {frames.length} frames
        </span>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <Column title="Causal" lines={causalLines.slice(-12)} empty="—" t={t} />
        <Column title="State" lines={stateLines.slice(-12)} empty="—" t={t} />
        <Column title="Control" lines={controlLines.slice(-12)} empty="—" t={t} />
      </div>
      <Column title="Narrative" lines={narrativeLines.slice(-8)} empty="Waiting for events…" t={t} />
      {feedbackLines.length ? (
        <Column title="Feedback (observe-only)" lines={feedbackLines.slice(-6)} empty="" t={t} />
      ) : null}
      {snapshot ? (
        <pre className="text-[10px] opacity-60 overflow-auto max-h-24 p-2 rounded border border-white/10">
          {JSON.stringify(snapshot)}
        </pre>
      ) : null}
    </div>
  );
}
