/** UI polling intervals — HTTP fallback tiers (WS handles realtime). */

/** CSE live synthesis — summary panels. */
export const CSE_POLL_MS = 30_000;

/** Debugger spine GTBS — incremental append, slow HTTP backup. */
export const SPINE_LIVE_POLL_MS = 20_000;

/** Execution / Ollama status card. */
export const EXECUTION_STATUS_POLL_MS = 30_000;

/** Authoritative ready gate on dashboard (full mode). */
export const RUNTIME_FULL_PROBE_MS = 60_000;

/** Faster capability poll while chat is live but upload (full_ready) is still warming. */
export const RUNTIME_UPLOAD_PROBE_MS = 5_000;

/** Float bar steady-state ready probe (separate WebView). */
export const FLOAT_IDLE_PROBE_MS = 60_000;
