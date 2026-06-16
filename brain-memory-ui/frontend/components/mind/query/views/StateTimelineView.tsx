"use client";

import type { StatePatchView } from "@/lib/spine/contract";
import { useQueryStore } from "@/lib/queryStore";
import { useMindTheme } from "../../MindUiProvider";

type Props = {
  timeline: StatePatchView[];
};

export function StateTimelineView({ timeline }: Props) {
  const t = useMindTheme();
  const { stateStepIndex, setStateStepIndex } = useQueryStore();

  if (!timeline.length) {
    return <p className="text-sm opacity-70">No state timeline for this trace.</p>;
  }

  const idx = Math.min(stateStepIndex, timeline.length - 1);
  const step = timeline[idx];

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <input
          type="range"
          min={0}
          max={Math.max(0, timeline.length - 1)}
          value={idx}
          onChange={(e) => setStateStepIndex(Number(e.target.value))}
          className="flex-1"
        />
        <span className="text-[10px] font-mono opacity-70">
          t{idx} / {timeline.length - 1}
        </span>
      </div>

      <div className="rounded-lg border p-3" style={{ borderColor: t.border, backgroundColor: t.chatBg }}>
        <p className="text-[10px] font-mono opacity-60 mb-2">
          {step.event_id ?? "—"} · {step.mutation_label ?? step.timestamp ?? "state step"}
        </p>
        {step.after ? (
          <pre className="text-[11px] overflow-auto max-h-[28vh] opacity-90">
            {JSON.stringify(step.after, null, 2)}
          </pre>
        ) : null}
        {step.changes?.length ? (
          <details className="mt-2">
            <summary className="text-[10px] uppercase cursor-pointer opacity-60">Delta expansion</summary>
            <pre className="text-[10px] mt-2 overflow-auto max-h-[24vh] opacity-80">
              {JSON.stringify(step.changes, null, 2)}
            </pre>
          </details>
        ) : null}
      </div>

      <ol className="text-[11px] font-mono space-y-1 opacity-80 max-h-[24vh] overflow-auto">
        {timeline.map((s, i) => (
          <li
            key={`${s.event_id}-${i}`}
            className={i === idx ? "text-teal-300" : ""}
          >
            t{i}: {s.mutation_label ?? s.event_id ?? "state"} ({s.change_count ?? 0} changes)
          </li>
        ))}
      </ol>
    </div>
  );
}
