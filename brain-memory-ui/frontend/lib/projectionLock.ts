/**
 * CP-3 UI Projection Lock — UI may only treat ExecutionRecord as truth.
 */

export function projectionLockEnabled(): boolean {
  const raw = process.env.NEXT_PUBLIC_CNEXUS_PROJECTION_LOCK ?? "1";
  return !["0", "false", "no", "off"].includes(raw.trim().toLowerCase());
}

export function debugSpineEnabled(): boolean {
  const raw = process.env.NEXT_PUBLIC_CNEXUS_DEBUG_SPINE ?? "0";
  return ["1", "true", "yes", "on"].includes(raw.trim().toLowerCase());
}

export function assertProjectionSource(url: string): void {
  if (!projectionLockEnabled()) return;
  if (url.includes("/v1/kernel/record") || url.includes("/v1/kernel/capabilities")) return;
  if (debugSpineEnabled()) return;
  throw new Error(`UI Projection Lock Violation: ${url}`);
}
