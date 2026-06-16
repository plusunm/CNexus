/** Spine Front Contract v1 — frontend single source of truth (renderer only). */

export type TraceStreamStatus = "LIVE" | "REPLAY" | "OFFLINE" | "STALE";

export type TraceContext = {
  trace_id: string;
  status: TraceStreamStatus;
  source: "execution_spine";
  event_count: number;
  semantic_edge_count?: number;
};

export type ExecutionNodeView = {
  event_id: string;
  trace_id: string;
  phase: string;
  event_type: string;
  entry?: string;
  actor?: string;
  timestamp?: string;
  summary?: string;
};

export type ExecutionEdgeView = {
  from: string;
  to: string;
  kind: "triggers" | "controls" | "executes" | "mutates" | "observes" | string;
  relation?: string;
};

export type ExecutionDagView = {
  version?: string;
  trace_id: string;
  nodes: ExecutionNodeView[];
  edges: ExecutionEdgeView[];
  roots: string[];
};

export type DriftStatus = "OK" | "MISSING" | "EXTRA" | "SUSPECT";

export type ExecutionIdentityView = {
  version?: string;
  identity: string;
  signatures?: Record<string, string>;
  equivalent_traces?: string[];
  drift_variants?: string[];
  identity_drift?: boolean;
  identity_mismatch?: boolean;
};

/** Top-level identity bundle (header + panel) — mapped in mapContract. */
export type ExecutionIdentityBundleView = {
  id: string;
  stability: number;
  drift: boolean;
  equivalent_traces: string[];
  drift_variants: string[];
  signatures: {
    graph: string;
    state: string;
    control: string;
    causal: string;
  };
  identity_note?: string;
};

export type DriftSummaryView = {
  score: number;
  missing_count: number;
  extra_count: number;
  mismatch_count: number;
  runtime_count: number;
  spine_count: number;
  spine_sync_status: "partial" | "synced" | "drifted" | string;
  last_spine_event_id?: string | null;
  identity?: string;
  identity_drift?: boolean;
  identity_mismatch?: boolean;
};

export type SpineEventView = {
  event_id: string;
  type: string;
  timestamp?: number;
  trace_id: string;
  entry?: string;
  summary?: string;
  subsystem?: string;
  action?: string;
  decision?: string;
  payload?: Record<string, unknown>;
  state_delta?: Record<string, unknown>;
  causal_edges?: Array<{ from: string; to: string; relation: string }>;
  drift_status?: DriftStatus;
  confidence?: number;
  raw: Record<string, unknown>;
};

export type SpineEdgeView = {
  from: string;
  to: string;
  kind: "temporal" | "triggered_by" | "control_flow" | "parent" | string;
};

export type StatePatchView = {
  event_id?: string;
  timestamp?: string;
  mutation_label?: string;
  before?: Record<string, unknown>;
  after?: Record<string, unknown>;
  changes?: unknown[];
  change_count?: number;
};

export type ControlDecisionView = {
  event_id: string;
  decision: "ALLOW" | "WARN" | "REJECT" | string;
  rule?: string;
  caller?: string;
  entry?: string;
};

export type CausalChainView = {
  root: string;
  path: string[];
  confidence?: number;
};

export type SpineFrontContractV1 = {
  trace_id: string;
  trace: TraceContext;

  /** Execution identity class (CP-3 EIV) */
  identity: ExecutionIdentityBundleView | null;

  events: SpineEventView[];
  edges: SpineEdgeView[];

  execution: {
    timeline: SpineEventView[];
    dag: ExecutionDagView;
  };

  causal: {
    enabled: boolean;
    roots: string[];
    chains: CausalChainView[];
    stream: Array<{ from: string; to: string; relation: string; label?: string }>;
  };

  state: {
    version: "tier-a";
    patches: StatePatchView[];
    timeline: StatePatchView[];
  };

  control: {
    decisions: ControlDecisionView[];
  };

  explanation: {
    narrative: string;
    root_causes: string[];
    causal_story?: string[];
    state_story?: string[];
    control_story?: string[];
    execution_narrative?: string;
    execution_path_labels?: string[];
    v3_summary?: string;
    explain_v3?: {
      version?: string;
      summary?: string;
      caveats?: string[];
      epistemic_score?: number;
      causal_story?: string[];
      state_story?: string[];
      control_story?: string[];
      identity_note?: string;
      identity?: ExecutionIdentityView;
    };
    execution_v2?: {
      version?: string;
      path_frames?: Array<{
        event_id: string;
        phase: string;
        event_type: string;
        summary?: string;
        drift_status?: DriftStatus;
        confidence?: number;
      }>;
      drift_summary?: DriftSummaryView;
      fusion_summary?: string;
    };
  };

  stream?: {
    explain_ws: boolean;
    last_frame_id?: string;
    live: boolean;
  };

  meta: {
    source: "spine-query-v1" | "spine-query-v2" | "spine-query-v3";
    latency_ms?: number;
    partial?: boolean;
    schema_version?: string;
    drift_summary?: DriftSummaryView;
    explain_engine?: string;
    identity?: ExecutionIdentityView;
    identity_engine?: string;
  };

  _raw?: Record<string, unknown>;
};

export type SpineQueryTab =
  | "execution"
  | "causal"
  | "state"
  | "control"
  | "explain"
  | "inspector";

export const EXECUTION_EVENT_TYPES = new Set([
  "dispatch",
  "chat",
  "recall",
  "memory_mutation",
  "llm_call",
  "state",
  "state_patch",
  "control",
  "capture",
  "write_intent",
]);
