"use client";

import type { SpineEvent } from "@/lib/spineTypes";
import { useSpineStore } from "@/lib/spineStore";
import { bi, debuggerL } from "@/lib/spine/labels";
import { useMindTheme } from "../MindUiProvider";

function Block({ title, children }: { title: string; children: React.ReactNode }) {
  const t = useMindTheme();
  return (
    <div className="rounded-lg border p-3 mb-3" style={{ borderColor: t.border, backgroundColor: t.chatBg }}>
      <p className="text-[10px] uppercase tracking-wider mb-2 font-medium" style={{ color: t.textLight }}>
        {title}
      </p>
      {children}
    </div>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  const t = useMindTheme();
  return (
    <div className="flex justify-between gap-2 text-[11px] py-0.5">
      <span style={{ color: t.textMuted }}>{k}</span>
      <span className="font-mono text-right break-all" style={{ color: t.text }}>
        {v}
      </span>
    </div>
  );
}

type Props = { events: SpineEvent[] };

/** Control + State 投影 — 点击 event 后展示 */
export function SpineInspectorPanel({ events }: Props) {
  const t = useMindTheme();
  const selectedEventId = useSpineStore((s) => s.selectedEventId);
  const showRaw = useSpineStore((s) => s.showRaw);
  const setShowRaw = useSpineStore((s) => s.setShowRaw);

  const event = events.find((e) => e.event_id === selectedEventId) ?? events[events.length - 1];

  if (!event) {
    return (
      <aside
        className="w-[300px] shrink-0 border-l p-4 flex items-center justify-center"
        style={{ borderColor: t.border, backgroundColor: t.surface }}
      >
        <p className="text-xs text-center" style={{ color: t.textMuted }}>
          {bi(debuggerL.selectEvent)}
          <br />
          {bi(debuggerL.inspectHint)}
        </p>
      </aside>
    );
  }

  const dec = event.decision;
  const decColor = dec?.decision === "ALLOW" ? t.green : dec?.decision === "WARN" ? t.orange : t.red;
  const hasDelta =
    event.state_delta &&
    (event.state_delta.memory?.length ||
      event.state_delta.working_self?.length ||
      event.state_delta.graph?.length ||
      event.state_delta.vector?.length);

  return (
    <aside
      className="w-[300px] shrink-0 border-l overflow-y-auto max-h-[calc(100vh-120px)] p-4"
      style={{ borderColor: t.border, backgroundColor: t.surface }}
    >
      <p className="text-sm font-semibold mb-1" style={{ color: t.text }}>
        Inspector
      </p>
      <p className="text-[11px] mb-4 leading-relaxed" style={{ color: t.textMuted }}>
        {event.summary}
      </p>

      {dec && (
        <Block title="Control Layer">
          <div className="flex items-center gap-2 mb-2">
            <span
              className="text-xs font-bold px-2 py-0.5 rounded"
              style={{ backgroundColor: `${decColor}22`, color: decColor }}
            >
              {dec.decision}
            </span>
            {dec.hard_gate && (
              <span className="text-[9px] px-1.5 py-0.5 rounded" style={{ backgroundColor: t.red + "22", color: t.red }}>
                HARD GATE
              </span>
            )}
          </div>
          <Row k="entry" v={dec.entry} />
          <Row k="caller" v={dec.caller} />
          {dec.reason && <Row k="reason" v={dec.reason} />}
        </Block>
      )}

      {event.write_intent && (
        <Block title="Write Intent">
          <Row k="kind" v={event.write_intent.kind} />
          <Row k="mutability" v={event.write_intent.mutability} />
          <Row k="phase" v={event.write_intent.phase ?? "—"} />
          <Row k="shadow" v={event.write_intent.shadow ? "yes" : "no"} />
          <Row k="intent_id" v={event.write_intent.intent_id} />
        </Block>
      )}

      {event.provenance && (
        <Block title="Provenance">
          <Row k="trace_id" v={event.trace_id} />
          <Row k="caller" v={event.provenance.caller} />
          <Row k="channel" v={event.provenance.channel} />
          <Row k="entry" v={event.provenance.entry_registry} />
          {event.provenance.dispatch_kind && <Row k="dispatch" v={event.provenance.dispatch_kind} />}
        </Block>
      )}

      <Block title="State Diff">
        {!hasDelta ? (
          <p className="text-[11px]" style={{ color: t.textMuted }}>
            NO STATE MUTATION
          </p>
        ) : (
          <div className="space-y-2 text-[11px]">
            {event.state_delta?.memory?.map((line) => (
              <p key={line} style={{ color: t.green }}>
                memory · {line}
              </p>
            ))}
            {event.state_delta?.working_self?.map((line) => (
              <p key={line} style={{ color: t.blue }}>
                working_self · {line}
              </p>
            ))}
            {event.state_delta?.graph?.map((line) => (
              <p key={line} style={{ color: t.purple }}>
                graph · {line}
              </p>
            ))}
            {event.state_delta?.vector?.map((line) => (
              <p key={line} style={{ color: t.orange }}>
                vector · {line}
              </p>
            ))}
          </div>
        )}
      </Block>

      {event.parent_event_id && (
        <Block title="Causal">
          <Row k="parent" v={event.parent_event_id} />
          {event.causal_links?.length ? (
            <p className="text-[10px] font-mono mt-1 break-all" style={{ color: t.textMuted }}>
              links: {event.causal_links.join(" → ")}
            </p>
          ) : null}
        </Block>
      )}

      <button
        type="button"
        onClick={() => setShowRaw(!showRaw)}
        className="text-[10px] mb-2 underline"
        style={{ color: t.textLight }}
      >
        {showRaw ? "Hide raw" : "Show raw (P2)"}
      </button>
      {showRaw && event.raw && (
        <pre
          className="text-[9px] p-2 rounded overflow-auto max-h-40 font-mono"
          style={{ backgroundColor: t.chatBg, color: t.textMuted }}
        >
          {JSON.stringify(event.raw, null, 2)}
        </pre>
      )}
    </aside>
  );
}
