"use client";

import type { ExecutionRecord } from "@/lib/kernelRecord";
import { useMindTheme } from "../MindUiProvider";

type Props = {
  record: ExecutionRecord;
};

export function ExecutionRecordTruthPanel({ record }: Props) {
  const t = useMindTheme();
  const nodeCount = Array.isArray(record.nodes) ? record.nodes.length : 0;
  const edgeCount = Array.isArray(record.edges) ? record.edges.length : 0;

  return (
    <div className="p-4 space-y-3 border-b" style={{ borderColor: t.border, backgroundColor: t.surface }}>
      <div className="flex flex-wrap items-center gap-2 text-[11px] font-mono">
        <span className="px-2 py-0.5 rounded border" style={{ borderColor: t.border, color: t.green }}>
          KERNEL RECORD
        </span>
        <span style={{ color: t.textMuted }}>trace={record.trace_id}</span>
        {record.identity ? (
          <span style={{ color: t.text }}>identity={record.identity}</span>
        ) : null}
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-[11px] font-mono">
        <Stat label="intent" value={record.intent_type} t={t} />
        <Stat label="nodes" value={String(nodeCount)} t={t} />
        <Stat label="edges" value={String(edgeCount)} t={t} />
        <Stat label="elapsed_ms" value={String(record.elapsed_ms)} t={t} />
      </div>
      {record.graph_invariant ? (
        <p className="text-[10px] font-mono break-all" style={{ color: t.textMuted }}>
          graph_invariant={record.graph_invariant}
        </p>
      ) : null}
      {record.replay_signature ? (
        <p className="text-[10px] font-mono break-all" style={{ color: t.textMuted }}>
          replay_signature={record.replay_signature}
        </p>
      ) : null}
    </div>
  );
}

function Stat({
  label,
  value,
  t,
}: {
  label: string;
  value: string;
  t: ReturnType<typeof useMindTheme>;
}) {
  return (
    <div className="rounded border px-2 py-1.5" style={{ borderColor: t.border }}>
      <div style={{ color: t.textMuted }}>{label}</div>
      <div style={{ color: t.text }}>{value}</div>
    </div>
  );
}
