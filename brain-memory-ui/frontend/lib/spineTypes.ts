import type { GtbsRawEvent } from "./api";

export type SpineEventType =
  | "dispatch"
  | "recall"
  | "write_intent"
  | "cdg"
  | "capture"
  | "ir"
  | "chat"
  | "control";

export type SpineSubsystem = "runtime" | "gtbs" | "cdg" | "control_plane";

export type SpineAction = "read" | "mutate" | "propose" | "commit" | "reject";

export type SpineDecision = "ALLOW" | "WARN" | "REJECT";

export type SpineEvent = {
  event_id: string;
  trace_id: string;
  timestamp: number;
  event_type: SpineEventType;
  subsystem: SpineSubsystem;
  action: SpineAction;
  parent_event_id?: string;
  causal_links?: string[];
  summary: string;
  write_intent?: {
    intent_id: string;
    kind: string;
    mutability: "explicit" | "implicit" | "advisory" | string;
    shadow: boolean;
    phase?: string;
  };
  decision?: {
    decision: SpineDecision;
    entry: string;
    caller: string;
    hard_gate: boolean;
    reason?: string;
  };
  provenance?: {
    caller: string;
    channel: string;
    entry_registry: string;
    dispatch_kind?: string;
    runtime_token?: string;
  };
  state_delta?: {
    memory?: string[];
    working_self?: string[];
    graph?: string[];
    vector?: string[];
  };
  raw?: GtbsRawEvent;
};

export type DebuggerView = "timeline" | "graph";

export type SpineFilters = {
  eventTypes: string[];
  mutability: string[];
  callers: string[];
  decisions: string[];
};

export const EMPTY_SPINE_FILTERS: SpineFilters = {
  eventTypes: [],
  mutability: [],
  callers: [],
  decisions: [],
};
