/**
 * CNexus Runtime — Causal State Machine Graph (TypeScript mirror).
 * Used for UI diagnostics / React Flow; source of truth algorithms in
 * core/runtime/causal_state_graph.py
 *
 * @see docs/CNEXUS_CAUSAL_STATE_GRAPH.md
 */

export type TransitionKind = "causal" | "soft_illegal" | "hard_illegal" | "race";

export type CausalTransition = {
  id: string;
  source: string;
  target: string;
  guard: string;
  kind: TransitionKind;
  enabled: boolean;
};

export type WaitEdge = {
  waiter: string;
  waitsFor: string;
  condition: string;
};

export const CAUSAL_STATES = {
  INIT: "INIT",
  BOOT_0: "BOOT_0_API",
  BOOT_1: "BOOT_1_RUNTIME_SPAWNED",
  BOOT_2: "BOOT_2_HYDRATING",
  BOOT_3: "BOOT_3_COGNITIVE_WARMING",
  BOOT_3_STALL: "BOOT_3_STALL",
  BOOT_4: "BOOT_4_READY",
  GATE_L3_DRAIN: "GATE_L3_QUEUE_DRAINED",
  GATE_ADAPTER_DONE: "GATE_ADAPTER_DONE",
  GATE_BOOT4_CAUSAL: "GATE_BOOT4_CAUSAL_COMMIT",
  GATE_READY: "GATE_READY_EVALUATION",
  GATE_V5: "GATE_V5_CLUSTER_IDLE",
  GATE_RUST: "GATE_RUST_STATUS_READY",
  STATUS_WARMING: "STATUS_WARMING",
  STATUS_READY: "STATUS_READY",
  UI_LIVE: "UI_RUNTIME_LIVE",
} as const;

