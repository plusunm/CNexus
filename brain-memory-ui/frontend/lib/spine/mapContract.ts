import type { SpineQueryResponse } from "@/lib/spineQueryTypes";
import type {
  ControlDecisionView,
  CausalChainView,
  ExecutionDagView,
  SpineEdgeView,
  SpineEventView,
  SpineFrontContractV1,
  StatePatchView,
  TraceStreamStatus,
} from "./contract";
import { EXECUTION_EVENT_TYPES } from "./contract";
import { buildIdentityBundle } from "./identityView";

function parseTimestamp(value: unknown): number | undefined {
  if (typeof value === "number") return value;
  if (typeof value === "string" && value) {
    const ms = Date.parse(value);
    return Number.isNaN(ms) ? undefined : ms;
  }
  return undefined;
}

function mapEvent(row: Record<string, unknown>, traceId: string): SpineEventView {
  const driftStatus = row.drift_status as SpineEventView["drift_status"] | undefined;
  const confidence = typeof row.confidence === "number" ? row.confidence : undefined;
  return {
    event_id: String(row.event_id ?? ""),
    type: String(row.event_type ?? row.type ?? "unknown"),
    timestamp: parseTimestamp(row.timestamp),
    trace_id: String(row.trace_id ?? traceId),
    entry: row.entry != null ? String(row.entry) : undefined,
    summary: row.summary != null ? String(row.summary) : undefined,
    subsystem: row.subsystem != null ? String(row.subsystem) : undefined,
    action: row.action != null ? String(row.action) : undefined,
    decision: row.decision != null ? String(row.decision) : undefined,
    payload: (row.payload as Record<string, unknown>) ?? undefined,
    state_delta: (row.state_delta as Record<string, unknown>) ?? undefined,
    causal_edges: Array.isArray(row.causal_edges)
      ? (row.causal_edges as Array<{ from: string; to: string; relation: string }>)
      : undefined,
    drift_status: driftStatus,
    confidence,
    raw: row,
  };
}

function mapChains(raw: SpineQueryResponse): CausalChainView[] {
  const chains = raw.causal?.chains ?? [];
  return chains.map((c) => ({
    root: String(c.root_cause ?? c.event_id ?? ""),
    path: Array.isArray(c.root_chain) ? c.root_chain.map(String) : [],
  }));
}

function mapStateTimeline(raw: SpineQueryResponse): StatePatchView[] {
  const timeline = raw.meta?.state_timeline;
  if (Array.isArray(timeline) && timeline.length) {
    return timeline.map((step) => {
      const s = step as Record<string, unknown>;
      return {
        event_id: s.event_id != null ? String(s.event_id) : undefined,
        timestamp: s.timestamp != null ? String(s.timestamp) : undefined,
        mutation_label:
          (s.mutation_label as string) ??
          ((s.state_delta as Record<string, unknown> | undefined)?.mutation_label as string | undefined),
        before: (s.before as Record<string, unknown>) ?? undefined,
        after: (s.after as Record<string, unknown>) ?? undefined,
        changes: (s.delta as unknown[]) ?? (s.changes as unknown[]),
        change_count: typeof s.change_count === "number" ? s.change_count : undefined,
      };
    });
  }

  const patches = raw.state?.patches ?? raw.state?.deltas ?? [];
  return patches.map((p) => {
    const row = p as { event_id?: string; delta?: Record<string, unknown> };
    const delta = row.delta ?? {};
    return {
      event_id: row.event_id,
      changes: (delta.changes as unknown[]) ?? [],
      change_count: typeof delta.change_count === "number" ? delta.change_count : undefined,
      before: undefined,
      after: undefined,
    };
  });
}

function mapControl(raw: SpineQueryResponse): ControlDecisionView[] {
  return (raw.control ?? []).map((row) => {
    const r = row as Record<string, unknown>;
    return {
      event_id: String(r.event_id ?? ""),
      decision: String(r.decision ?? "ALLOW"),
      rule: r.route_kind != null ? String(r.route_kind) : undefined,
      caller: r.caller != null ? String(r.caller) : undefined,
      entry: r.entry != null ? String(r.entry) : undefined,
    };
  });
}

function mapEdges(raw: SpineQueryResponse): SpineEdgeView[] {
  const semantic = raw.causal?.semantic as
    | { edges?: { from: string; to: string; relation: string }[] }
    | undefined;
  if (semantic?.edges?.length) {
    return semantic.edges.map((e) => ({
      from: String(e.from),
      to: String(e.to),
      kind: String(e.relation ?? "temporal"),
    }));
  }
  return (raw.edges ?? []).map((e) => ({
    from: e.from,
    to: e.to,
    kind: (e.kind as SpineEdgeView["kind"]) ?? "parent",
  }));
}

function buildCausalStream(events: SpineEventView[], edges: SpineEdgeView[]) {
  const byId = new Map(events.map((e) => [e.event_id, e]));
  return edges.map((edge) => {
    const fromEv = byId.get(edge.from);
    const toEv = byId.get(edge.to);
    const label = `${fromEv?.type ?? edge.from} → ${toEv?.type ?? edge.to}`;
    return { from: edge.from, to: edge.to, relation: edge.kind, label };
  });
}

