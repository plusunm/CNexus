export type CostLevel = "low" | "mid" | "high" | "spike";

export type TokenTrace = {
  trace_id: string;
  tokens_in: number;
  tokens_out: number;
  total: number;
  mode: string;
  cost_level: CostLevel;
  entry: string;
  event_count?: number;
};

export type TokenEventRow = {
  trace_id: string;
  event_id: string;
  source: string;
  tokens_in: number;
  tokens_out: number;
  total: number;
  spine_event_id?: string | null;
  causal_edge_id?: string | null;
  identity_id?: string | null;
  phase: string;
  mode?: string;
  entry?: string;
  cost_level?: CostLevel;
  timestamp?: number;
};

export type TokenWeightedEdge = {
  from: string;
  to: string;
  kind?: string;
  base_weight?: number;
  token_weight?: number;
  influenced?: boolean;
};

export type TokenHotPath = {
  from: string;
  to: string;
  severity: string;
  weight: number;
};

export type TokenField = {
  trace_id: string;
  total_cost: number;
  total_tokens: number;
  field: Record<string, number>;
  gradient: Record<string, number>;
  by_phase: Record<string, number>;
  bindings: { spine_event_id: string; tokens: number }[];
  influence?: {
    hot_paths: TokenHotPath[];
    max_weight: number;
  };
  identity_id?: string | null;
  token_events?: TokenEventRow[];
  causal?: {
    nodes: unknown[];
    edges: TokenWeightedEdge[];
  };
};

export type TokenTraceReport = TokenField;

export type TokenObservatoryResponse = {
  token_traces: TokenTrace[];
  count: number;
};

export type TokenTab =
  | "overview"
  | "events"
  | "field"
  | "binding"
  | "influence"
  | "identity";
