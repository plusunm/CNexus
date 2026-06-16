/** Progressive capability model — mirrors /v1/system/capability SSOT. */

export type RuntimeCapabilities = {
  api: boolean;
  memory: boolean;
  chat: boolean;
  upload: boolean;
  llm: boolean;
  full: boolean;
};

export type SystemCapabilitySnapshot = {
  status: string;
  operational_ready: boolean;
  full_ready: boolean;
  cognitive_status: "ready" | "warming" | "offline" | string;
  capabilities: RuntimeCapabilities;
  ready_for_chat: boolean;
  ready_for_upload: boolean;
  boot_phase?: string | null;
  reason?: string | null;
  progress?: number | null;
  ws?: string;
};

export const EMPTY_CAPABILITIES: RuntimeCapabilities = {
  api: false,
  memory: false,
  chat: false,
  upload: false,
  llm: false,
  full: false,
};

export function parseCapabilityPayload(raw: Record<string, unknown>): SystemCapabilitySnapshot {
  const caps = (raw.capabilities as Record<string, unknown> | undefined) ?? {};
  return {
    status: String(raw.status ?? "warming"),
    operational_ready: Boolean(raw.operational_ready),
    full_ready: Boolean(raw.full_ready),
    cognitive_status: String(raw.cognitive_status ?? "warming"),
    capabilities: {
      api: Boolean(caps.api),
      memory: Boolean(caps.memory),
      chat: Boolean(caps.chat ?? raw.ready_for_chat),
      upload: Boolean(caps.upload ?? raw.ready_for_upload),
      llm: Boolean(caps.llm),
      full: Boolean(caps.full ?? raw.full_ready),
    },
    ready_for_chat: Boolean(raw.ready_for_chat ?? caps.chat),
    ready_for_upload: Boolean(raw.ready_for_upload ?? caps.upload),
    boot_phase: (raw.boot_phase as string | undefined) ?? null,
    reason: (raw.reason as string | null | undefined) ?? null,
    progress: typeof raw.progress === "number" ? raw.progress : null,
    ws: raw.ws as string | undefined,
  };
}

export function capabilityConnectionPhase(
  snap: SystemCapabilitySnapshot,
): "ready" | "warming" | "offline" {
  if (snap.operational_ready || snap.ready_for_chat) return "ready";
  if (snap.status === "warming" || snap.capabilities.api) return "warming";
  return "offline";
}
