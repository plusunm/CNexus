/** Best-effort probes from the UI when Runtime API is offline. */

import { isTauriDesktop } from "@/lib/tauriDesktop";

const OLLAMA_HOSTS = ["http://127.0.0.1:11434", "http://localhost:11434"];

export type OllamaLocalProbe = {
  reachable: boolean;
  host: string | null;
  modelCount: number;
  ollamaHostEnv?: string | null;
  attempts?: string[];
  error?: string | null;
};

async function probeOllamaViaTauri(): Promise<OllamaLocalProbe | null> {
  if (!isTauriDesktop()) return null;
  try {
    const { invoke } = await import("@tauri-apps/api/core");
    const result = await invoke<OllamaLocalProbe>("probe_ollama_local");
    return result;
  } catch {
    return null;
  }
}

async function probeOllamaViaFetch(timeoutMs: number): Promise<OllamaLocalProbe> {
  for (const host of OLLAMA_HOSTS) {
    try {
      const ctrl = new AbortController();
      const timer = window.setTimeout(() => ctrl.abort(), timeoutMs);
      const res = await fetch(`${host}/api/tags`, { signal: ctrl.signal, method: "GET" });
      window.clearTimeout(timer);
      if (res.ok) {
        let modelCount = 0;
        try {
          const body = (await res.json()) as { models?: unknown[] };
          modelCount = body.models?.length ?? 0;
        } catch {
          /* tags body optional */
        }
        return { reachable: true, host, modelCount };
      }
    } catch {
      /* try next host */
    }
  }
  return { reachable: false, host: null, modelCount: 0 };
}

export async function probeLocalOllamaDetail(timeoutMs = 2000): Promise<OllamaLocalProbe> {
  const tauri = await probeOllamaViaTauri();
  if (tauri) return tauri;
  return probeOllamaViaFetch(timeoutMs);
}

export async function probeLocalOllama(timeoutMs = 2000): Promise<boolean> {
  const result = await probeLocalOllamaDetail(timeoutMs);
  return result.reachable;
}

export function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}
