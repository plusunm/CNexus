"use client";

import { bi, biSection, tokenL } from "@/lib/spine/labels";
import { costBarWidth } from "@/lib/token/format";
import type { TokenField } from "@/lib/token/types";
import { useMindTheme } from "../../MindUiProvider";

type Props = {
  report: TokenField;
  onSelectSpine?: (id: string) => void;
};

export function TokenBindingPanel({ report, onSelectSpine }: Props) {
  const t = useMindTheme();
  const bindings = [...(report.bindings ?? [])].sort((a, b) => b.tokens - a.tokens);
  const max = bindings.length ? bindings[0].tokens : 1;

  return (
    <div className="space-y-3">
      <p className="text-[10px] uppercase tracking-wider opacity-60" style={{ color: t.textMuted }}>
        {biSection(tokenL.tabBinding)} · {bindings.length} {bi(tokenL.bindings)}
      </p>
      {!bindings.length ? (
        <p className="text-xs opacity-60" style={{ color: t.textMuted }}>
          {bi(tokenL.noBindings)}
        </p>
      ) : (
        bindings.map((b) => (
          <button
            key={b.spine_event_id}
            type="button"
            onClick={() => onSelectSpine?.(b.spine_event_id)}
            className="w-full text-left rounded border p-2"
            style={{ borderColor: t.border, backgroundColor: t.chatBg }}
          >
            <div className="flex justify-between text-xs font-mono mb-1" style={{ color: t.text }}>
              <span className="truncate">{b.spine_event_id}</span>
              <span style={{ color: t.blue }}>{b.tokens}</span>
            </div>
            <div className="h-1 rounded-full overflow-hidden" style={{ backgroundColor: t.border }}>
              <div
                className="h-full rounded-full"
                style={{
                  width: costBarWidth(b.tokens, max),
                  backgroundColor: "#5eead4",
                  opacity: 0.85,
                }}
              />
            </div>
          </button>
        ))
      )}
    </div>
  );
}
