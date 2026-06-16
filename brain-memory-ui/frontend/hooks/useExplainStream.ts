"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { getWsBase } from "@/lib/cnexusConfig";

export type ExplanationFrame = {
  version?: string;
  trace_id?: string;
  event_id?: string;
  frame_type?: string;
  execution_phase?: string;
  causal_delta?: { added_edges?: string[][]; graph_size?: number };
  state_delta?: {
    before?: Record<string, unknown>;
    after?: Record<string, unknown>;
    delta?: Record<string, unknown>;
  };
  control_delta?: { event_id?: string; decision?: string; policy?: string };
  narrative_delta?: string;
  feedback?: {
    evaluation?: { score?: number; quality?: string };
    drift?: Record<string, boolean>;
    control_state?: Record<string, boolean>;
    applied_to_runtime?: boolean;
  };
};

export type ExecutionFrame = {
  trace_id?: string;
  event_id?: string;
  event_type?: string;
  summary?: string;
  timestamp?: unknown;
  source?: string;
  drift_status?: string;
};

/** Unified execution subscription — WS open ≠ subscribed; wait for contract ack. */
export function useExplainStream(traceId: string | null, enabled: boolean) {
  const [frames, setFrames] = useState<ExplanationFrame[]>([]);
  const [executionFrames, setExecutionFrames] = useState<ExecutionFrame[]>([]);
  const [snapshot, setSnapshot] = useState<Record<string, unknown> | null>(null);
  const [socketOpen, setSocketOpen] = useState(false);
  const [subscribed, setSubscribed] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const heartbeatRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearHeartbeatTimer = useCallback(() => {
    if (heartbeatRef.current) {
      clearTimeout(heartbeatRef.current);
      heartbeatRef.current = null;
    }
  }, []);

  const markSubscribed = useCallback(() => {
    setSubscribed(true);
    clearHeartbeatTimer();
    heartbeatRef.current = setTimeout(() => setSubscribed(false), 8000);
  }, [clearHeartbeatTimer]);

  const disconnect = useCallback(() => {
    clearHeartbeatTimer();
    wsRef.current?.close();
    wsRef.current = null;
    setSocketOpen(false);
    setSubscribed(false);
  }, [clearHeartbeatTimer]);

  useEffect(() => {
    if (!enabled || !traceId?.trim()) {
      disconnect();
      setFrames([]);
      setExecutionFrames([]);
      setSnapshot(null);
      setError(null);
      return;
    }

    const wsUrl = `${getWsBase()}/v1/spine/stream?trace_id=${encodeURIComponent(traceId.trim())}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;
    setError(null);
    setFrames([]);
    setExecutionFrames([]);
    setSubscribed(false);

    ws.onopen = () => setSocketOpen(true);
    ws.onclose = () => {
      setSocketOpen(false);
      setSubscribed(false);
      clearHeartbeatTimer();
    };
    ws.onerror = () => setError("execution stream WebSocket failed");
    ws.onmessage = (msg) => {
      try {
        const data = JSON.parse(msg.data as string) as {
          type?: string;
          payload?: ExplanationFrame | ExecutionFrame | Record<string, unknown>;
        };
        if (data.type === "execution_stream_connected") {
          const payload = data.payload as { connected?: boolean } | undefined;
          if (payload?.connected) markSubscribed();
        }
        if (data.type === "execution_stream_heartbeat") {
          const payload = data.payload as { connected?: boolean } | undefined;
          if (payload?.connected) markSubscribed();
        }
        if (data.type === "execution_frame" && data.payload) {
          setExecutionFrames((prev) =>
            [...prev, data.payload as ExecutionFrame].slice(-200),
          );
        }
        if (data.type === "explanation_frame" && data.payload) {
          setFrames((prev) => [...prev, data.payload as ExplanationFrame].slice(-200));
        }
        if (data.type === "explanation_snapshot") {
          setSnapshot((data.payload as Record<string, unknown>) ?? null);
        }
      } catch {
        /* ignore malformed */
      }
    };

    return () => {
      ws.close();
      wsRef.current = null;
      clearHeartbeatTimer();
    };
  }, [traceId, enabled, disconnect, markSubscribed, clearHeartbeatTimer]);

  return {
    frames,
    executionFrames,
    snapshot,
    connected: subscribed,
    socketOpen,
    subscribed,
    error,
    disconnect,
  };
}
