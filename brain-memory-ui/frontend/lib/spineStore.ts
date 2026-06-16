import { create } from "zustand";
import type { DebuggerView, SpineEvent, SpineFilters } from "./spineTypes";
import { EMPTY_SPINE_FILTERS } from "./spineTypes";

type SpineStore = {
  events: SpineEvent[];
  searchQuery: string;
  filters: SpineFilters;
  activeTraceId: string | null;
  selectedEventId: string | null;
  debuggerView: DebuggerView;
  streamMode: "live" | "replay";
  replayIndex: number;
  playing: boolean;
  showRaw: boolean;

  setEvents: (events: SpineEvent[]) => void;
  appendEvents: (events: SpineEvent[]) => void;
  setSearchQuery: (q: string) => void;
  setFilters: (f: SpineFilters) => void;
  resetFilters: () => void;
  setActiveTraceId: (id: string | null) => void;
  selectEvent: (id: string | null) => void;
  setDebuggerView: (v: DebuggerView) => void;
  setStreamMode: (m: "live" | "replay") => void;
  setReplayIndex: (i: number) => void;
  setPlaying: (p: boolean) => void;
  setShowRaw: (v: boolean) => void;
};

export const useSpineStore = create<SpineStore>((set, get) => ({
  events: [],
  searchQuery: "",
  filters: EMPTY_SPINE_FILTERS,
  activeTraceId: null,
  selectedEventId: null,
  debuggerView: "timeline",
  streamMode: "live",
  replayIndex: 0,
  playing: false,
  showRaw: false,

  setEvents: (events) => set({ events }),
  appendEvents: (incoming) => {
    const seen = new Set(get().events.map((e) => e.event_id));
    const merged = [...get().events];
    for (const e of incoming) {
      if (!seen.has(e.event_id)) merged.push(e);
    }
    merged.sort((a, b) => a.timestamp - b.timestamp);
    set({ events: merged });
  },
  setSearchQuery: (searchQuery) => set({ searchQuery }),
  setFilters: (filters) => set({ filters }),
  resetFilters: () => set({ filters: EMPTY_SPINE_FILTERS }),
  setActiveTraceId: (activeTraceId) => set({ activeTraceId }),
  selectEvent: (selectedEventId) => set({ selectedEventId }),
  setDebuggerView: (debuggerView) => set({ debuggerView }),
  setStreamMode: (streamMode) => set({ streamMode }),
  setReplayIndex: (replayIndex) => set({ replayIndex }),
  setPlaying: (playing) => set({ playing }),
  setShowRaw: (showRaw) => set({ showRaw }),
}));
