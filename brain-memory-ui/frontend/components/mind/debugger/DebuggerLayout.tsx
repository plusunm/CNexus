"use client";

import { useEffect, useMemo } from "react";
import { Activity } from "lucide-react";
import { filterSpineEvents } from "@/lib/spineMapper";
import { useSpineStore } from "@/lib/spineStore";
import { useSpineStream } from "@/hooks/useSpineStream";
import { isReleaseBuild } from "@/lib/releaseBuild";
import { bi, biSection, navL } from "@/lib/spine/labels";
import { useMindTheme } from "../MindUiProvider";
import { DebuggerFilterSidebar } from "./DebuggerFilterSidebar";
import { SpineEventTreePanel } from "./SpineEventTreePanel";
import { SpineCausalGraph } from "./SpineCausalGraph";
import { SpineInspectorPanel } from "./SpineInspectorPanel";
import { DebuggerControlBar } from "./DebuggerControlBar";

/** CNexus 认知调试器 — Spine 单流 + 三投影 */
export function DebuggerLayout() {
  const t = useMindTheme();
  const { loading, refreshing, error, refresh, isLive, emptyReason } = useSpineStream(400);

  const events = useSpineStore((s) => s.events);
  const filters = useSpineStore((s) => s.filters);
  const searchQuery = useSpineStore((s) => s.searchQuery);
  const activeTraceId = useSpineStore((s) => s.activeTraceId);
  const debuggerView = useSpineStore((s) => s.debuggerView);
  const playing = useSpineStore((s) => s.playing);
  const replayIndex = useSpineStore((s) => s.replayIndex);
  const setReplayIndex = useSpineStore((s) => s.setReplayIndex);

  const filtered = useMemo(
    () => filterSpineEvents(events, filters, searchQuery, activeTraceId),
    [events, filters, searchQuery, activeTraceId],
  );

  useEffect(() => {
    if (!playing) return;
    const id = window.setInterval(() => {
      setReplayIndex(Math.min(replayIndex + 1, Math.max(0, filtered.length - 1)));
    }, 800);
    return () => window.clearInterval(id);
  }, [playing, replayIndex, filtered.length, setReplayIndex]);

  return (
    <div className="flex flex-col min-h-[calc(100vh-80px)] rounded-xl border overflow-hidden" style={{ borderColor: t.border }}>
      <header
        className="shrink-0 px-4 py-3 border-b flex items-start justify-between gap-3"
        style={{ borderColor: t.border, backgroundColor: t.surface }}
      >
        <div>
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4" style={{ color: "#5eead4" }} />
            <h1 className="text-base font-bold" style={{ color: t.text }}>
              {biSection(navL.debuggerHeader)}
            </h1>
          </div>
          <p className="text-[11px] mt-0.5" style={{ color: t.textMuted }}>
            {biSection(navL.debuggerHeaderSub)}
          </p>
        </div>
        {error && (
          <p className="text-[11px]" style={{ color: t.orange }}>
            {error}
          </p>
        )}
      </header>

      {!isReleaseBuild && (
        <div
          className="px-4 py-2 text-[11px] border-b shrink-0"
          style={{ borderColor: t.border, backgroundColor: t.chatBg, color: t.orange }}
        >
          {bi(navL.debuggerHint)} ·{" "}
          <a href="/shell?layout=overview" className="underline" style={{ color: "#5eead4" }}>
            {navL.learnMode.en} / {navL.learnMode.zh}
          </a>
        </div>
      )}

      <div className="flex flex-1 min-h-0">
        <DebuggerFilterSidebar events={events} />

        <div className="flex-1 flex flex-col min-w-0 min-h-0">
          {debuggerView === "timeline" ? (
            <SpineEventTreePanel events={filtered} emptyReason={emptyReason} isLive={isLive} />
          ) : (
            <SpineCausalGraph events={filtered} />
          )}
        </div>

        {debuggerView === "graph" && <SpineInspectorPanel events={filtered} />}
      </div>

      <DebuggerControlBar
        events={filtered}
        loading={loading}
        refreshing={refreshing}
        onRefresh={() => void refresh()}
      />
    </div>
  );
}
