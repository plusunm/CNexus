"use client";

import type { ExplanationFrame } from "@/hooks/useExplainStream";
import { bi, biSection, spineL } from "@/lib/spine/labels";
import { useMindTheme } from "../../MindUiProvider";

type Props = {
  frames: ExplanationFrame[];
  connected: boolean;
  enabled: boolean;
  onToggle: () => void;
};

export function SpineLiveStreamSidebar({ frames, connected, enabled, onToggle }: Props) {
  const t = useMindTheme();

  if (!enabled) {
    return (
      <aside
        className="hidden lg:flex w-[48px] shrink-0 border-l items-start justify-center pt-4"
        style={{ borderColor: t.border, backgroundColor: t.surface }}
      >
        <button
          type="button"
          onClick={onToggle}
          className="text-[9px] writing-mode-vertical opacity-50 hover:opacity-100"
          style={{ color: t.textMuted }}
          title={bi(spineL.openLiveStream)}
        >
          {spineL.statusLive.en}
        </button>
      </aside>
    );
  }

  const status = connected ? bi(spineL.statusLive) : bi(spineL.statusOffline);
  const statusColor = connected ? t.green : t.textMuted;

  return (
    <aside
      className="hidden lg:flex w-[260px] shrink-0 flex-col border-l overflow-hidden"
      style={{ borderColor: t.border, backgroundColor: t.surface }}
    >
      <div className="px-3 py-3 border-b flex items-center justify-between shrink-0" style={{ borderColor: t.border }}>
        <div>
          <h3 className="text-[10px] uppercase tracking-wider font-semibold" style={{ color: t.text }}>
            {biSection(spineL.liveSpineStream)}
          </h3>
          <p className="text-[9px] font-mono mt-0.5" style={{ color: statusColor }}>
            {status} · {frames.length} {bi(spineL.frameCount)}
          </p>
        </div>
        <button type="button" onClick={onToggle} className="text-[10px] opacity-60" style={{ color: t.textMuted }}>
          ×
        </button>
      </div>
      <div className="flex-1 overflow-auto p-2 space-y-2 text-[10px] font-mono">
        {frames.slice(-24).reverse().map((f, i) => (
          <div
            key={`${f.event_id}-${i}`}
            className="rounded border p-2"
            style={{ borderColor: t.border, backgroundColor: t.chatBg }}
          >
            <div className="opacity-60">{f.execution_phase ?? f.frame_type ?? "frame"}</div>
            <div className="mt-1 opacity-90" style={{ color: t.text }}>
              {f.narrative_delta ?? f.event_id?.slice(0, 16) ?? "—"}
            </div>
          </div>
        ))}
        {!frames.length ? (
          <p className="opacity-40 p-2">{bi(spineL.waitingFrames)}</p>
        ) : null}
      </div>
    </aside>
  );
}
