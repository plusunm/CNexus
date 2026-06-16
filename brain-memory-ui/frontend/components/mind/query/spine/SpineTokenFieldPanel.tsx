"use client";

import type { SpineFrontContractV1 } from "@/lib/spine/contract";
import { bi, biSection, tokenL } from "@/lib/spine/labels";
import type { TokenField } from "@/lib/token/types";
import { useMindTheme } from "../../MindUiProvider";

type Props = {
  contract: SpineFrontContractV1;
  tokenField: TokenField | null;
  loading?: boolean;
};

function edgeColor(weight: number): string {
  if (weight > 2.5) return "#ef4444";
  if (weight >= 1.5) return "#f97316";
  return "#94a3b8";
}

export function SpineTokenFieldPanel({ contract, tokenField, loading }: Props) {
  const t = useMindTheme();
  const identity = contract.identity;

  if (loading) {
    return (
      <p className="text-xs p-2" style={{ color: t.textMuted }}>
        {bi(tokenL.loadingField)}
      </p>
    );
  }

  const field = tokenField?.field ?? {};
  const gradient = tokenField?.gradient ?? {};
  const hotPaths = tokenField?.influence?.hot_paths ?? [];

  return (
    <div className="space-y-3">
      <div className="border rounded-lg p-3 shrink-0" style={{ borderColor: t.border, backgroundColor: t.chatBg }}>
        <div className="text-sm font-bold" style={{ color: t.text }}>
          {biSection(tokenL.gravityField)}
        </div>
        <div className="text-xs mt-1" style={{ color: t.textMuted }}>
          {bi(tokenL.totalCost)}: {tokenField?.total_cost ?? 0}
        </div>
        {identity?.id ? (
          <div className="text-xs mt-1" style={{ color: t.textMuted }}>
            {bi(tokenL.identityOverlay)}: {identity.id}
            {identity.drift ? " ⚠" : ""}
          </div>
        ) : null}
      </div>

      <div className="border rounded-lg p-3 flex flex-col min-h-0 overflow-hidden" style={{ borderColor: t.border }}>
        <div className="text-[10px] uppercase tracking-wider mb-2 opacity-60 shrink-0" style={{ color: t.textMuted }}>
          {biSection(tokenL.costTimeline)}
        </div>
        <div className="cnexus-trace-list-scroll overflow-y-auto overflow-x-hidden space-y-1 text-xs max-h-[min(280px,calc(100vh-22rem))]">
          {Object.entries(field)
            .slice(0, 20)
            .map(([eventId, cost]) => {
              const g = gradient[eventId] ?? 0;
              return (
                <div
                  key={eventId}
                  className="flex justify-between border-b py-1"
                  style={{
                    borderColor: t.border,
                    opacity: Math.min(1, cost / 2000 + 0.3),
                    color: t.text,
                  }}
                >
                  <span className="font-mono truncate max-w-[45%]">{eventId.slice(0, 14)}</span>
                  <span>
                    {cost} · {bi(tokenL.gradDelta)}{" "}
                    <span style={{ color: g > 0 ? t.red : g < 0 ? t.green : t.textMuted }}>{g}</span>
                  </span>
                </div>
              );
            })}
          {!Object.keys(field).length ? (
            <p className="opacity-60" style={{ color: t.textMuted }}>
              {bi(tokenL.noFieldData)}
            </p>
          ) : null}
        </div>
      </div>

      {hotPaths.length > 0 ? (
        <div className="border rounded-lg p-3" style={{ borderColor: t.border }}>
          <div className="text-[10px] uppercase tracking-wider mb-2 opacity-60" style={{ color: t.textMuted }}>
            {biSection(tokenL.hotPaths)}
          </div>
          <div className="space-y-1 text-xs font-mono">
            {hotPaths.slice(0, 10).map((hp, i) => (
              <div key={`${hp.from}-${hp.to}-${i}`} style={{ color: edgeColor(hp.weight) }}>
                {hp.from.slice(0, 8)} → {hp.to.slice(0, 8)} · {bi(tokenL.weightShort)} {hp.weight}
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {tokenField?.by_phase && Object.keys(tokenField.by_phase).length > 0 ? (
        <div className="border rounded-lg p-3" style={{ borderColor: t.border }}>
          <div className="text-[10px] uppercase tracking-wider mb-2 opacity-60" style={{ color: t.textMuted }}>
            {biSection(tokenL.byPhase)}
          </div>
          <div className="grid grid-cols-2 gap-2 text-xs">
            {Object.entries(tokenField.by_phase).map(([phase, cost]) => (
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
