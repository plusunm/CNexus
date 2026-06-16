"use client";

import type { ExecutionIdentityBundleView } from "@/lib/spine/contract";
import { bi, biSection, spineL } from "@/lib/spine/labels";
import { useMindTheme } from "../../MindUiProvider";

type Props = {
  identity: ExecutionIdentityBundleView | null;
  traceId?: string;
};

export function SpineIdentityHeader({ identity, traceId }: Props) {
  const t = useMindTheme();

  if (!identity) {
    return (
      <section
        className="px-4 py-4 border-b"
        style={{ borderColor: t.border, backgroundColor: t.chatBg }}
      >
        <p className="text-sm" style={{ color: t.textMuted }}>
          {bi(spineL.noIdentity)}
        </p>
      </section>
    );
  }

  const stabilityPct = Math.round(identity.stability * 100);

  return (
    <section
      className="px-4 py-4 border-b shrink-0"
      style={{
        borderColor: t.border,
        background: `linear-gradient(135deg, ${t.chatBg} 0%, ${t.sidebarActive}44 100%)`,
      }}
    >
      <p className="text-[10px] uppercase tracking-widest mb-2 opacity-60" style={{ color: t.textMuted }}>
        {biSection(spineL.identityHeader)}
      </p>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-lg font-bold font-mono" style={{ color: "#5eead4" }}>
            {identity.id}
          </p>
          {traceId ? (
            <p className="text-[11px] font-mono mt-1 opacity-70" style={{ color: t.textMuted }}>
              {bi(spineL.traceInstance)}: {traceId}
            </p>
          ) : null}
        </div>
        <div className="flex flex-wrap gap-4 text-[11px] font-mono">
          <span style={{ color: stabilityPct >= 90 ? t.green : stabilityPct >= 70 ? t.orange : t.red }}>
            {bi(spineL.identityStability)}: {stabilityPct}%
          </span>
          <span style={{ color: identity.drift ? t.red : t.green }}>
            {bi(spineL.identityDriftFlag)}: {identity.drift ? bi(spineL.yes) : bi(spineL.no)}
          </span>
          <span style={{ color: t.textMuted }}>
            {bi(spineL.equivalentCount)}: {identity.equivalent_traces.length}
          </span>
        </div>
      </div>
    </section>
  );
}
