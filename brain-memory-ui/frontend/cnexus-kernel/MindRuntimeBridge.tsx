"use client";

import { useEffect } from "react";
import { cnexusProductApi } from "@/lib/api";
import type { RuntimeLogEntry, RuntimeState } from "@/lib/api";
import {
  buildRuntimeModelPayload,
  syncLlmQuickConfigToRuntime,
  syncOllamaLocalToRuntime,
} from "@/lib/floatIntegrations";
import { isTauriDesktop, listenRuntimeReady } from "@/lib/tauriDesktop";
import { createBootstrapGate } from "./FrontendBootstrapGateV3";
import { useMindConnection } from "./MindConnectionProvider";
import { useMindStore } from "./MindStore";
import { RUNTIME_FULL_PROBE_MS, RUNTIME_UPLOAD_PROBE_MS } from "@/lib/uiPollIntervals";
import {
  applyExternalReachabilityToMindStore,
  getRuntimeReachabilitySnapshot,
  subscribeRuntimeReachabilityStore,
} from "./runtimeReachabilityStore";

const WS_RECONNECT_MS = 2_500;
/** Defer WS/log streams until control plane settles — reduces CLOSE_WAIT storm. */
const WS_BOOT_DELAY_MS = 3_000;

function connectStateStream(
  onUpdate: (state: RuntimeState) => void,
  onClose: () => void,
): () => void {
  let ws: WebSocket | null = null;
  let reconnectTimer: number | undefined;
  let stopped = false;

  const connect = () => {
    if (stopped) return;
    ws = cnexusProductApi.connectStateStream(onUpdate);
    ws.onclose = () => {
      onClose();
      if (!stopped) {
        reconnectTimer = window.setTimeout(connect, WS_RECONNECT_MS);
      }
    };
  };

  connect();

  return () => {
    stopped = true;
    if (reconnectTimer) window.clearTimeout(reconnectTimer);
    ws?.close();
  };
}

function connectLogStream(
  onEntry: (entry: RuntimeLogEntry) => void,
  onClose: () => void,
): () => void {
  let ws: WebSocket | null = null;
  let reconnectTimer: number | undefined;
  let stopped = false;

  const connect = () => {
    if (stopped) return;
    ws = cnexusProductApi.connectLogStream(onEntry);
    ws.onclose = () => {
      onClose();
      if (!stopped) {
        reconnectTimer = window.setTimeout(connect, WS_RECONNECT_MS);
      }
    };
  };

  connect();

  return () => {
    stopped = true;
    if (reconnectTimer) window.clearTimeout(reconnectTimer);
    ws?.close();
  };
}

/** Kernel-only: REST/WS binding when user preference is runtime. */
export function MindRuntimeBridge({ children }: { children: React.ReactNode }) {
  const { runtimeEnabled } = useMindConnection();

  useEffect(() => {
    if (!runtimeEnabled) return;

    const zustand = useMindStore.getState;
    let lastReachabilityKey = "";

    const syncZustand = () => {
      const snap = getRuntimeReachabilitySnapshot();
      const key = `${snap.reachable}|${snap.phase}|${snap.bootPhase ?? ""}|${snap.bootSessionId ?? ""}`;
      const changed = key !== lastReachabilityKey;
      lastReachabilityKey = key;

      applyExternalReachabilityToMindStore(
        (v) => zustand().setRuntimeReachable(v),
        (phase) => useMindStore.setState({ runtimeBootPhase: phase }),
      );

      if (!snap.reachable || !changed) return;

      const state = zustand();
      if (state.runtimeOperationalReady && state.runtimeReady) return;

      void state.syncSystemCapability().then(() => state.hydrateRuntimeData());
    };
    syncZustand();

    const unsubStore = subscribeRuntimeReachabilityStore(syncZustand);

    let unlistenReady: (() => void) | undefined;
    if (isTauriDesktop()) {
      void listenRuntimeReady(() => {
        void zustand()
          .syncSystemCapability()
          .then(() => zustand().hydrateRuntimeData());
      }).then((fn) => {
        unlistenReady = fn;
      });
    }

    return () => {
      unsubStore();
      unlistenReady?.();
    };
  }, [runtimeEnabled]);

  useEffect(() => {
    if (!runtimeEnabled) {
      useMindStore.getState().resetRuntimeBinding();
      return;
    }

    let cancelled = false;
    let disconnectStateWs: (() => void) | null = null;
    let disconnectLogWs: (() => void) | null = null;
    let healthTimer: number | undefined;
    let uploadProbeTimer: number | undefined;
    let modelsTimer: number | undefined;

    const store = useMindStore.getState;

    const syncModels = async () => {
      const sync = buildRuntimeModelPayload();
      if (sync) {
        const result = await syncLlmQuickConfigToRuntime();
        if (result.ok && result.testOk && result.modelId) {
          store().setSelectedModel(result.modelId);
          await store().refreshModels();
          return;
        }
      }
      try {
        const exec = await cnexusProductApi.executionStatus();
        const activeChat = exec.active_chat_provider;
        const { models } = await import("@/lib/api").then((m) => m.brainApi.models());
        const hasChat =
          models.some((model) => model.api_key_set && model.enabled) ||
          models.some((model) => model.id === "ollama-local" && model.enabled);
        if (!hasChat && activeChat === "ollama") {
          const ollama = await syncOllamaLocalToRuntime();
          if (ollama.ok && ollama.modelId) {
            store().setSelectedModel(ollama.modelId);
            await store().refreshModels();
          }
        }
      } catch {
        /* runtime may still be warming */
      }
    };

    const bootstrap = async () => {
      await new Promise((r) => window.setTimeout(r, WS_BOOT_DELAY_MS));
      if (cancelled) return;
      const gate = createBootstrapGate({
        store,
        syncModels,
      });
      for (let i = 0; i < 8 && !cancelled; i++) {
        try {
          await gate.load();
          break;
        } catch {
          await new Promise((r) => window.setTimeout(r, 400));
        }
      }
      if (cancelled) return;
      if (store().runtimeReachable) {
        void store().syncSystemCapability().then(() => store().hydrateRuntimeData());
      }
    };

    void bootstrap();

    const wsTimer = window.setTimeout(() => {
      if (cancelled) return;
      disconnectStateWs = connectStateStream(
        (state) => {
          store().ingestRuntimeState(state);
        },
        () => undefined,
      );

      disconnectLogWs = connectLogStream(
        (entry) => {
          store().appendRuntimeLog(entry);
        },
        () => {
          void store().refreshLogs();
        },
      );
    }, WS_BOOT_DELAY_MS);

    healthTimer = window.setInterval(() => {
      void store().syncSystemCapability();
    }, RUNTIME_FULL_PROBE_MS);

    uploadProbeTimer = window.setInterval(() => {
      const s = store();
      if (s.runtimeOperationalReady && !s.runtimeReady && s.runtimeReachable) {
        void s.syncSystemCapability();
      }
    }, RUNTIME_UPLOAD_PROBE_MS);

    modelsTimer = window.setInterval(() => {
      if (!store().models.length) void store().refreshModels();
    }, 15_000);

    return () => {
      cancelled = true;
      window.clearTimeout(wsTimer);
      disconnectStateWs?.();
      disconnectLogWs?.();
      if (healthTimer) window.clearInterval(healthTimer);
      if (uploadProbeTimer) window.clearInterval(uploadProbeTimer);
      if (modelsTimer) window.clearInterval(modelsTimer);
    };
  }, [runtimeEnabled]);

  return <>{children}</>;
}
