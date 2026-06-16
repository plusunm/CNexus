"use client";

import { bootPhaseMeta, BOOT_PHASES, normalizeBootPhase, parseL3Status, type BootPhaseId, type L3SchedulerStatus } from "@/lib/systemConvergence";
import { useMindTheme } from "../MindUiProvider";

type Props = {
  phase: string | null;
  l3?: L3SchedulerStatus | null;
  boot?: Record<string, unknown> | null;
  compact?: boolean;
};

/** Boot v3 progress rail + L3 tick pulse during BOOT_3 */
export function BootPhaseRail({ phase, l3, boot, compact = false }: Props) {
  const t = useMindTheme();
  const normalized = normalizeBootPhase(phase);
  const activeOrder = normalized ? (bootPhaseMeta(normalized)?.order ?? -1) : -1;
  const l3Status = l3 ?? parseL3Status(boot ?? undefined);
  const showL3 = normalized === "boot_3_cognitive_warming" && l3Status;

  return (
    <div
      className={compact ? "flex items-center gap-1" : "flex flex-col gap-1.5"}
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={BOOT_PHASES.length - 1}
      aria-valuenow={Math.max(0, activeOrder)}
      aria-label="CNexus boot phase"
    >
      <div className="flex items-center gap-1">
        {BOOT_PHASES.map((p) => {
          const done = activeOrder > p.order;
          const active = p.id === normalized;
          const color = done ? t.green : active ? t.blue : t.textMuted;
          return (
            <span
              key={p.id}
              title={p.description.zh}
              className="inline-block rounded-full transition-colors"
              style={{
                width: compact ? 6 : 8,
                height: compact ? 6 : 8,
                backgroundColor: color,
                opacity: active || done ? 1 : 0.35,
                boxShadow: active ? `0 0 0 2px ${t.blue}40` : undefined,
              }}
            />
          );
        })}
      </div>
      {!compact && normalized && (
        <span className="text-[10px] tabular-nums" style={{ color: t.textMuted }}>
          {bootPhaseMeta(normalized as BootPhaseId)?.label ?? normalized}
        </span>
      )}
      {showL3 && (
        <span className="text-[10px] tabular-nums" style={{ color: t.purple }}>
          L3 · q={l3Status.queue_length ?? 0} · tick={l3Status.ticks ?? 0}
          {l3Status.last_tick?.tick_cost_ms != null ? ` · ${l3Status.last_tick.tick_cost_ms}ms` : ""}
        </span>
      )}
    </div>
  );
}
