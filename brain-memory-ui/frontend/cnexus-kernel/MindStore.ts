import { create } from "zustand";
import { DEMO_MIND_OVERVIEW } from "@/lib/demoMindOverview";
import type { MindOverview } from "@/lib/runtimeTypes";
import { ModelProfile, RuntimeLogEntry, RuntimeState, brainApi, cnexusProductApi } from "@/lib/api";
import { parseL3Status, type L3SchedulerStatus } from "@/lib/systemConvergence";
import { assertMindOverviewContract } from "./MindOverviewContract";
import { resolveOverviewForSource } from "./selectOverview";
import type { EffectiveConnectionMode } from "./connectionMode";
import {
  clearRuntimeReachability,
  publishRuntimeReachability,
} from "./runtimeReachabilityBus";
import {
  getBootSessionId,
  markRuntimeReachabilityBooting,
  markRuntimeReachabilityFailed,
  markRuntimeReachabilityReady,
  resetRuntimeReachabilityStore,
  syncRuntimeReachabilityFromMindStore,
} from "./runtimeReachabilityStore";
import {
  EMPTY_CAPABILITIES,
  parseCapabilityPayload,
  type RuntimeCapabilities,
  type SystemCapabilitySnapshot,
} from "@/lib/systemCapability";
import { reportClientPhaseFlip, reportRuntimeConflict } from "@/lib/runtimeConflictMonitor";

type MindStoreState = {
  models: ModelProfile[];
  selectedModelId: string;
  runtimeState: RuntimeState | null;
  mindOverview: MindOverview | null;
  runtimeLogs: RuntimeLogEntry[];
  runtimeReachable: boolean;
  /** Full readiness (BOOT_4 + cognitive) — upload / authoritative gate. */
  runtimeReady: boolean;
  /** Layer-1 operational readiness — chat / basic API without cognitive gate. */
  runtimeOperationalReady: boolean;
  runtimeCapabilities: RuntimeCapabilities;
  runtimeCognitiveStatus: string | null;
  runtimeBootPhase: string | null;
  runtimeBootReason: string | null;
  runtimeBootProgress: number | null;
  runtimeL3Status: L3SchedulerStatus | null;
  runtimeRenderMode: string | null;
  runtimeStreamPhase: string | null;
  effectiveMode: EffectiveConnectionMode;
  setEffectiveMode: (mode: EffectiveConnectionMode) => void;
  setModels: (m: ModelProfile[]) => void;
  setSelectedModel: (id: string) => void;
  ingestRuntimeState: (s: RuntimeState) => void;
  ingestMindOverview: (o: MindOverview) => void;
  setRuntimeLogs: (logs: RuntimeLogEntry[]) => void;
  appendRuntimeLog: (entry: RuntimeLogEntry) => void;
  setRuntimeReachable: (v: boolean) => void;
  resetRuntimeBinding: () => void;
  refreshModels: () => Promise<void>;
  probeRuntime: () => Promise<void>;
  probeRuntimeFull: () => Promise<void>;
  /** SSOT — poll /v1/system/capability and update all runtime gates. */
  syncSystemCapability: () => Promise<void>;
  syncRuntimeProbeResult: (
    result: "ready" | "warming" | "offline",
    bootPhase?: string | null,
    details?: { reason?: string | null; progress?: number | null },
  ) => void;
  applyFastReadySnapshot: (payload: {
    status: string;
    boot_phase?: string;
    ws?: string;
    render_mode?: string;
  }) => void;
  applyStreamEvent: (event: {
    phase: string;
    status?: string;
    boot_phase?: string;
    ws?: string;
    render_mode?: string;
    cluster?: string;
    ready?: boolean;
  }) => void;
  applyV3Ready: (payload: {
    status: string;
    mode?: string;
    boot_phase?: string;
    ws?: string;
    render_mode?: string;
  }) => void;
  applyComputeResult: (result: {
    type?: string;
    status?: string;
    l3?: number;
    cluster?: string;
  }) => void;
  refreshLogs: () => Promise<void>;
  pullMindOverview: () => Promise<void>;
  /** Pull overview, models, logs after Runtime becomes ready (debounced). */
  hydrateRuntimeData: () => Promise<void>;
  afterMemoryCapture: (payload: {
    content: string;
    layer: string;
    label?: string;
    keywords?: string[];
  }) => Promise<void>;
  getOverview: () => MindOverview;
};

