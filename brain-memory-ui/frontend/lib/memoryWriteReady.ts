import type { EffectiveConnectionMode } from "@/cnexus-kernel/connectionMode";
import { useMindStore } from "@/cnexus-kernel/MindStore";

import { cnexusProductApi } from "@/lib/api";

export type MemoryWriteGate = {
  isDemo: boolean;
  isWarming: boolean;
  isFallback: boolean;
  canWriteMemory: boolean;
  /** Operational ready — chat/API up but upload may still wait for full_ready. */
  isLive?: boolean;
};

export type MemoryWriteReadyResult = {
  ok: boolean;
  hint: string | null;
};

/** Accepted extensions for document ingest (PDF / Word / text). */
export const DOCUMENT_ACCEPT = ".pdf,.doc,.docx,.txt,.md,.markdown";

const FULL_READY_POLL_MS = 1_500;
const FULL_READY_POLL_MAX_MS = 90_000;

export function buildMemoryWriteGate(effectiveMode: EffectiveConnectionMode): MemoryWriteGate {
  const state = useMindStore.getState();
  const isDemo = effectiveMode === "demo";
  const isFallback = effectiveMode === "fallback";
  const isLive =
    effectiveMode === "runtime" &&
    (state.runtimeOperationalReady || state.runtimeCapabilities.chat);
  const isWarming = effectiveMode === "runtime" && state.runtimeReachable && !isLive;
  const canWriteMemory =
    isDemo ||
    (effectiveMode === "runtime" &&
      (state.runtimeCapabilities.upload || state.runtimeReady));
  return { isDemo, isWarming, isFallback, canWriteMemory, isLive };
}

export function memoryWriteStatusHint(gate: MemoryWriteGate): string | null {
  if (gate.isDemo) return null;
  if (gate.canWriteMemory) return null;
  if (gate.isFallback) return "当前为离线模式，请连接 Runtime 或切换演示模式";
  if (gate.isWarming) return "Runtime 正在启动，请稍候再导入";
  if (gate.isLive) return "认知索引构建中，上传将在完全就绪后开放";
  return "Runtime 未连接，请先启动应用并等待「运行时已连接」";
}

function uploadBlockedHint(gate: MemoryWriteGate): string {
  return memoryWriteStatusHint(gate) ?? "Runtime 未连接，无法导入";
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

async function verifyRuntimeWritePath(): Promise<{ ok: boolean; hint: string | null }> {
  try {
    await cnexusProductApi.memoryStats();
    return { ok: true, hint: null };
  } catch (err) {
    void useMindStore.getState().syncSystemCapability();
    const message =
      err instanceof Error && err.message.trim()
        ? err.message
        : "记忆写入路径不可用，请稍后再试";
    return { ok: false, hint: message };
  }
}

/** Probe full ready + write path before ingest. Polls capability when chat is live but upload waits. */
export async function ensureMemoryWriteReady(
  gate?: MemoryWriteGate,
  options?: { pollForFull?: boolean },
): Promise<MemoryWriteReadyResult> {
  const pollForFull = options?.pollForFull !== false;
  const store = useMindStore.getState();
  let current = gate ?? buildMemoryWriteGate(store.effectiveMode);

  if (current.isDemo) return { ok: true, hint: null };
  if (current.isFallback) return { ok: false, hint: uploadBlockedHint(current) };

  const deadline = Date.now() + FULL_READY_POLL_MAX_MS;

  while (Date.now() < deadline) {
    await store.syncSystemCapability();
    current = buildMemoryWriteGate(store.effectiveMode);

    if (current.isFallback) return { ok: false, hint: uploadBlockedHint(current) };

    if (current.canWriteMemory) {
      const probe = await verifyRuntimeWritePath();
      if (probe.ok) return { ok: true, hint: null };
      return { ok: false, hint: probe.hint ?? uploadBlockedHint(current) };
    }

    if (!current.isLive && !current.isWarming) {
      return { ok: false, hint: uploadBlockedHint(current) };
    }

    if (!pollForFull) {
      return { ok: false, hint: uploadBlockedHint(current) };
    }

    await sleep(FULL_READY_POLL_MS);
  }

  return { ok: false, hint: uploadBlockedHint(current) };
}

export function formatImportError(err: unknown, fallback: string): string {
  if (err instanceof Error && err.message.trim()) return err.message;
  return fallback;
}
