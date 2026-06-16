/** Runtime-configurable endpoints + edition (single installer). */

import {
  parseEdition,
  resolveEdition,
  saveStoredEdition,
  setEdition,
  loadStoredEdition,
  type CnexusEdition,
} from "@/cnexus-kernel/edition";

let apiBase = process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000";
let wsBase = process.env.NEXT_PUBLIC_WS_BASE ?? "ws://127.0.0.1:8000";
let apiToken = "";
let configEdition: CnexusEdition | undefined;

export function getApiToken(): string {
  return apiToken;
}

export function getApiBase(): string {
  return apiBase;
}

export function getWsBase(): string {
  return wsBase;
}

export function setCnexusEndpoints(nextApi: string, nextWs?: string): void {
  apiBase = nextApi.replace(/\/$/, "");
  wsBase = (nextWs ?? nextApi.replace(/^http/, "ws")).replace(/\/$/, "");
}

export function activateEnterpriseEdition(): void {
  setEdition("enterprise");
  saveStoredEdition("enterprise");
}

/** Load cnexus-config.json — written by installer or Docker entrypoint. */
export async function initCnexusConfig(): Promise<void> {
  if (typeof window === "undefined") return;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 3000);
  try {
    const res = await fetch("/cnexus-config.json", {
      cache: "no-store",
      signal: controller.signal,
    });
    if (!res.ok) return;
    const cfg = (await res.json()) as {
      edition?: string;
      apiBase?: string;
      wsBase?: string;
      apiToken?: string;
    };
    configEdition = parseEdition(cfg.edition);
    if (cfg.apiBase) setCnexusEndpoints(cfg.apiBase, cfg.wsBase);
    if (cfg.apiToken) apiToken = cfg.apiToken;
  } catch {
    /* defaults: local bundled runtime */
  } finally {
    clearTimeout(timer);
    const edition = resolveEdition(configEdition, loadStoredEdition());
    setEdition(edition);
  }
}