function mapExecutionDag(raw: SpineQueryResponse, traceId: string): ExecutionDagView {
  const ex = raw.execution;
  if (ex?.nodes?.length) {
    return {
      version: ex.version,
      trace_id: String(ex.trace_id ?? traceId),
      nodes: ex.nodes.map((n) => {
        const row = n as Record<string, unknown>;
        return {
          event_id: String(row.event_id ?? ""),
          trace_id: String(row.trace_id ?? traceId),
          phase: String(row.phase ?? ""),
          event_type: String(row.event_type ?? ""),
          entry: row.entry != null ? String(row.entry) : undefined,
          actor: row.actor != null ? String(row.actor) : undefined,
          timestamp: row.timestamp != null ? String(row.timestamp) : undefined,
          summary: row.summary != null ? String(row.summary) : undefined,
        };
      }),
      edges: (ex.edges ?? []).map((e) => ({
        from: String(e.from_id ?? e.from ?? ""),
        to: String(e.to_id ?? e.to ?? ""),
        kind: String(e.kind ?? "executes"),
        relation: e.relation,
      })),
      roots: (ex.roots ?? []).map(String),
    };
  }
  return { trace_id: traceId, nodes: [], edges: [], roots: [] };
}

export function mapToSpineFrontContract(
  raw: SpineQueryResponse,
  opts?: { streamStatus?: TraceStreamStatus; latencyMs?: number },
): SpineFrontContractV1 {
  const traceId = raw.trace_id;
  const events = (raw.events ?? []).map((e) => mapEvent(e as Record<string, unknown>, traceId));
  const edges = mapEdges(raw);
  const stateTimeline = mapStateTimeline(raw);

  const executionTimeline = [...events]
    .filter((e) => EXECUTION_EVENT_TYPES.has(e.type))
    .sort((a, b) => (a.timestamp ?? 0) - (b.timestamp ?? 0));

  const rc = raw.explanation?.root_causes;
  let rootCauses: string[] = raw.causal?.roots ?? [];
  if (rc && typeof rc === "object" && !Array.isArray(rc)) {
    const roots = (rc as { roots?: string[] }).roots;
    if (roots?.length) rootCauses = roots.map(String);
  } else if (Array.isArray(rc)) {
    rootCauses = rc.map(String);
  }

  const partial: SpineFrontContractV1 = {
    trace_id: traceId,
    identity: null,
    trace: {
      trace_id: traceId,
      status: opts?.streamStatus ?? "REPLAY",
      source: "execution_spine",
      event_count: raw.meta?.event_count ?? events.length,
      semantic_edge_count: raw.meta?.semantic_edge_count as number | undefined,
    },
    events,
    edges,
    execution: { timeline: executionTimeline, dag: mapExecutionDag(raw, traceId) },
    causal: {
      enabled: Boolean(raw.causal?.roots?.length || edges.length),
      roots: raw.causal?.roots ?? [],
      chains: mapChains(raw),
      stream: buildCausalStream(events, edges),
    },
    state: {
      version: "tier-a",
      patches: stateTimeline,
      timeline: stateTimeline,
    },
    control: { decisions: mapControl(raw) },
    explanation: {
      narrative:
        raw.explanation?.v2_summary ??
        raw.explanation?.narrative ??
        raw.fusion_v2?.explanation?.summary ??
        "",
      root_causes: rootCauses,
      causal_story: raw.explanation?.causal_story ?? raw.fusion_v2?.explanation?.causal_story,
      state_story: raw.explanation?.state_story ?? raw.fusion_v2?.explanation?.state_story,
      control_story: raw.explanation?.control_story ?? raw.fusion_v2?.explanation?.control_story,
      execution_narrative: raw.explanation?.execution_narrative,
      execution_path_labels: raw.explanation?.execution_path_labels,
      v3_summary: raw.explanation?.v3_summary,
      explain_v3: raw.explanation?.explain_v3 as SpineFrontContractV1["explanation"]["explain_v3"],
      execution_v2: raw.explanation?.execution_v2 as SpineFrontContractV1["explanation"]["execution_v2"],
    },
    stream: {
      explain_ws: true,
      live: opts?.streamStatus === "LIVE",
    },
    meta: {
      source:
        raw.schema_version === "spine-query-3"
          ? "spine-query-v3"
          : raw.schema_version === "spine-query-2"
            ? "spine-query-v2"
            : "spine-query-v1",
      latency_ms: opts?.latencyMs,
      partial: events.length === 0,
      schema_version: raw.schema_version,
      drift_summary: raw.meta?.drift_summary as SpineFrontContractV1["meta"]["drift_summary"],
      explain_engine: raw.meta?.explain_engine as string | undefined,
      identity: raw.meta?.identity as SpineFrontContractV1["meta"]["identity"],
      identity_engine: raw.meta?.identity_engine as string | undefined,
    },
    _raw: raw as unknown as Record<string, unknown>,
  };
  partial.identity = buildIdentityBundle(partial);
  return partial;
}
