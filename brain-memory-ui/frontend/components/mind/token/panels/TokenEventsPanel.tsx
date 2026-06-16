"use client";

import clsx from "clsx";
import { bi, biFmt, tokenL } from "@/lib/spine/labels";
import { COST_COLOR, PHASE_COLOR, SOURCE_COLOR } from "@/lib/token/format";
import type { TokenEventRow } from "@/lib/token/types";
import { useMindTheme } from "../../MindUiProvider";

type Props = {
  events: TokenEventRow[];
  selectedEventId: string | null;
  onSelect: (id: string) => void;
};

export function TokenEventsPanel({ events, selectedEventId, onSelect }: Props) {
  const t = useMindTheme();

  if (!events.length) {
    return (
      <p className="text-xs opacity-60 p-4" style={{ color: t.textMuted }}>
        {bi(tokenL.noEvents)}
      </p>
    );
  }

  return (
    <div className="space-y-2">
      {events.map((ev, i) => {
        const selected = selectedEventId === ev.event_id;
        const sourceColor = SOURCE_COLOR[ev.source] ?? t.blue;
        const phaseColor = PHASE_COLOR[ev.phase] ?? t.textMuted;
        const costColor = COST_COLOR[ev.cost_level ?? "mid"];

        return (
          <button
            key={`${ev.event_id}-${i}`}
            type="button"
            onClick={() => onSelect(ev.event_id)}
            className={clsx("w-full text-left rounded-lg border p-3 transition")}
            style={{
              borderColor: selected ? t.blue : t.border,
              backgroundColor: selected ? t.blueSoft : t.chatBg,
            }}
          >
            <div className="flex flex-wrap items-center gap-2 mb-2">
              <span
                className="text-[9px] uppercase tracking-wider px-1.5 py-0.5 rounded font-semibold"
                style={{ backgroundColor: `${sourceColor}22`, color: sourceColor }}
              >
                {ev.source}
              </span>
              <span
                className="text-[9px] uppercase tracking-wider px-1.5 py-0.5 rounded"
                style={{ backgroundColor: `${phaseColor}18`, color: phaseColor }}
              >
                {ev.phase}
              </span>
              {ev.cost_level ? (
                <span className="text-[9px] uppercase font-mono" style={{ color: costColor }}>
                  {ev.cost_level}
                </span>
              ) : null}
            </div>

            <p className="text-xs font-mono" style={{ color: t.text }}>
              {bi(tokenL.whatHappened)}: {ev.source} · {ev.total} Token
            </p>
            <p className="text-[10px] mt-1 opacity-70" style={{ color: t.textMuted }}>
              {bi(tokenL.whoTriggered)}: {ev.entry || ev.mode || "—"}
            </p>
            <p className="text-[10px] opacity-50 font-mono mt-1" style={{ color: t.textMuted }}>
              {biFmt(tokenL.eventSpineLine, {
                id: ev.spine_event_id?.slice(0, 14) ?? "—",
                in: ev.tokens_in,
                out: ev.tokens_out,
              })}
            </p>
          </button>
        );
      })}
    </div>
  );
}
