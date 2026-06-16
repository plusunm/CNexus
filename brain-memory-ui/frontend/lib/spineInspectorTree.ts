import type { SpineEvent } from "./spineTypes";

export type InspectorTreeField = {
  key: string;
  value: string;
  tone?: "green" | "blue" | "purple" | "orange" | "red" | "muted";
};

export type InspectorTreeSection = {
  id: string;
  label: string;
  fields: InspectorTreeField[];
};

export function buildInspectorSections(event: SpineEvent): InspectorTreeSection[] {
  const sections: InspectorTreeSection[] = [];

  if (event.decision) {
    const dec = event.decision;
    sections.push({
      id: `${event.event_id}:control`,
      label: "Control Layer",
      fields: [
        { key: "decision", value: dec.decision, tone: dec.decision === "ALLOW" ? "green" : dec.decision === "WARN" ? "orange" : "red" },
        { key: "entry", value: dec.entry },
        { key: "caller", value: dec.caller },
        ...(dec.reason ? [{ key: "reason", value: dec.reason }] : []),
        ...(dec.hard_gate ? [{ key: "hard_gate", value: "yes", tone: "red" as const }] : []),
      ],
    });
  }

  if (event.write_intent) {
    const wi = event.write_intent;
    sections.push({
      id: `${event.event_id}:intent`,
      label: "Write Intent",
      fields: [
        { key: "kind", value: wi.kind },
        { key: "mutability", value: wi.mutability },
        { key: "phase", value: wi.phase ?? "—" },
        { key: "shadow", value: wi.shadow ? "yes" : "no", tone: wi.shadow ? "orange" : undefined },
        { key: "intent_id", value: wi.intent_id },
      ],
    });
  }

  if (event.provenance) {
    const p = event.provenance;
    sections.push({
      id: `${event.event_id}:provenance`,
      label: "Provenance",
      fields: [
        { key: "trace_id", value: event.trace_id },
        { key: "caller", value: p.caller },
        { key: "channel", value: p.channel },
        { key: "entry", value: p.entry_registry },
        ...(p.dispatch_kind ? [{ key: "dispatch", value: p.dispatch_kind }] : []),
      ],
    });
  }

  const delta = event.state_delta;
  const deltaFields: InspectorTreeField[] = [];
  delta?.memory?.forEach((line) => deltaFields.push({ key: "memory", value: line, tone: "green" }));
  delta?.working_self?.forEach((line) => deltaFields.push({ key: "working_self", value: line, tone: "blue" }));
  delta?.graph?.forEach((line) => deltaFields.push({ key: "graph", value: line, tone: "purple" }));
  delta?.vector?.forEach((line) => deltaFields.push({ key: "vector", value: line, tone: "orange" }));

  sections.push({
    id: `${event.event_id}:state`,
    label: "State Diff",
    fields: deltaFields.length ? deltaFields : [{ key: "mutation", value: "NO STATE MUTATION", tone: "muted" }],
  });

  if (event.parent_event_id || event.causal_links?.length) {
    sections.push({
      id: `${event.event_id}:causal`,
      label: "Causal",
      fields: [
        ...(event.parent_event_id ? [{ key: "parent", value: event.parent_event_id }] : []),
        ...(event.causal_links?.length
          ? [{ key: "links", value: event.causal_links.join(" → ") }]
          : []),
      ],
    });
  }

  if (event.raw) {
    sections.push({
      id: `${event.event_id}:raw`,
      label: "Raw",
      fields: [{ key: "payload", value: JSON.stringify(event.raw, null, 2), tone: "muted" }],
    });
  }

  return sections;
}

export type EventTreeNode = {
  event: SpineEvent;
  children: EventTreeNode[];
};

export function buildEventForest(events: SpineEvent[]): EventTreeNode[] {
  const byId = new Map(events.map((e) => [e.event_id, e]));
  const childMap = new Map<string, SpineEvent[]>();

  for (const event of events) {
    const parentId = event.parent_event_id;
    if (parentId && byId.has(parentId)) {
      const list = childMap.get(parentId) ?? [];
      list.push(event);
      childMap.set(parentId, list);
    }
  }

  const roots = events.filter((e) => !e.parent_event_id || !byId.has(e.parent_event_id));
  const sortByTime = (a: SpineEvent, b: SpineEvent) => a.timestamp - b.timestamp;

  const toNode = (event: SpineEvent): EventTreeNode => ({
    event,
    children: (childMap.get(event.event_id) ?? []).sort(sortByTime).map(toNode),
  });

  return roots.sort(sortByTime).map(toNode);
}

export function formatSpanDuration(ms: number): string {
  if (ms < 1) return `${Math.round(ms * 1000)}µs`;
  if (ms < 1000) return `${ms.toFixed(2)}ms`;
  return `${(ms / 1000).toFixed(2)}s`;
}

export function estimateEventDurationMs(event: SpineEvent, traceEvents: SpineEvent[]): number {
  const children = traceEvents.filter((e) => e.parent_event_id === event.event_id);
  if (children.length) {
    const childEnd = Math.max(...children.map((c) => c.timestamp));
    return Math.max(0.5, childEnd - event.timestamp);
  }
  const sorted = [...traceEvents].sort((a, b) => a.timestamp - b.timestamp);
  const idx = sorted.findIndex((e) => e.event_id === event.event_id);
  const next = sorted[idx + 1];
  if (next) return Math.max(0.5, next.timestamp - event.timestamp);
  return 5;
}

export function traceWindow(events: SpineEvent[]): { start: number; end: number; spanMs: number } {
  if (!events.length) return { start: 0, end: 0, spanMs: 1 };
  const start = Math.min(...events.map((e) => e.timestamp));
  const end = Math.max(...events.map((e) => e.timestamp));
  return { start, end, spanMs: Math.max(1, end - start) };
}
