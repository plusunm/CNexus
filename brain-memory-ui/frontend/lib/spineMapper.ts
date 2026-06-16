import type { GtbsRawEvent, RuntimeLogEntry } from "./api";
import type { SpineAction, SpineDecision, SpineEvent, SpineEventType } from "./spineTypes";

function parseTs(raw: GtbsRawEvent): number {
  const s = raw.ts ?? raw.timestamp;
  if (!s) return Date.now();
  const t = Date.parse(s);
  return Number.isNaN(t) ? Date.now() : t;
}

function kindToEventType(kind: string): SpineEventType {
  if (kind.includes("recall")) return "recall";
  if (kind.includes("cdg")) return "cdg";
  if (kind.includes("capture")) return "capture";
  if (kind.includes("ir")) return "ir";
  if (kind.includes("chat")) return "chat";
  if (kind.includes("working_self")) return "write_intent";
  return "write_intent";
}

function phaseToAction(phase: string, mutability?: string): SpineAction {
  if (phase === "commit") return "commit";
  if (phase === "rejection") return "reject";
  if (phase === "approval") return "propose";
  if (mutability === "advisory") return "read";
  return "propose";
}

function summaryFor(kind: string, phase: string, mutability?: string): string {
  const k = kind.replace(/_/g, " ");
  if (phase === "rejection") return `${k} · rejected`;
  if (phase === "commit") return `${k} · committed`;
  if (mutability === "implicit") return `${k} · implicit side-effect`;
  if (mutability === "advisory") return `${k} · advisory only`;
  return `${k} · ${phase}`;
}

function mapGtbsRow(raw: GtbsRawEvent, index: number): SpineEvent | null {
  const payload = (raw.payload ?? {}) as Record<string, unknown>;
  const prov = (payload.provenance ?? {}) as Record<string, unknown>;
  const kind = String(payload.write_intent_kind ?? payload.source ?? "write_intent");
  const mutability = String(payload.mutability ?? "explicit");
  const phase = raw.event_type ?? "proposal";
  const traceId = String(prov.trace_id ?? `trace-${raw.transaction_id.slice(0, 8)}`);
  const caller = String(prov.caller ?? prov.channel ?? "http");
  const entry = String(prov.entry_registry ?? "unknown");

  if (phase !== "proposal" && phase !== "commit" && phase !== "rejection" && phase !== "approval") {
    return null;
  }

  const eventId = `${raw.transaction_id}:${phase}:${index}`;
  const shadow = Boolean(payload.shadow);
  const gtbsMode = String(payload.gtbs_mode ?? "");

  let decision: SpineEvent["decision"];
  if (phase === "rejection") {
    decision = {
      decision: "REJECT",
      entry,
      caller,
      hard_gate: true,
      reason: String(payload.reason ?? "rejected"),
    };
  } else if (gtbsMode.includes("SHADOW") || shadow) {
    decision = { decision: "WARN", entry, caller, hard_gate: false, reason: "shadow emit" };
  } else {
    decision = { decision: "ALLOW", entry, caller, hard_gate: false };
  }

  const targetStores = Array.isArray(payload.target_stores)
    ? (payload.target_stores as string[])
    : [];

  return {
    event_id: eventId,
    trace_id: traceId,
    timestamp: parseTs(raw),
    event_type: kindToEventType(kind),
    subsystem: "gtbs",
    action: phaseToAction(phase, mutability),
    summary: summaryFor(kind, phase, mutability),
    write_intent: {
      intent_id: raw.transaction_id,
      kind,
      mutability,
      shadow,
      phase,
    },
    decision,
    provenance: {
      caller,
      channel: String(prov.channel ?? caller),
      entry_registry: entry,
      dispatch_kind: prov.dispatch_kind ? String(prov.dispatch_kind) : undefined,
      runtime_token: prov.runtime_token ? String(prov.runtime_token) : undefined,
    },
    state_delta:
      targetStores.length > 0
        ? { memory: targetStores.map((s) => `${s} touched`) }
        : phase === "commit"
          ? undefined
          : undefined,
    raw,
  };
}

