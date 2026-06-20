/**
 * Tauri SecurityBootstrap bridge — preflight, license status, heartbeat.
 */

import { invoke } from "@tauri-apps/api/core";

export type SecurityBootstrapResult = {
  ok: boolean;
  runtime_mode: "Trusted" | "OfflineGrace" | "Degraded" | "Locked" | string;
  user_message: string;
  internal_code: string;
  edition: "personal" | "enterprise" | string;
  machine_fingerprint: string;
  license_present: boolean;
  granted_features: string[];
  issues: Array<{ code: string; detail: string }>;
};

export type LicenseStatusSnapshot = {
  ok: boolean;
  runtime_mode: string;
  license_valid: boolean;
  grace_until: number;
  grace_remaining_sec: number;
  heartbeat_fail_count: number;
  granted_features: string[];
  user_message: string;
};

export async function runSecurityBootstrapPreflight(
  dryRun = false,
): Promise<SecurityBootstrapResult> {
  return invoke<SecurityBootstrapResult>("security_bootstrap_preflight", {
    dryRun,
  });
}

export async function fetchLicenseStatus(): Promise<LicenseStatusSnapshot> {
  return invoke<LicenseStatusSnapshot>("security_bootstrap_license_status");
}

export async function postSessionHeartbeat(): Promise<LicenseStatusSnapshot> {
  return invoke<LicenseStatusSnapshot>("security_bootstrap_heartbeat");
}

const DEFAULT_HEARTBEAT_MS = 10 * 60 * 1000;

let heartbeatTimer: ReturnType<typeof setInterval> | null = null;
let heartbeatListener: ((snap: LicenseStatusSnapshot) => void) | null = null;

/** Poll Runtime /v1/session/heartbeat via Tauri command. */
export function startSecurityHeartbeat(
  intervalMs = DEFAULT_HEARTBEAT_MS,
  onUpdate?: (snap: LicenseStatusSnapshot) => void,
): void {
  stopSecurityHeartbeat();
  heartbeatListener = onUpdate ?? null;

  const tick = async () => {
    try {
      const snap = await postSessionHeartbeat();
      heartbeatListener?.(snap);
    } catch {
      // Runtime may still be warming — ignore transient errors.
    }
  };

  void tick();
  heartbeatTimer = setInterval(() => void tick(), intervalMs);
}

export function stopSecurityHeartbeat(): void {
  if (heartbeatTimer) {
    clearInterval(heartbeatTimer);
    heartbeatTimer = null;
  }
  heartbeatListener = null;
}

/** Desktop boot: preflight before relying on Runtime. */
export async function securityBootstrapOnBoot(): Promise<SecurityBootstrapResult> {
  const preflight = await runSecurityBootstrapPreflight(false);
  if (!preflight.ok) {
    return preflight;
  }
  return preflight;
}

export function featureAllowed(
  snap: LicenseStatusSnapshot | SecurityBootstrapResult,
  capabilityId: string,
): boolean {
  return snap.granted_features.includes(capabilityId);
}
