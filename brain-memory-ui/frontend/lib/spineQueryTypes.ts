export type SpineQueryResponse = {

  schema_version: string;

  trace_id: string;

  mode: string;

  events: Record<string, unknown>[];

  edges: { from: string; to: string; kind: string }[];

  subgraph?: {

    nodes: Record<string, unknown>[];

    edges: { from: string; to: string; kind: string }[];

  };

  causal?: {

    index_version?: string;

    enabled?: boolean;

    roots?: string[];

    chains?: { event_id: string; root_chain: string[]; root_cause: string }[];

    structural?: Record<string, unknown>;

    semantic?: {

      edges?: { from: string; to: string; relation: string }[];

      edge_count?: number;

    };

  };

  execution?: {

    version?: string;

    trace_id?: string;

    nodes?: Record<string, unknown>[];

    edges?: { from_id?: string; to_id?: string; from?: string; to?: string; kind: string; relation?: string }[];

    roots?: string[];

  };

  control: Record<string, unknown>[];

  state: {

    deltas: { event_id?: string; delta: unknown }[];

    patches?: { event_id?: string; delta: unknown }[];

  };

  explanation: {

    narrative?: string;

    rules?: string[];

    mode?: string;

    v2_summary?: string;

    causal_story?: string[];

    state_story?: string[];

    control_story?: string[];

    execution_narrative?: string;

    execution_path?: string[];

    execution_path_labels?: string[];

    execution_v2?: {

      version?: string;

      path_frames?: Array<{

        event_id: string;

        phase: string;

        event_type: string;

        summary?: string;

        drift_status?: string;

        confidence?: number;

      }>;

      drift_summary?: Record<string, unknown>;

      fusion_summary?: string;

    };

    v3_summary?: string;

    explain_v3?: {

      version?: string;

      summary?: string;

      caveats?: string[];

      epistemic_score?: number;

    };

    root_causes?:

      | {

          roots?: string[];

          chains?: { event_id: string; root_chain: string[]; root_cause: string }[];

        }

      | string[];

  };

  fusion_v2?: {

    version?: string;

    trace_id?: string;

    causal_chain?: Record<string, unknown>[];

    state_transitions?: Record<string, unknown>[];

    control_flow?: Record<string, unknown>[];

    explanation?: {

      summary?: string;

      causal_story?: string[];

      state_story?: string[];

      control_story?: string[];

    };

  };

  meta?: {

    source?: string;

    event_count?: number;

    edge_count?: number;

    semantic_edge_count?: number;

    node_count?: number;

    state_timeline?: Record<string, unknown>[];

    trace_validation?: {

      trace_id: string;

      complete: boolean;

      present: string[];

      missing: string[];

      event_count: number;

    };

    drift_summary?: {

      score: number;

      missing_count: number;

      extra_count: number;

      mismatch_count: number;

      runtime_count: number;

      spine_count: number;

      spine_sync_status: string;

      last_spine_event_id?: string | null;

    };

    drift_engine?: string;

    explain_engine?: string;

    identity?: {

      version?: string;

      identity?: string;

      equivalent_traces?: string[];

      drift_variants?: string[];

      identity_drift?: boolean;

    };

    identity_engine?: string;

  };

};

