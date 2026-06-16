"use client";

import { bi, biSection, tokenL } from "@/lib/spine/labels";
import { COST_COLOR } from "@/lib/token/format";
import type { TokenTrace } from "@/lib/token/types";
import { useMindTheme } from "../MindUiProvider";

type Props = {
  traces: TokenTrace[];
  selectedTraceId: string | null;
  onSelect: (traceId: string) => void;
};

export function TokenTraceList({ traces, selectedTraceId, onSelect }: Props) {
  const t = useMindTheme();

  return (
    <div className="flex flex-col min-h-0 overflow-hidden lg:h-full lg:flex-1">
      <h3 className="text-[10px] uppercase tracking-wider mb-2 opacity-60 shrink-0" style={{ color: t.textMuted }}>
        {biSection(tokenL.traceList)}
      </h3>
      <p className="text-[10px] font-mono mb-2 opacity-50 shrink-0" style={{ color: t.textMuted }}>
        {traces.length} {bi(tokenL.traceCount)}
      </p>
      {!traces.length ? (
        <p className="text-xs opacity-60 shrink-0" style={{ color: t.textMuted }}>
          {bi(tokenL.noTraces)}
        </p>
      ) : (
        <div className="cnexus-trace-list-scroll overflow-y-auto overflow-x-hidden space-y-0.5 pr-1 font-mono text-[11px] max-h-[220px] lg:max-h-none lg:flex-1 lg:min-h-0">
          {traces.map((trace, i) => {
            const selected = selectedTraceId === trace.trace_id;
            const prefix = i === traces.length - 1 ? "└─" : "├─";
            const color = COST_COLOR[trace.cost_level];
            return (
              <button
                key={trace.trace_id}
                type="button"
                onClick={() => onSelect(trace.trace_id)}
                className="w-full text-left pl-3 py-1.5 rounded transition"
                style={{
                  backgroundColor: selected ? t.sidebarActive : "transparent",
                  color: t.text,
                }}
              >
                <span className="opacity-50 mr-1">{prefix}</span>
                <span className="font-semibold truncate block" style={{ color: "#60a5fa" }}>
                  {trace.trace_id.slice(0, 16)}
                </span>
                <span className="text-[9px] opacity-70" style={{ color }}>
                  {trace.total} · {trace.cost_level}
                </span>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
