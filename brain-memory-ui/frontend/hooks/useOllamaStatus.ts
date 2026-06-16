"use client";

import { useCallback, useMemo, useState } from "react";
import { brainApi } from "@/lib/api";
import { useExecutionStatus } from "./useExecutionStatus";

export type OllamaRuntimeStatus = {
  installed: boolean;
  binaryFound: boolean;
  running: boolean;
  host: string;
  downloadUrl: string;
  binaryPath: string | null;
  loading: boolean;
  actionLoading: boolean;
  error: string | null;
  runtimeConnected: boolean;
  localOllamaReachable: boolean;
  suggestedActions: string[];
};

export function useOllamaStatus() {
  const { status, refresh } = useExecutionStatus();
  const [actionLoading, setActionLoading] = useState(false);

  const mapped = useMemo<OllamaRuntimeStatus>(() => {
    const ollama = status.ollama ?? {};
    const running = Boolean(ollama.running);
    return {
      installed: Boolean(ollama.installed),
      binaryFound: Boolean(ollama.binary_found),
      running,
      host: String(ollama.host ?? "http://127.0.0.1:11434"),
      downloadUrl: String(ollama.download_url ?? "https://ollama.com/download"),
      binaryPath: (ollama.binary_path as string | null | undefined) ?? null,
      loading: status.loading,
      actionLoading,
      error: status.error,
      runtimeConnected: status.runtimeConnected,
      localOllamaReachable: status.localOllamaReachable,
      suggestedActions: status.suggestedActions,
    };
  }, [status, actionLoading]);

  const start = useCallback(async () => {
    setActionLoading(true);
    try {
      const payload = await brainApi.ollamaStart();
      if (!payload.ok && payload.detail === "not_installed") {
        await refresh();
        return { ok: false as const, reason: "not_installed" as const };
      }
      await refresh();
      return { ok: payload.ok, reason: payload.detail };
    } catch (err) {
      const message = err instanceof Error ? err.message : "启动 Ollama 失败";
      return { ok: false as const, reason: message };
    } finally {
      setActionLoading(false);
    }
  }, [refresh]);

  const stop = useCallback(async () => {
    setActionLoading(true);
    try {
      const payload = await brainApi.ollamaStop();
      await refresh();
      if (payload.detail === "externally_managed") {
        return {
          ok: false as const,
          reason: "Ollama 由系统托盘管理，请从 Ollama 应用退出",
        };
      }
      return { ok: payload.ok, reason: payload.detail };
    } catch (err) {
      const message = err instanceof Error ? err.message : "关闭 Ollama 失败";
      return { ok: false as const, reason: message };
    } finally {
      setActionLoading(false);
    }
  }, [refresh]);

  return { status: mapped, refresh, start, stop };
}

export type OllamaUiPhase =
  | "loading"
  | "runtime_offline"
  | "demo"
  | "not_installed"
  | "stopped"
  | "running"
  | "error";

export function deriveOllamaUiPhase(status: OllamaRuntimeStatus): OllamaUiPhase {
  if (status.loading || status.actionLoading) return "loading";
  if (status.error?.includes("Demo")) return "demo";
  if (!status.runtimeConnected) {
    if (status.running) return "running";
    return "runtime_offline";
  }
  if (status.running) return "running";
  if (status.installed || status.binaryFound) return "stopped";
  if (status.error) return "error";
  return "not_installed";
}