const HYDRATE_MIN_INTERVAL_MS = 2_000;

function validateOverview(
  overview: MindOverview,
  effectiveMode: EffectiveConnectionMode,
): MindOverview {
  try {
    assertMindOverviewContract(overview as unknown as Record<string, unknown>);
    return overview;
  } catch (err) {
    if (effectiveMode === "runtime" || effectiveMode === "fallback") {
      console.warn("[cnexus] mind overview contract mismatch — keeping runtime payload", err);
      return overview;
    }
    return DEMO_MIND_OVERVIEW;
  }
}

function pickDefaultModelId(models: ModelProfile[], current: string): string {
  if (current && models.some((m) => m.id === current && m.enabled)) {
    const cur = models.find((m) => m.id === current)!;
    if (cur.api_key_set || cur.provider === "ollama") return current;
  }
  const keyed =
    models.find((m) => m.is_default && m.api_key_set && m.enabled) ??
    models.find((m) => m.api_key_set && m.enabled);
  if (keyed) return keyed.id;
  const ollama = models.find((m) => m.id === "ollama-local" && m.enabled);
  if (ollama) return ollama.id;
  return models.find((m) => m.is_default && m.enabled)?.id ?? models.find((m) => m.enabled)?.id ?? "";
}

function overviewCacheKey(
  effectiveMode: EffectiveConnectionMode,
  mindOverview: MindOverview | null,
  runtimeState: RuntimeState | null,
  runtimeBootPhase: string | null,
): string {
  return [
    effectiveMode,
    runtimeBootPhase ?? "",
    mindOverview?.generated_at ?? "",
    mindOverview?.schema_version ?? "",
    runtimeState?.timestamp ?? "",
  ].join("|");
}

