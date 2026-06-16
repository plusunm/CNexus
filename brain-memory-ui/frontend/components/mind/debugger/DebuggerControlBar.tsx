"use client";

import clsx from "clsx";
import { Pause, Play, RefreshCw } from "lucide-react";
import type { SpineEvent } from "@/lib/spineTypes";
import { useSpineStore } from "@/lib/spineStore";
import { useMindTheme } from "../MindUiProvider";

type Props = {
  events: SpineEvent[];
  loading: boolean;
  refreshing?: boolean;
  onRefresh: () => void;
};

/** 底部控制条 — stream / replay / view 切换 */
export function DebuggerControlBar({ events, loading, refreshing, onRefresh }: Props) {
  const t = useMindTheme();
  const debuggerView = useSpineStore((s) => s.debuggerView);
  const setDebuggerView = useSpineStore((s) => s.setDebuggerView);
  const streamMode = useSpineStore((s) => s.streamMode);
  const setStreamMode = useSpineStore((s) => s.setStreamMode);
  const replayIndex = useSpineStore((s) => s.replayIndex);
  const setReplayIndex = useSpineStore((s) => s.setReplayIndex);
  const playing = useSpineStore((s) => s.playing);
  const setPlaying = useSpineStore((s) => s.setPlaying);

  const allowCount = events.filter((e) => e.decision?.decision === "ALLOW").length;
  const warnCount = events.filter((e) => e.decision?.decision === "WARN").length;
  const rejectCount = events.filter((e) => e.decision?.decision === "REJECT").length;

  return (
    <footer
      className="shrink-0 border-t px-4 py-2 flex flex-wrap items-center gap-3"
      style={{ borderColor: t.border, backgroundColor: t.chatBg }}
    >
      <div className="inline-flex rounded-lg border p-0.5" style={{ borderColor: t.border }}>
        {(["timeline", "graph"] as const).map((v) => (
          <button
            key={v}
            type="button"
            onClick={() => setDebuggerView(v)}
            className={clsx("px-3 py-1 rounded text-[11px] font-medium capitalize")}
            style={{
              backgroundColor: debuggerView === v ? t.sidebarActive : "transparent",
              color: debuggerView === v ? t.blue : t.textMuted,
            }}
          >
            {v === "timeline" ? "Tree" : "Causal Graph"}
          </button>
        ))}
      </div>

      <div className="inline-flex rounded-lg border p-0.5" style={{ borderColor: t.border }}>
        <button
          type="button"
          onClick={() => {
            setStreamMode("live");
            setPlaying(false);
          }}
          className="px-2.5 py-1 rounded text-[10px]"
          style={{
            backgroundColor: streamMode === "live" ? "#5eead422" : "transparent",
            color: streamMode === "live" ? "#5eead4" : t.textMuted,
          }}
        >
          Live
        </button>
        <button
          type="button"
          onClick={() => setStreamMode("replay")}
          className="px-2.5 py-1 rounded text-[10px]"
          style={{
            backgroundColor: streamMode === "replay" ? t.purpleSoft : "transparent",
            color: streamMode === "replay" ? t.purple : t.textMuted,
          }}
        >
          Replay
        </button>
      </div>

      {streamMode === "replay" && (
        <div className="flex items-center gap-2 flex-1 min-w-[180px] max-w-md">
          <button
            type="button"
            onClick={() => setPlaying(!playing)}
            className="p-1 rounded border"
            style={{ borderColor: t.border, color: t.textMuted }}
          >
            {playing ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
          </button>
          <input
            type="range"
            min={0}
            max={Math.max(0, events.length - 1)}
            value={replayIndex}
            onChange={(e) => setReplayIndex(Number(e.target.value))}
            className="flex-1 accent-cyan-400"
          />
          <span className="text-[10px] font-mono" style={{ color: t.textMuted }}>
            {replayIndex + 1}/{events.length}
          </span>
        </div>
      )}

      <div className="flex items-center gap-3 text-[10px] ml-auto">
        <span style={{ color: t.green }}>● ALLOW {allowCount}</span>
        <span style={{ color: t.orange }}>● WARN {warnCount}</span>
        <span style={{ color: t.red }}>● REJECT {rejectCount}</span>
      </div>

      <button
        type="button"
        onClick={onRefresh}
        disabled={loading}
        className="inline-flex items-center gap-1 px-2 py-1 rounded text-[10px] border disabled:opacity-50"
        style={{ borderColor: t.border, color: t.blue }}
      >
        <RefreshCw className={clsx("w-3 h-3", (loading || refreshing) && "animate-spin")} />
        Sync
      </button>
    </footer>
  );
}
