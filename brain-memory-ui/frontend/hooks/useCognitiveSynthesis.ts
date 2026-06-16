"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { cnexusProductApi } from "@/lib/api";
import { useMindOverview } from "@/cnexus-kernel";
import { useMindConnection } from "@/cnexus-kernel/MindConnectionProvider";
import { useMindStore } from "@/cnexus-kernel/MindStore";
import type { RuntimeConnectionPhase } from "@/hooks/useFloatRuntimeMonitor";
import { resolveRuntimeConnectionDisplay } from "@/lib/runtimeConnection";
import { DEMO_COGNITIVE_OUTPUT } from "@/lib/demoCognitiveOutput";
import { emptyCognitiveOutput } from "@/lib/cognitiveValue";
import type { CognitiveOutput } from "@/lib/cognitiveTypes";

function patchCognitiveOutput(
  prev: CognitiveOutput,
  payload: CognitiveOutput,
  mode: string,
): CognitiveOutput {
  return {
    ...prev,
    ...payload,
    summary: payload.summary ?? prev.summary,
    patterns: payload.patterns ?? prev.patterns,
    insights: payload.insights ?? prev.insights,
    rules: payload.rules ?? prev.rules,
    experiences: payload.experiences ?? prev.experiences,
    discoveries: payload.discoveries ?? prev.discoveries,
    actions: payload.actions ?? prev.actions,
    top_actions: payload.top_actions ?? prev.top_actions,
    narrative: payload.narrative ?? prev.narrative,
    generated_at: payload.generated_at ?? prev.generated_at,
    window_size: payload.window_size ?? prev.window_size,
    mode: payload.mode || mode,
    exec_traces: payload.exec_traces ?? prev.exec_traces,
  };
}

import { CSE_POLL_MS } from "@/lib/uiPollIntervals";

export type CognitiveSynthesisOptions = {
  requireOperational?: boolean;
  monitorPhase?: RuntimeConnectionPhase | null;
};

export function useCognitiveSynthesis(
  pollMs = CSE_POLL_MS,
  options?: CognitiveSynthesisOptions,
) {
  const { effectiveMode } = useMindConnection();
  const { isDemo, isLive, isWarming } = useMindOverview();
  const runtimeOperationalReady = useMindStore((s) => s.runtimeOperationalReady);
  const connection = resolveRuntimeConnectionDisplay({
    effectiveMode,
    isLive,
    isWarming,
    isDemo,
    monitorPhase: options?.monitorPhase ?? null,
  });
  const canFetch = options?.requireOperational ? connection.canUseRuntimeApi : isLive || isWarming;

  const [data, setData] = useState<CognitiveOutput>(() =>
    isDemo ? DEMO_COGNITIVE_OUTPUT : emptyCognitiveOutput(),
  );
  const [initialLoading, setInitialLoading] = useState(!isDemo);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const hasLoadedRef = useRef(isDemo);

  useEffect(() => {
    setError(null);
    if (isDemo) {
      setData({ ...DEMO_COGNITIVE_OUTPUT, mode: "demo" });
      setInitialLoading(false);
      hasLoadedRef.current = true;
      return;
    }
    setData((prev) => ({
      ...prev,
      mode: isLive ? "runtime" : isWarming ? "warming" : "fallback",
    }));
  }, [isDemo, isLive, isWarming]);

  const refresh = useCallback(
    async (window = 200, opts?: { initial?: boolean }) => {
      if (isDemo) {
        setData({
          ...DEMO_COGNITIVE_OUTPUT,
          generated_at: new Date().toISOString(),
          window_size: window,
          mode: "demo",
        });
        setInitialLoading(false);
        setRefreshing(false);
        setError(null);
        hasLoadedRef.current = true;
        return;
      }

      if (!canFetch) {
        setData((prev) => ({ ...prev, mode: connection.phase === "warming" ? "warming" : "fallback" }));
        setInitialLoading(false);
        setRefreshing(false);
        setError(
          connection.phase === "warming"
            ? "Runtime 正在启动，请稍候片刻后再试"
            : "Runtime 未连接 — 请启动本地 API（127.0.0.1:8000）或切换 Demo 模式",
        );
        return;
      }

      const background = !opts?.initial && hasLoadedRef.current;
      if (background) setRefreshing(true);
      else setInitialLoading(true);
      setError(null);

      try {
        const payload = await cnexusProductApi.cseLive(window);
        const mode = payload.mode || "live";
        setData((prev) =>
          hasLoadedRef.current
            ? patchCognitiveOutput(prev, payload, mode)
            : { ...payload, mode },
        );
        hasLoadedRef.current = true;
      } catch (err) {
        if (!hasLoadedRef.current) {
          setData(emptyCognitiveOutput("fallback"));
        }
        setError(err instanceof Error ? err.message : String(err));
      } finally {
        setInitialLoading(false);
        setRefreshing(false);
      }
    },
    [canFetch, connection.phase, isDemo],
  );

  const synthesize = useCallback(
    async (window = 200) => {
      if (isDemo) {
        setData({
          ...DEMO_COGNITIVE_OUTPUT,
          generated_at: new Date().toISOString(),
          window_size: window,
          mode: "demo_synth",
        });
        setInitialLoading(false);
        setRefreshing(false);
        setError(null);
        hasLoadedRef.current = true;
        return;
      }

      if (!canFetch) {
        setData((prev) => ({ ...prev, mode: connection.phase === "warming" ? "warming" : "fallback" }));
        setError(
          connection.phase === "warming"
            ? "Runtime 正在启动，请稍候片刻后再试"
            : "Runtime 未连接 — 无法重新分析",
        );
        setInitialLoading(false);
        setRefreshing(false);
        return;
      }

      const background = hasLoadedRef.current;
      if (background) setRefreshing(true);
      else setInitialLoading(true);
      setError(null);

      try {
        const payload = await cnexusProductApi.cseSynthesize(window);
        const mode = payload.mode || "synth";
        setData((prev) =>
          hasLoadedRef.current
            ? patchCognitiveOutput(prev, payload, mode)
            : { ...payload, mode },
        );
        hasLoadedRef.current = true;
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      } finally {
        setInitialLoading(false);
        setRefreshing(false);
      }
    },
    [canFetch, connection.phase, isDemo],
  );

  useEffect(() => {
    void refresh(200, { initial: !hasLoadedRef.current });
    if (isDemo || !canFetch || pollMs <= 0) return;
    const timer = window.setInterval(() => void refresh(), pollMs);
    return () => window.clearInterval(timer);
  }, [pollMs, refresh, isDemo, canFetch]);

  useEffect(() => {
    if (runtimeOperationalReady) void refresh();
  }, [runtimeOperationalReady, refresh]);

  return {
    data,
    /** Initial load only — use for full-panel overlay. */
    loading: initialLoading,
    initialLoading,
    refreshing,
    error,
    refresh,
    synthesize,
    isLive,
    isDemo,
  };
}
