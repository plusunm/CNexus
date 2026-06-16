"use client";



import { useCallback, useEffect, useState } from "react";

import { brainApi } from "@/lib/api";

import { useMindConnection } from "@/cnexus-kernel";
import { useMindStore } from "@/cnexus-kernel/MindStore";
import { EXECUTION_STATUS_POLL_MS } from "@/lib/uiPollIntervals";

import { useRuntimeReachability } from "@/hooks/useRuntimeReachability";

import { probeLocalOllama } from "@/lib/localServiceProbe";

import {

  markRuntimeReachabilityBooting,

  markRuntimeReachabilityFailed,

  markRuntimeReachabilityReady,

} from "@/cnexus-kernel/runtimeReachabilityStore";



export type ExecutionProviderHealth = {

  state: "ready" | "degraded" | "unavailable" | string;

  capabilities: string[];

  reachable: boolean;

  issues: string[];

  details: Record<string, unknown>;

};



export type ExecutionStatusSnapshot = {

  activeChatProvider: string | null;

  activeEmbedProvider: string | null;

  providers: Record<string, ExecutionProviderHealth>;

  suggestedActions: string[];

  embedding: {

    active_mode?: string;

    active_provider?: string;

    model?: string;

    ollama_reachable?: boolean;

  };

  ollama: {

    installed?: boolean;

    binary_found?: boolean;

    running?: boolean;

    host?: string;

    download_url?: string;

    binary_path?: string | null;

  };

  loading: boolean;

  runtimeConnected: boolean;

  localOllamaReachable: boolean;

  error: string | null;

};



const DEFAULT: ExecutionStatusSnapshot = {

  activeChatProvider: null,

  activeEmbedProvider: null,

  providers: {},

  suggestedActions: [],

  embedding: {},

  ollama: {},

  loading: true,

  runtimeConnected: false,

  localOllamaReachable: false,

  error: null,

};



/** Live probe + API — never sticky-run from a past successful probe. */
function resolveOllamaSnapshot(
  apiOllama: ExecutionStatusSnapshot["ollama"],
  localReachable: boolean,
  runtimeConnected: boolean,
): ExecutionStatusSnapshot["ollama"] {
  const host = apiOllama.host ?? "http://127.0.0.1:11434";
  const downloadUrl = apiOllama.download_url ?? "https://ollama.com/download";

  if (runtimeConnected) {
    return {
      installed: Boolean(apiOllama.installed),
      binary_found: Boolean(apiOllama.binary_found),
      running: Boolean(apiOllama.running),
      host,
      download_url: downloadUrl,
      binary_path: apiOllama.binary_path ?? null,
    };
  }

  if (localReachable) {
    return {
      installed: apiOllama.installed ?? true,
      binary_found: apiOllama.binary_found ?? true,
      running: true,
      host,
      download_url: downloadUrl,
      binary_path: apiOllama.binary_path ?? null,
    };
  }

  return {
    installed: Boolean(apiOllama.installed),
    binary_found: Boolean(apiOllama.binary_found),
    running: false,
    host,
    download_url: downloadUrl,
    binary_path: apiOllama.binary_path ?? null,
  };
}



async function probeRuntimePhase(): Promise<"ready" | "warming" | "offline"> {
  await useMindStore.getState().syncSystemCapability();
  const s = useMindStore.getState();
  if (s.runtimeOperationalReady) return "ready";
  if (s.runtimeReachable) return "warming";
  return "offline";
}



