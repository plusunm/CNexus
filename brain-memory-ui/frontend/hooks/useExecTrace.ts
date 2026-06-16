"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { cnexusProductApi } from "@/lib/api";
import { useMindOverview } from "@/cnexus-kernel";
import { useMindStore } from "@/cnexus-kernel/MindStore";
import { DEMO_EXEC_LOGS } from "@/lib/demoCognitiveOutput";
import type { ExecLogEvent, ExecTraceManifest } from "@/lib/cognitiveTypes";

function mergeLogs(prev: ExecLogEvent[], incoming: ExecLogEvent[], cap: number): ExecLogEvent[] {
  if (incoming.length === 0) return prev;
  const seen = new Set(prev.map((l) => l.id));
  const merged = [...prev];
  for (const log of incoming) {
    if (!seen.has(log.id)) {
      merged.push(log);
      seen.add(log.id);
    }
  }
  return merged.slice(-cap);
}

function mergeTraces(prev: ExecTraceManifest[], incoming: ExecTraceManifest[]): ExecTraceManifest[] {
  if (incoming.length === 0) return prev;
  const seen = new Set(prev.map((t) => t.trace_id));
  const merged = [...prev];
  for (const trace of incoming) {
    if (!seen.has(trace.trace_id)) {
      merged.push(trace);
      seen.add(trace.trace_id);
    }
  }
  return merged;
}

export function useExecTrace(limit = 80) {
  const { isDemo, isLive, isWarming } = useMindOverview();
  const runtimeOperationalReady = useMindStore((s) => s.runtimeOperationalReady);

  const [logs, setLogs] = useState<ExecLogEvent[]>(isDemo ? DEMO_EXEC_LOGS : []);
  const [traces, setTraces] = useState<ExecTraceManifest[]>([]);
  const [initialLoading, setInitialLoading] = useState(!isDemo);
  const [refreshing, setRefreshing] = useState(false);
  const hasLoadedRef = useRef(isDemo);

  useEffect(() => {
    if (isDemo) {
      setLogs(DEMO_EXEC_LOGS);
      setTraces([
        {
          trace_id: "demo-sigma-trace-001",
          graph_id: "ir-graph-demo",
          template_name: "chat_single_turn",
          status: "completed",
        },
      ]);
      setInitialLoading(false);
      hasLoadedRef.current = true;
    }
  }, [isDemo]);

  const refresh = useCallback(
    async (opts?: { initial?: boolean }) => {
      if (isDemo) {
        setLogs(DEMO_EXEC_LOGS);
        setTraces([
          {
            trace_id: "demo-sigma-trace-001",
            graph_id: "ir-graph-demo",
            template_name: "chat_single_turn",
            status: "completed",
          },
        ]);
        setInitialLoading(false);
        setRefreshing(false);
        hasLoadedRef.current = true;
        return;
      }
      if (!isLive && !isWarming) {
        setInitialLoading(false);
        setRefreshing(false);
        return;
      }

      const background = !opts?.initial && hasLoadedRef.current;
      if (background) setRefreshing(true);
      else setInitialLoading(true);

      try {
        const [logPayload, csePayload] = await Promise.all([
          cnexusProductApi.runtimeLogs(limit),
          cnexusProductApi.cseLive(120).catch(() => null),
        ]);
        const incomingLogs = logPayload.logs ?? [];
        const incomingTraces = csePayload?.exec_traces ?? [];
        setLogs((prev) =>
          hasLoadedRef.current ? mergeLogs(prev, incomingLogs, limit) : incomingLogs.slice(-limit),
        );
        setTraces((prev) =>
          hasLoadedRef.current ? mergeTraces(prev, incomingTraces) : incomingTraces,
        );
        hasLoadedRef.current = true;
      } finally {
        setInitialLoading(false);
        setRefreshing(false);
      }
    },
    [isDemo, isLive, isWarming, limit],
  );

  useEffect(() => {
    void refresh({ initial: !hasLoadedRef.current });
  }, [refresh]);

  useEffect(() => {
    if (runtimeOperationalReady) void refresh();
  }, [runtimeOperationalReady, refresh]);

  return {
    logs,
    traces,
    loading: initialLoading,
    initialLoading,
    refreshing,
    refresh,
  };
}