export const useMindStore = create<MindStoreState>((set, get) => {
  let cachedOverview: { key: string; value: MindOverview } | null = null;
  let probeInFlight: Promise<void> | null = null;
  let hydrateInFlight: Promise<void> | null = null;
  let lastHydrateAt = 0;

  const invalidateOverviewCache = () => {
    cachedOverview = null;
  };

  const markRuntimeWarming = (bootPhase?: string | null) => {
    const phase = bootPhase ?? get().runtimeBootPhase;
    const { runtimeOperationalReady } = get();
    set({
      runtimeReachable: true,
      runtimeReady: false,
      runtimeOperationalReady,
      runtimeBootPhase: phase,
    });
    if (runtimeOperationalReady) {
      markRuntimeReachabilityReady(phase);
    } else {
      markRuntimeReachabilityBooting(phase);
    }
  };

  const applyCapabilitySnapshot = (snap: SystemCapabilitySnapshot) => {
    const wasFull = get().runtimeReady;
    const wasOperational = get().runtimeOperationalReady;
    const bootPhase = snap.boot_phase ?? null;
    set({
      runtimeReachable: snap.capabilities.api || snap.operational_ready,
      runtimeOperationalReady: snap.operational_ready,
      runtimeReady: snap.full_ready,
      runtimeCognitiveStatus: snap.cognitive_status,
      runtimeCapabilities: snap.capabilities,
      runtimeBootPhase: bootPhase ?? get().runtimeBootPhase,
      runtimeBootReason: snap.full_ready ? null : snap.reason,
      runtimeBootProgress: snap.full_ready ? 100 : snap.progress,
      runtimeRenderMode: "capability_v1",
    });
    if (snap.operational_ready) {
      markRuntimeReachabilityReady(bootPhase);
      syncRuntimeReachabilityFromMindStore(true, bootPhase, "ws");
      publishRuntimeReachability({
        reachable: true,
        bootPhase,
        bootSessionId: getBootSessionId(),
      });
    } else if (snap.capabilities.api || snap.status === "warming") {
      markRuntimeReachabilityBooting(bootPhase);
    } else {
      markRuntimeProbeFailed();
      return;
    }
    if (snap.operational_ready && !wasOperational) {
      void get().hydrateRuntimeData();
    } else if (snap.full_ready && !wasFull) {
      void get().hydrateRuntimeData();
    }
    const phase = snap.operational_ready ? "ready" : snap.capabilities.api ? "warming" : "offline";
    reportClientPhaseFlip(phase);
    if (snap.full_ready !== wasFull || snap.operational_ready !== wasOperational) {
      void reportRuntimeConflict(
        "CAPABILITY_TRANSITION",
        {
          operational_ready: snap.operational_ready,
          full_ready: snap.full_ready,
          cognitive_status: snap.cognitive_status,
          boot_phase: snap.boot_phase,
          reason: snap.reason,
        },
        "info",
      );
    }
  };

  const markRuntimeHealthy = () => {
    const { runtimeReady, runtimeReachable, runtimeBootPhase, runtimeOperationalReady } = get();
    if (!runtimeOperationalReady && !runtimeReady) return;

    const bootPhase = runtimeBootPhase;
    if (!runtimeReachable) {
      set({ runtimeReachable: true });
    }
    markRuntimeReachabilityReady(bootPhase);
    syncRuntimeReachabilityFromMindStore(true, bootPhase, "ws");
    publishRuntimeReachability({
      reachable: true,
      bootPhase,
      bootSessionId: getBootSessionId(),
    });
  };

  const markRuntimeProbeFailed = () => {
    set({
      runtimeReady: false,
      runtimeOperationalReady: false,
      runtimeReachable: false,
      runtimeCapabilities: EMPTY_CAPABILITIES,
    });
    markRuntimeReachabilityFailed();
  };

  const computeOverview = (): MindOverview => {
    const { effectiveMode, mindOverview, runtimeState, runtimeBootPhase } = get();
    const key = overviewCacheKey(effectiveMode, mindOverview, runtimeState, runtimeBootPhase);
    if (cachedOverview?.key === key) return cachedOverview.value;
    const value = validateOverview(
      resolveOverviewForSource(
        effectiveMode,
        DEMO_MIND_OVERVIEW,
        mindOverview,
        runtimeState,
        { bootPhase: runtimeBootPhase },
      ),
      effectiveMode,
    );
    cachedOverview = { key, value };
    return value;
  };

  return {
    models: [],
    selectedModelId: "",
    runtimeState: null,
    mindOverview: null,
    runtimeLogs: [],
    runtimeReachable: false,
    runtimeReady: false,
    runtimeOperationalReady: false,
    runtimeCapabilities: EMPTY_CAPABILITIES,
    runtimeCognitiveStatus: null,
    runtimeBootPhase: null,
    runtimeBootReason: null,
    runtimeBootProgress: null,
    runtimeL3Status: null,
    runtimeRenderMode: null,
    runtimeStreamPhase: null,
    effectiveMode: "demo",

    setEffectiveMode: (effectiveMode) => {
      invalidateOverviewCache();
      set({ effectiveMode });
    },

    setModels: (models) => set({ models }),
    setSelectedModel: (selectedModelId) => set({ selectedModelId }),

    ingestRuntimeState: (runtimeState) => {
      invalidateOverviewCache();
      set({
        runtimeState,
        mindOverview:
          runtimeState.mind_overview !== null && runtimeState.mind_overview !== undefined
            ? runtimeState.mind_overview
            : get().mindOverview,
      });
    },

    ingestMindOverview: (mindOverview) => {
      invalidateOverviewCache();
      markRuntimeHealthy();
      set({ mindOverview: validateOverview(mindOverview, get().effectiveMode) });
    },

    setRuntimeLogs: (runtimeLogs) => set({ runtimeLogs }),
    appendRuntimeLog: (entry) => {
      set((s) => ({ runtimeLogs: [...s.runtimeLogs.slice(-199), entry] }));
    },

    setRuntimeReachable: (runtimeReachable) => set({ runtimeReachable }),

    resetRuntimeBinding: () => {
      invalidateOverviewCache();
      probeInFlight = null;
      clearRuntimeReachability();
      resetRuntimeReachabilityStore();
      set({
        runtimeState: null,
        mindOverview: null,
        runtimeLogs: [],
        runtimeReachable: false,
        runtimeReady: false,
        runtimeOperationalReady: false,
        runtimeCapabilities: EMPTY_CAPABILITIES,
        runtimeCognitiveStatus: null,
        runtimeBootPhase: null,
        runtimeL3Status: null,
        runtimeRenderMode: null,
        runtimeStreamPhase: null,
      });
    },

    applyFastReadySnapshot: ({ status, boot_phase, render_mode }) => {
      set({
        runtimeReachable: true,
        runtimeBootPhase: boot_phase ?? status,
        runtimeRenderMode: render_mode ?? "fast_path_v1",
        runtimeL3Status: null,
      });
      void get().syncSystemCapability();
    },

    applyStreamEvent: (event) => {
      const phase = event.phase;
      set({
        runtimeStreamPhase: phase,
        runtimeRenderMode: event.render_mode ?? "fast_path_v2",
        runtimeBootPhase: event.boot_phase ?? get().runtimeBootPhase,
        runtimeReachable: true,
      });
      if (phase === "shell" || phase === "final") {
        void get().syncSystemCapability();
      }
    },

    applyV3Ready: ({ status, boot_phase, render_mode }) => {
      set({
        runtimeReachable: true,
        runtimeBootPhase: boot_phase ?? status ?? get().runtimeBootPhase,
        runtimeRenderMode: render_mode ?? "fast_path_v3",
        runtimeStreamPhase: "ui_driver",
        runtimeL3Status: null,
      });
      void get().syncSystemCapability();
    },

    applyComputeResult: (result) => {
      if (result.type === "status" && typeof result.l3 === "number") {
        set({
          runtimeL3Status: {
            queue_length: result.l3,
            scheduler: "ui-driven-v3",
          },
        });
      }
    },

    syncRuntimeProbeResult: (_result, bootPhase, details) => {
      if (bootPhase) {
        set({ runtimeBootPhase: bootPhase });
      }
      if (details?.reason != null || details?.progress != null) {
        set({
          runtimeBootReason: details.reason ?? get().runtimeBootReason,
          runtimeBootProgress: details.progress ?? get().runtimeBootProgress,
        });
      }
      void get().syncSystemCapability();
    },

    getOverview: computeOverview,

    refreshModels: async () => {
      try {
        const { models } = await brainApi.models();
        const fallbackId = pickDefaultModelId(models, get().selectedModelId);
        set({
          models,
          selectedModelId: fallbackId,
        });
        markRuntimeHealthy();
      } catch {
        /* models optional while runtime warms up */
      }
    },

    probeRuntime: async () => {
      return get().syncSystemCapability();
    },

    probeRuntimeFull: async () => {
      return get().syncSystemCapability();
    },

    syncSystemCapability: async () => {
      if (probeInFlight) return probeInFlight;

      probeInFlight = (async () => {
        try {
          const raw = await cnexusProductApi.systemCapability();
          applyCapabilitySnapshot(parseCapabilityPayload(raw as Record<string, unknown>));
          set({
            runtimeL3Status: parseL3Status(raw.boot as Record<string, unknown> | undefined),
          });
        } catch {
          // capability failed — secondary SSOT read, then degraded (not offline)
          try {
            const ready = await cnexusProductApi.systemReadyFull();
            applyCapabilitySnapshot(parseCapabilityPayload(ready as Record<string, unknown>));
            set({
              runtimeL3Status: parseL3Status(ready.boot as Record<string, unknown> | undefined),
            });
            void reportRuntimeConflict(
              "PROBE_DEGRADED",
              { health: "ok", capability: "fail", recovered: "system_ready" },
              "warn",
            );
            return;
          } catch {
            /* fall through */
          }
          try {
            const health = await cnexusProductApi.health();
            if (health.status === "ok") {
              const prev = get();
              const apiUp = Boolean(
                (health as { runtime_pointer?: boolean }).runtime_pointer ?? true,
              );
              set({
                runtimeReachable: true,
                runtimeOperationalReady: prev.runtimeOperationalReady,
                runtimeReady: prev.runtimeReady,
                runtimeCognitiveStatus: "warming",
                runtimeCapabilities: prev.runtimeCapabilities.api
                  ? prev.runtimeCapabilities
                  : { ...EMPTY_CAPABILITIES, api: apiUp },
                runtimeBootReason: "capability_fail_health_ok",
              });
              markRuntimeReachabilityBooting(prev.runtimeBootPhase);
              void reportRuntimeConflict("PROBE_DEGRADED", { health: "ok", capability: "fail" }, "warn");
              return;
            }
          } catch {
            // health also failed — runtime is offline
          }
          set({
            runtimeBootReason: "capability_fail_health_fail",
            runtimeBootPhase: get().runtimeBootPhase ?? "ERROR",
          });
          markRuntimeProbeFailed();
          void reportRuntimeConflict("PROBE_OFFLINE", {}, "error");
        }
      })().finally(() => {
        probeInFlight = null;
      });

      return probeInFlight;
    },

    refreshLogs: async () => {
      try {
        const { logs } = await brainApi.logs(80);
        set({ runtimeLogs: logs });
      } catch {
        /* log stream may lag; do not flip reachability */
      }
    },

    pullMindOverview: async () => {
      try {
        const overview = await brainApi.mindOverview();
        invalidateOverviewCache();
        set({ mindOverview: validateOverview(overview, get().effectiveMode) });
        markRuntimeHealthy();
      } catch {
        /* overview refresh failure alone must not drop Live status */
      }
    },

    hydrateRuntimeData: async () => {
      const now = Date.now();
      if (hydrateInFlight) return hydrateInFlight;
      if (now - lastHydrateAt < HYDRATE_MIN_INTERVAL_MS) return;
      const { runtimeReachable, runtimeReady, runtimeOperationalReady } = get();
      if (!runtimeReachable && !runtimeReady && !runtimeOperationalReady) return;

      lastHydrateAt = now;
      hydrateInFlight = (async () => {
        const s = get();
        await Promise.allSettled([
          s.pullMindOverview(),
          s.refreshModels(),
          s.refreshLogs(),
        ]);
      })().finally(() => {
        hydrateInFlight = null;
      });
      return hydrateInFlight;
    },

    afterMemoryCapture: async ({ content, layer, label, keywords }) => {
      const { effectiveMode } = get();
      if (effectiveMode === "demo") {
        const base = get().mindOverview ?? get().getOverview();
        const tag = layer === "episodic" ? "episode" : layer;
        const title = content.trim().slice(0, 120) || label || "导入内容";
        const keywordHint = keywords?.length ? ` · ${keywords.slice(0, 4).join("、")}` : "";
        const item = {
          id: `capture-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
          title,
          tag,
          desc: `导入 · ${label ?? "文本"}${keywordHint}`,
          meta: "刚刚",
        };
        invalidateOverviewCache();
        set({
          mindOverview: validateOverview({
            ...base,
            generated_at: new Date().toISOString(),
            memory_items: [item, ...base.memory_items].slice(0, 24),
            feeds: {
              ...base.feeds,
              episodic:
                tag === "episode"
                  ? [{ text: title.slice(0, 80), ago: "刚刚" }, ...base.feeds.episodic].slice(0, 8)
                  : base.feeds.episodic,
              changes: [`已导入: ${title.slice(0, 48)}`, ...base.feeds.changes].slice(0, 8),
            },
            system: { ...base.system, last_update_ago: "刚刚" },
          }, "demo"),
        });
        return;
      }
      await get().pullMindOverview();
    },
  };
});

export type { RuntimeState, RuntimeLogEntry, ModelProfile } from "@/lib/api";