/** Formal transition relation T + banned edges for CNexus boot. */
export function buildCnexusBootGraph(): {
  states: string[];
  initial: string;
  transitions: CausalTransition[];
  waitEdges: WaitEdge[];
} {
  const S = CAUSAL_STATES;
  const transitions: CausalTransition[] = [
    { id: "t_init_api", source: S.INIT, target: S.BOOT_0, guard: "app_started", kind: "causal", enabled: true },
    { id: "t_spawn", source: S.BOOT_0, target: S.BOOT_1, guard: "runtime_pointer != null", kind: "causal", enabled: true },
    { id: "t_hydrate_start", source: S.BOOT_1, target: S.BOOT_2, guard: "hydrate_worker_started", kind: "causal", enabled: true },
    {
      id: "t_hydrate_done_cog",
      source: S.BOOT_2,
      target: S.BOOT_3,
      guard: "hydrate_complete && !cognitive_disabled",
      kind: "causal",
      enabled: true,
    },
    {
      id: "t_hydrate_done_skip",
      source: S.BOOT_2,
      target: S.BOOT_4,
      guard: "hydrate_complete && cognitive_disabled",
      kind: "causal",
      enabled: true,
    },
    {
      id: "t_l3_tick_drain",
      source: S.BOOT_3,
      target: S.GATE_L3_DRAIN,
      guard: "scheduler.run_tick()",
      kind: "causal",
      enabled: true,
    },
    { id: "t_l3_empty", source: S.GATE_L3_DRAIN, target: S.GATE_ADAPTER_DONE, guard: "queue_length == 0", kind: "causal", enabled: true },
    {
      id: "t_adapter_done",
      source: S.GATE_ADAPTER_DONE,
      target: S.GATE_BOOT4_CAUSAL,
      guard: "adapter.done == true",
      kind: "causal",
      enabled: true,
    },
    {
      id: "t_boot4_commit",
      source: S.GATE_BOOT4_CAUSAL,
      target: S.BOOT_4,
      guard: "mark_cognitive_warmup_done() causal ok",
      kind: "causal",
      enabled: true,
    },
    {
      id: "t_tick_budget",
      source: S.BOOT_3,
      target: S.BOOT_3_STALL,
      guard: "tick_budget_exhausted && queue_length > 0",
      kind: "causal",
      enabled: true,
    },
    {
      id: "t_stall_recover",
      source: S.BOOT_3_STALL,
      target: S.GATE_L3_DRAIN,
      guard: "L3 continues draining",
      kind: "causal",
      enabled: true,
    },
    { id: "t_ready_gate_pass", source: S.BOOT_4, target: S.GATE_READY, guard: "phase == BOOT_4", kind: "causal", enabled: true },
    {
      id: "t_ready_gate_block_cog",
      source: S.GATE_READY,
      target: S.STATUS_WARMING,
      guard: "_cognitive_warmup_blocks_ready()",
      kind: "causal",
      enabled: true,
    },
    {
      id: "t_ready_gate_block_v5",
      source: S.GATE_READY,
      target: S.STATUS_WARMING,
      guard: "v5_enabled && !cluster_idle",
      kind: "causal",
      enabled: true,
    },
    {
      id: "t_ready_gate_ok",
      source: S.GATE_READY,
      target: S.STATUS_READY,
      guard: "!blocks_ready && runtime_present && memory_ok",
      kind: "causal",
      enabled: true,
    },
    {
      id: "t_rust_probe",
      source: S.STATUS_READY,
      target: S.GATE_RUST,
      guard: 'JSON status == "ready" && runtime_pointer != false',
      kind: "causal",
      enabled: true,
    },
    { id: "t_ui_live", source: S.GATE_RUST, target: S.UI_LIVE, guard: "Tauri emit runtime-ready", kind: "causal", enabled: true },
    { id: "t_warming_stay", source: S.STATUS_WARMING, target: S.STATUS_WARMING, guard: "probe / poll", kind: "causal", enabled: true },
    // Banned
    {
      id: "t_force_boot4_ticks",
      source: S.BOOT_3,
      target: S.BOOT_4,
      guard: "tick_budget_exhausted (OPTIMISTIC)",
      kind: "hard_illegal",
      enabled: false,
    },
    {
      id: "t_force_boot4_timeout",
      source: S.BOOT_3,
      target: S.BOOT_4,
      guard: "cognitive_timeout 120s (OPTIMISTIC)",
      kind: "hard_illegal",
      enabled: false,
    },
    {
      id: "t_skipws_ready",
      source: S.STATUS_WARMING,
      target: S.UI_LIVE,
      guard: "JS skipWs / ready_fast (RACE)",
      kind: "race",
      enabled: false,
    },
  ];

  const waitEdges: WaitEdge[] = [
    { waiter: S.STATUS_READY, waitsFor: S.GATE_READY, condition: "evaluate_system_ready == ready" },
    { waiter: S.GATE_READY, waitsFor: S.GATE_L3_DRAIN, condition: "!_cognitive_warmup_blocks_ready" },
    { waiter: S.GATE_L3_DRAIN, waitsFor: S.BOOT_3, condition: "L3 scheduler ticks" },
    { waiter: S.UI_LIVE, waitsFor: S.GATE_RUST, condition: 'status == "ready"' },
    { waiter: S.GATE_RUST, waitsFor: S.STATUS_READY, condition: "HTTP /v1/system/ready" },
  ];

  return {
    states: Object.values(S),
    initial: S.INIT,
    transitions,
    waitEdges,
  };
}

export function reachabilityFromInit(
  graph: ReturnType<typeof buildCnexusBootGraph>,
): Record<string, number> {
  const dist: Record<string, number> = {};
  for (const s of graph.states) dist[s] = -1;
  const q: string[] = [graph.initial];
  dist[graph.initial] = 0;
  while (q.length) {
    const node = q.shift()!;
    for (const t of graph.transitions) {
      if (!t.enabled || t.kind !== "causal" || t.source !== node) continue;
      if (dist[t.target] < 0) {
        dist[t.target] = dist[node] + 1;
        q.push(t.target);
      }
    }
  }
  return dist;
}

export function illegalTransitions(graph: ReturnType<typeof buildCnexusBootGraph>): CausalTransition[] {
  return graph.transitions.filter((t) => !t.enabled || t.kind !== "causal");
}

/** Primary deadlock gate (historical + structural). */
export const PRIMARY_DEADLOCK_GATE = CAUSAL_STATES.GATE_READY;
