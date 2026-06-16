"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import type { ExecLogEvent, ExecTraceManifest } from "@/lib/cognitiveTypes";
import { useMindTheme } from "../MindUiProvider";

type Props = {
  logs: ExecLogEvent[];
  traces: ExecTraceManifest[];
  loading: boolean;
  onRefresh: () => void;
  defaultOpen?: boolean;
};

export function ExecTracePanel({ logs, traces, loading, onRefresh, defaultOpen = false }: Props) {
  const t = useMindTheme();
  const [open, setOpen] = useState(defaultOpen);

  return (
    <section
      className="rounded-xl border overflow-hidden"
      style={{ borderColor: t.border, backgroundColor: t.surface }}
    >
      <button
        type="button"
        className="w-full flex items-center justify-between px-4 py-3 text-left"
        onClick={() => setOpen((v) => !v)}
      >
        <div className="flex items-center gap-2">
          {open ? <ChevronDown className="w-4 h-4" style={{ color: t.textMuted }} /> : <ChevronRight className="w-4 h-4" style={{ color: t.textMuted }} />}
          <span className="text-sm font-medium" style={{ color: t.text }}>
            Execution Trace · Σ_exec
          </span>
          <span className="text-[10px]" style={{ color: t.textLight, fontFamily: t.fontMono }}>
            {logs.length} events · {traces.length} traces
          </span>
        </div>
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onRefresh();
          }}
          className="text-[10px] px-2 py-1 rounded border"
          style={{ borderColor: t.border, color: t.textMuted }}
        >
          {loading ? "…" : "刷新"}
        </button>
      </button>

      {open && (
        <div className="border-t max-h-[280px] overflow-auto" style={{ borderColor: t.border }}>
          {traces.length > 0 && (
            <div className="px-4 py-2 border-b" style={{ borderColor: t.border }}>
              <p className="text-[10px] uppercase mb-2" style={{ color: t.purple, fontFamily: t.fontMono }}>
                IR Traces
              </p>
              <div className="flex flex-wrap gap-2">
                {traces.map((tr) => (
                  <span
                    key={tr.trace_id}
                    className="text-[10px] px-2 py-1 rounded"
                    style={{ backgroundColor: t.purpleSoft, color: t.purple, fontFamily: t.fontMono }}
                  >
                    {tr.trace_id.slice(0, 12)}… · {tr.template_name || "ir"}
                  </span>
                ))}
              </div>
            </div>
          )}
          <ul className="divide-y" style={{ borderColor: t.border }}>
            {[...logs].reverse().slice(0, 40).map((log) => (
              <li key={log.id} className="px-4 py-2 text-xs flex gap-3" style={{ color: t.textMuted }}>
                <span className="shrink-0 w-16" style={{ fontFamily: t.fontMono, color: t.textLight }}>
                  {log.timestamp?.slice(11, 19) || "—"}
                </span>
                <span
                  className="shrink-0 w-12 uppercase"
                  style={{
                    color:
                      log.level === "error" ? t.red : log.level === "warn" ? t.orange : t.green,
                    fontFamily: t.fontMono,
                  }}
                >
                  {log.level}
                </span>
                <span className="shrink-0 w-16" style={{ color: t.purple, fontFamily: t.fontMono }}>
                  {log.category}
                </span>
                <span className="min-w-0 truncate" style={{ color: t.text }}>
                  {log.message}
                </span>
              </li>
            ))}
            {logs.length === 0 && (
              <li className="px-4 py-6 text-center text-xs" style={{ color: t.textLight }}>
                暂无运行 trace — 触发 Intent 后将写入 Σ_exec
              </li>
            )}
          </ul>
        </div>
      )}
    </section>
  );
}