export function useExecutionStatus() {

  const { runtimeEnabled } = useMindConnection();

  const reach = useRuntimeReachability();

  const runtimeOperationalReady = useMindStore((s) => s.runtimeOperationalReady);

  const [status, setStatus] = useState<ExecutionStatusSnapshot>(DEFAULT);



  const refresh = useCallback(async () => {

    const [localResult, readyResult] = await Promise.allSettled([

      probeLocalOllama(2500),

      runtimeEnabled

        ? probeRuntimePhase()

        : Promise.resolve("offline" as const),

    ]);



    const localReachable = localResult.status === "fulfilled" ? localResult.value : false;

    const readyPhase =

      readyResult.status === "fulfilled" ? readyResult.value : ("offline" as const);



    if (!runtimeEnabled) {

      setStatus({

        ...DEFAULT,

        loading: false,

        runtimeConnected: false,

        localOllamaReachable: localReachable,

        ollama: resolveOllamaSnapshot({}, localReachable, false),

        error: null,

      });

      return;

    }



    const runtimeOptimistic =
      reach.reachable &&
      (reach.phase === "pending" || reach.phase === "booting" || reach.phase === "ready");

    const runtimeOnline =

      readyPhase === "ready" ||

      readyPhase === "warming" ||

      (runtimeOptimistic && readyPhase === "offline");



    if (runtimeOnline) {
      if (readyPhase === "ready") {
        markRuntimeReachabilityReady(reach.bootPhase);
      } else if (readyPhase === "warming") {
        markRuntimeReachabilityBooting(reach.bootPhase);
      }
    } else if (reach.phase !== "pending" && reach.phase !== "booting") {
      markRuntimeReachabilityFailed();
    }



    const runtimePending =
      !runtimeOnline && (reach.phase === "pending" || reach.phase === "booting" || reach.reachable);



    setStatus((prev) => ({

      ...prev,

      loading: runtimePending && !localReachable,

      error: null,

      localOllamaReachable: localReachable,

      ollama: resolveOllamaSnapshot(prev.ollama, localReachable, false),

    }));



    if (!runtimeOnline) {

      setStatus((prev) => ({

        ...prev,

        loading: false,

        runtimeConnected: false,

        localOllamaReachable: localReachable,

        ollama: resolveOllamaSnapshot(prev.ollama, localReachable, false),

        error: localReachable ? null : "Runtime 未连接",

      }));

      return;

    }



    try {

      const payload = await brainApi.executionStatus();

      setStatus({

        activeChatProvider: payload.active_chat_provider ?? null,

        activeEmbedProvider: payload.active_embed_provider ?? null,

        providers: Object.fromEntries(

          Object.entries(payload.providers ?? {}).map(([key, value]) => [

            key,

            {

              state: value.state,

              capabilities: value.capabilities ?? [],

              reachable: Boolean(value.reachable),

              issues: value.issues ?? [],

              details: value.details ?? {},

            },

          ]),

        ),

        suggestedActions: payload.suggested_actions ?? [],

        embedding: payload.embedding ?? {},

        ollama: resolveOllamaSnapshot(payload.ollama ?? {}, localReachable, true),

        loading: false,

        runtimeConnected: true,

        localOllamaReachable: localReachable,

        error: null,

      });

    } catch (err) {

      let ollamaFallback: ExecutionStatusSnapshot["ollama"] = {};

      try {

        ollamaFallback = await brainApi.ollamaStatus();

      } catch {

        /* API slow — fall back to direct probe */

      }

      setStatus((prev) => ({

        ...prev,

        ollama: resolveOllamaSnapshot(
          Object.keys(ollamaFallback).length ? ollamaFallback : prev.ollama,
          localReachable,
          true,
        ),

        loading: false,

        runtimeConnected: true,

        localOllamaReachable: localReachable,

        error: err instanceof Error ? err.message : "Execution status unavailable",

      }));

    }

  }, [runtimeEnabled, reach.reachable, reach.phase, reach.bootPhase]);



  useEffect(() => {

    void refresh();

    const timer = window.setInterval(() => void refresh(), EXECUTION_STATUS_POLL_MS);

    return () => window.clearInterval(timer);

  }, [refresh]);



  useEffect(() => {

    if (runtimeOperationalReady) void refresh();

  }, [runtimeOperationalReady, refresh]);



  return { status, refresh };

}