/** GTBS rows → unified Spine projection (with synthetic parent links per trace) */
export function buildSpineFromGtbs(rows: GtbsRawEvent[]): SpineEvent[] {
  const mapped = rows
    .map((r, i) => mapGtbsRow(r, i))
    .filter((e): e is SpineEvent => e !== null)
    .sort((a, b) => a.timestamp - b.timestamp);

  const byTrace = new Map<string, SpineEvent[]>();
  for (const e of mapped) {
    const list = byTrace.get(e.trace_id) ?? [];
    list.push(e);
    byTrace.set(e.trace_id, list);
  }

  for (const list of byTrace.values()) {
    for (let i = 1; i < list.length; i += 1) {
      list[i].parent_event_id = list[i - 1].event_id;
      list[i].causal_links = [list[i - 1].event_id];
    }
  }

  return mapped;
}

/** Fallback projection when GTBS jsonl is empty but Runtime logs exist. */
export function buildSpineFromRuntimeLogs(logs: RuntimeLogEntry[]): SpineEvent[] {
  return logs.map((log, index) => {
    const ts = Date.parse(log.timestamp);
    const traceId = String(log.meta?.trace_id ?? `trace-log-${index}`);
    const subsystem: SpineEvent["subsystem"] =
      log.category === "gtbs" || log.category === "cdg" || log.category === "control_plane"
        ? log.category
        : "runtime";
    return {
      event_id: log.id || `runtime-log-${index}`,
      trace_id: traceId,
      timestamp: Number.isNaN(ts) ? Date.now() - index * 1000 : ts,
      event_type: log.category.includes("chat")
        ? "chat"
        : log.category.includes("ollama")
          ? "dispatch"
          : "write_intent",
      subsystem,
      action: log.level === "error" ? "reject" : "read",
      summary: log.message,
      provenance: {
        caller: "runtime",
        channel: log.category || "log",
        entry_registry: log.category || "runtime_log",
      },
      decision:
        log.level === "error"
          ? { decision: "REJECT", entry: log.category, caller: "runtime", hard_gate: false, reason: log.message }
          : { decision: "ALLOW", entry: log.category, caller: "runtime", hard_gate: false },
    };
  });
}

export function filterSpineEvents(
  events: SpineEvent[],
  filters: { eventTypes: string[]; mutability: string[]; callers: string[]; decisions: string[] },
  search: string,
  traceId: string | null,
): SpineEvent[] {
  let out = events;
  if (traceId) out = out.filter((e) => e.trace_id === traceId);
  if (filters.eventTypes.length)
    out = out.filter((e) => filters.eventTypes.includes(e.event_type));
  if (filters.mutability.length)
    out = out.filter((e) => e.write_intent && filters.mutability.includes(e.write_intent.mutability));
  if (filters.callers.length)
    out = out.filter((e) => e.provenance && filters.callers.includes(e.provenance.caller));
  if (filters.decisions.length)
    out = out.filter((e) => e.decision && filters.decisions.includes(e.decision.decision));
  const q = search.trim().toLowerCase();
  if (q) {
    out = out.filter(
      (e) =>
        e.summary.toLowerCase().includes(q) ||
        e.trace_id.toLowerCase().includes(q) ||
        e.event_type.includes(q) ||
        e.write_intent?.kind.toLowerCase().includes(q),
    );
  }
  return out;
}

export function uniqueSpineValues(events: SpineEvent[]) {
  const eventTypes = new Set<string>();
  const mutability = new Set<string>();
  const callers = new Set<string>();
  const traces = new Set<string>();
  for (const e of events) {
    eventTypes.add(e.event_type);
    if (e.write_intent?.mutability) mutability.add(e.write_intent.mutability);
    if (e.provenance?.caller) callers.add(e.provenance.caller);
    traces.add(e.trace_id);
  }
  return {
    eventTypes: [...eventTypes],
    mutability: [...mutability],
    callers: [...callers],
    traces: [...traces],
  };
}

export function decisionColor(decision?: SpineDecision): "green" | "yellow" | "red" | "blue" {
  if (!decision) return "blue";
  if (decision === "ALLOW") return "green";
  if (decision === "WARN") return "yellow";
  return "red";
}

export function eventTypeLabel(t: SpineEventType): string {
  const map: Record<SpineEventType, string> = {
    dispatch: "DISPATCH",
    recall: "RECALL",
    write_intent: "WRITE",
    cdg: "CDG",
    capture: "CAPTURE",
    ir: "IR",
    chat: "CHAT",
    control: "CONTROL",
  };
  return map[t] ?? t.toUpperCase();
}
