"use client";

import { bi, biSection, tokenL } from "@/lib/spine/labels";
import { costBarWidth } from "@/lib/token/format";
import type { TokenField } from "@/lib/token/types";
import { useMindTheme } from "../../MindUiProvider";

type Props = {
  report: TokenField;
  onSelectEvent?: (spineEventId: string) => void;
};

export function TokenFieldPanel({ report, onSelectEvent }: Props) {
  const t = useMindTheme();
  const field = Object.entries(report.field ?? {}).sort((a, b) => b[1] - a[1]);
  const gradient = report.gradient ?? {};
  const maxCost = field.length ? field[0][1] : 1;

  return (
    <div className="flex flex-col min-h-0 h-full overflow-hidden gap-3">
      <div
        className="rounded-lg border p-3 shrink-0"
        style={{ borderColor: t.border, backgroundColor: t.chatBg }}
      >
        <p className="text-sm font-semibold" style={{ color: t.text }}>
          {biSection(tokenL.gravityField)}
        </p>
        <p className="text-xs mt-1 font-mono" style={{ color: t.textMuted }}>
          {bi(tokenL.totalCost)}: {report.total_cost ?? 0} · {field.length} {bi(tokenL.nodeCount)}
        </p>
      </div>

      <div className="cnexus-trace-list-scroll flex-1 min-h-0 overflow-y-auto overflow-x-hidden space-y-2 max-h-[min(360px,calc(100vh-20rem))]">
        {field.length === 0 ? (
          <p className="text-xs opacity-60" style={{ color: t.textMuted }}>
            {bi(tokenL.noFieldData)}
          </p>
        ) : (
          field.map(([eventId, cost]) => {
            const g = gradient[eventId] ?? 0;
            return (
              <button
                key={eventId}
                type="button"
                onClick={() => onSelectEvent?.(eventId)}
                className="w-full text-left rounded border p-2"
                style={{ borderColor: t.border }}
              >
                <div className="flex justify-between text-[10px] font-mono mb-1" style={{ color: t.text }}>
                  <span className="truncate max-w-[55%]">{eventId}</span>
                  <span>
                    {cost}{" "}
                    <span style={{ color: g > 0 ? t.red : g < 0 ? t.green : t.textMuted }}>
                      Δ{g}
                    </span>
                  </span>
                </div>
                <div className="h-1.5 rounded-full overflow-hidden" style={{ backgroundColor: t.border }}>
                  <div
                    className="h-full rounded-full transition-all"
                    style={{
                      width: costBarWidth(cost, maxCost),
                      backgroundColor: t.blue,
                      opacity: Math.min(1, cost / maxCost + 0.25),
                    }}
                  />
                </div>
              </button>
            );
          })
        )}
      </div>

      {report.by_phase && Object.keys(report.by_phase).length > 0 ? (
        <div className="rounded-lg border p-3 shrink-0" style={{ borderColor: t.border }}>
          <p className="text-[10px] uppercase tracking-wider mb-2 opacity-60" style={{ color: t.textMuted }}>
            {biSection(tokenL.byPhase)}
          </p>
          <div className="grid grid-cols-2 gap-2 text-xs font-mono">
            {Object.entries(report.by_phase).map(([phase, cost]) => (
              <div key={phase} style={{ color: t.text }}>
                <span className="opacity-60">{phase}</span>: {cost}
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}
