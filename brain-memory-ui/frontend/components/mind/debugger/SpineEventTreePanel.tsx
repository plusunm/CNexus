"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import clsx from "clsx";
import { ChevronDown, ChevronRight, FileJson, FolderTree, Layers } from "lucide-react";
import { eventTypeLabel } from "@/lib/spineMapper";
import type { SpineEvent } from "@/lib/spineTypes";
import {
  buildEventForest,
  buildInspectorSections,
  estimateEventDurationMs,
  formatSpanDuration,
  traceWindow,
  type EventTreeNode,
  type InspectorTreeField,
} from "@/lib/spineInspectorTree";
import { useSpineStore } from "@/lib/spineStore";
import { bi, debuggerL } from "@/lib/spine/labels";
import { useMindTheme } from "../MindUiProvider";

const INDENT = 18;
/** Grafana-style column plan: labels | timeline bars | duration (fixed, inset from edge) */
const TREE_GRID_COLUMNS = "minmax(0, 1fr) 168px 64px";
const TREE_PANEL_MAX_WIDTH = "56rem";
const TREE_PANEL_INSET = "1.25rem";

function toneColor(tone: InspectorTreeField["tone"], t: ReturnType<typeof useMindTheme>): string {
  if (tone === "green") return t.green;
  if (tone === "blue") return t.blue;
  if (tone === "purple") return t.purple;
  if (tone === "orange") return t.orange;
  if (tone === "red") return t.red;
  return t.textMuted;
}

function DecisionDot({ decision }: { decision?: SpineEvent["decision"] }) {
  const t = useMindTheme();
  if (!decision) return <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: t.textLight }} />;
  const color = decision.decision === "ALLOW" ? t.green : decision.decision === "WARN" ? t.orange : t.red;
  return <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: color }} />;
}

type TreeRowProps = {
  depth: number;
  expanded: boolean;
  hasChildren: boolean;
  active?: boolean;
  onToggle?: () => void;
  onSelect?: () => void;
  label: React.ReactNode;
  meta?: React.ReactNode;
  bar?: { leftPct: number; widthPct: number; color: string };
  durationLabel?: string;
};

function TreeRow({
  depth,
  expanded,
  hasChildren,
  active,
  onToggle,
  onSelect,
  label,
  meta,
  bar,
  durationLabel,
}: TreeRowProps) {
  const t = useMindTheme();

  return (
    <div
      className={clsx(
        "group grid items-center gap-x-3 min-h-[30px] border-b cursor-pointer transition-colors",
        active && "ring-1 ring-inset",
      )}
      style={{
        gridTemplateColumns: TREE_GRID_COLUMNS,
        paddingLeft: `calc(${TREE_PANEL_INSET} + ${depth * INDENT}px)`,
        paddingRight: TREE_PANEL_INSET,
        borderColor: t.border,
        backgroundColor: active ? t.sidebarActive : "transparent",
        boxShadow: active ? `inset 0 0 0 1px ${t.blue}55` : undefined,
      }}
      onClick={onSelect}
    >
      <div className="flex items-center gap-1.5 min-w-0 py-1 pr-1">
        <button
          type="button"
          className="shrink-0 p-0.5 rounded hover:bg-white/5"
          style={{ color: t.textMuted, visibility: hasChildren ? "visible" : "hidden" }}
          onClick={(e) => {
            e.stopPropagation();
            onToggle?.();
          }}
          aria-label={expanded ? "Collapse" : "Expand"}
        >
          {expanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
        </button>
        <div className="min-w-0 flex-1">{label}</div>
        {meta}
      </div>
      <div className="relative h-5 flex items-center">
        {bar && (
          <div
            className="absolute left-0 top-1/2 -translate-y-1/2 h-2 rounded-sm opacity-80"
            style={{
              marginLeft: `${bar.leftPct}%`,
              width: `${Math.max(bar.widthPct, 2)}%`,
              maxWidth: "100%",
              backgroundColor: bar.color,
            }}
          />
        )}
      </div>
      <div className="flex items-center justify-end py-1">
        {durationLabel && (
          <span className="text-[10px] font-mono tabular-nums whitespace-nowrap" style={{ color: t.textMuted }}>
            {durationLabel}
          </span>
        )}
      </div>
    </div>
  );
}

function InspectorSectionRows({
  event,
  depth,
  expandedSections,
  toggleSection,
}: {
  event: SpineEvent;
  depth: number;
  expandedSections: Set<string>;
  toggleSection: (id: string) => void;
}) {
  const t = useMindTheme();
  const sections = buildInspectorSections(event);

  return (
    <>
      {sections.map((section) => {
        const open = expandedSections.has(section.id);
        return (
          <div key={section.id}>
            <TreeRow
              depth={depth}
              expanded={open}
              hasChildren={section.fields.length > 0}
              onToggle={() => toggleSection(section.id)}
              onSelect={() => toggleSection(section.id)}
              label={
                <span className="flex items-center gap-1.5 min-w-0">
                  <Layers className="w-3 h-3 shrink-0" style={{ color: t.purple }} />
                  <span className="text-[11px] font-medium truncate" style={{ color: t.text }}>
                    {section.label}
                  </span>
                  <span className="text-[9px] shrink-0" style={{ color: t.textLight }}>
                    Inspector
                  </span>
                </span>
              }
            />
            {open &&
              section.fields.map((field, idx) => (
                <TreeRow
                  key={`${section.id}:${field.key}:${idx}`}
                  depth={depth + 1}
                  expanded={false}
                  hasChildren={false}
                  label={
                    <span className="text-[10px] font-mono truncate" style={{ color: toneColor(field.tone, t) }}>
                      <span style={{ color: t.textMuted }}>{field.key}</span>
                      <span className="mx-1 opacity-40">:</span>
                      <span className="break-all">{field.value}</span>
                    </span>
                  }
                />
              ))}
          </div>
        );
      })}
    </>
  );
}

function EventNodeRows({
  node,
  traceEvents,
  traceStart,
  traceSpanMs,
  depth,
  expandedEvents,
  expandedSections,
  toggleEvent,
  toggleSection,
  selectedEventId,
  selectEvent,
}: {
  node: EventTreeNode;
  traceEvents: SpineEvent[];
  traceStart: number;
  traceSpanMs: number;
  depth: number;
  expandedEvents: Set<string>;
  expandedSections: Set<string>;
  toggleEvent: (id: string) => void;
  toggleSection: (id: string) => void;
  selectedEventId: string | null;
  selectEvent: (id: string) => void;
}) {
  const t = useMindTheme();
  const { event, children } = node;
  const eventOpen = expandedEvents.has(event.event_id);
  const active = selectedEventId === event.event_id;
  const durationMs = estimateEventDurationMs(event, traceEvents);
  const leftPct = ((event.timestamp - traceStart) / traceSpanMs) * 100;
  const widthPct = (durationMs / traceSpanMs) * 100;
  const barColor =
    event.decision?.decision === "REJECT" ? t.red : event.decision?.decision === "WARN" ? t.orange : t.blue;
  const time = new Date(event.timestamp).toLocaleTimeString("zh-CN", { hour12: false });

  return (
    <>
      <TreeRow
        depth={depth}
        expanded={eventOpen}
        hasChildren
        active={active}
        onToggle={() => toggleEvent(event.event_id)}
        onSelect={() => {
          selectEvent(event.event_id);
          if (!eventOpen) toggleEvent(event.event_id);
        }}
        label={
          <span className="flex items-center gap-1.5 min-w-0">
            <DecisionDot decision={event.decision} />
            <span className="text-[10px] font-semibold shrink-0" style={{ color: t.purple }}>
              {event.subsystem}
            </span>
            <span className="text-[10px] shrink-0 px-1 rounded" style={{ backgroundColor: t.blueSoft, color: t.blue }}>
              {eventTypeLabel(event.event_type)}
            </span>
            <span className="text-[11px] truncate" style={{ color: t.text }}>
              {event.summary}
            </span>
          </span>
        }
        meta={
          <span className="text-[9px] font-mono shrink-0 hidden sm:inline" style={{ color: t.textLight }}>
            {time}
          </span>
        }
        bar={{ leftPct, widthPct, color: barColor }}
        durationLabel={formatSpanDuration(durationMs)}
      />

      {eventOpen && (
        <>
          {children.map((child) => (
            <EventNodeRows
              key={child.event.event_id}
              node={child}
              traceEvents={traceEvents}
              traceStart={traceStart}
              traceSpanMs={traceSpanMs}
              depth={depth + 1}
              expandedEvents={expandedEvents}
              expandedSections={expandedSections}
              toggleEvent={toggleEvent}
              toggleSection={toggleSection}
              selectedEventId={selectedEventId}
              selectEvent={selectEvent}
            />
          ))}
          <InspectorSectionRows
            event={event}
            depth={depth + 1}
            expandedSections={expandedSections}
            toggleSection={toggleSection}
          />
        </>
      )}
    </>
  );
}

type Props = {
  events: SpineEvent[];
  emptyReason?: import("@/hooks/useSpineStream").SpineEmptyReason;
  isLive?: boolean;
};

/** Grafana 式 Event Spine + Inspector 统一树状视图 */
export function SpineEventTreePanel({ events, emptyReason = null, isLive = false }: Props) {
  const t = useMindTheme();
  const replayIndex = useSpineStore((s) => s.replayIndex);
  const streamMode = useSpineStore((s) => s.streamMode);
  const selectedEventId = useSpineStore((s) => s.selectedEventId);
  const selectEvent = useSpineStore((s) => s.selectEvent);

  const slice = streamMode === "replay" ? events.slice(0, Math.max(1, replayIndex + 1)) : events;

  const byTrace = useMemo(() => {
    const map = new Map<string, SpineEvent[]>();
    for (const e of slice) {
      const list = map.get(e.trace_id) ?? [];
      list.push(e);
      map.set(e.trace_id, list);
    }
    return map;
  }, [slice]);

  const [expandedTraces, setExpandedTraces] = useState<Set<string>>(() => new Set());
  const [expandedEvents, setExpandedEvents] = useState<Set<string>>(() => new Set());
  const [expandedSections, setExpandedSections] = useState<Set<string>>(() => new Set());

  useEffect(() => {
    if (byTrace.size === 1) {
      const only = [...byTrace.keys()][0];
      setExpandedTraces(new Set([only]));
    }
  }, [byTrace]);

  useEffect(() => {
    if (!selectedEventId) return;
    const event = slice.find((e) => e.event_id === selectedEventId);
    if (!event) return;
    setExpandedTraces((prev) => new Set(prev).add(event.trace_id));
    setExpandedEvents((prev) => new Set(prev).add(event.event_id));
    const sections = buildInspectorSections(event);
    if (sections.length) {
      setExpandedSections((prev) => {
        const next = new Set(prev);
        next.add(sections[0].id);
        return next;
      });
    }
  }, [selectedEventId, slice]);

  const toggleTrace = useCallback((traceId: string) => {
    setExpandedTraces((prev) => {
      const next = new Set(prev);
      if (next.has(traceId)) next.delete(traceId);
      else next.add(traceId);
      return next;
    });
  }, []);

  const toggleEvent = useCallback((eventId: string) => {
    setExpandedEvents((prev) => {
      const next = new Set(prev);
      if (next.has(eventId)) next.delete(eventId);
      else next.add(eventId);
      return next;
    });
  }, []);

  const toggleSection = useCallback((sectionId: string) => {
    setExpandedSections((prev) => {
      const next = new Set(prev);
      if (next.has(sectionId)) next.delete(sectionId);
      else next.add(sectionId);
      return next;
    });
  }, []);

  if (events.length === 0) {
    const hint =
      emptyReason === "no_events" && isLive
        ? bi(debuggerL.noSpineEventsLive)
        : emptyReason === "offline"
          ? bi(debuggerL.spineOffline)
          : bi(debuggerL.noSpineEvents);
    return (
      <div className="flex-1 flex items-center justify-center p-8">
        <p className="text-sm text-center max-w-md" style={{ color: t.textMuted }}>
          {hint}
        </p>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
      <div className="mr-auto w-full flex flex-col min-h-0" style={{ maxWidth: TREE_PANEL_MAX_WIDTH }}>
        <div
          className="shrink-0 py-2 border-b flex items-center justify-between gap-3"
          style={{
            borderColor: t.border,
            backgroundColor: t.surface,
            paddingLeft: TREE_PANEL_INSET,
            paddingRight: TREE_PANEL_INSET,
          }}
        >
          <div className="flex items-center gap-2 min-w-0">
            <FolderTree className="w-4 h-4 shrink-0" style={{ color: "#5eead4" }} />
            <p className="text-xs font-medium truncate" style={{ color: t.text }}>
              Event Spine / Inspector
            </p>
          </div>
          <p className="text-[10px] font-mono shrink-0" style={{ color: t.textMuted }}>
            {slice.length} events · {byTrace.size} traces
          </p>
        </div>

        <div
          className="shrink-0 grid items-center gap-x-3 py-1.5 border-b text-[9px] uppercase tracking-wider font-medium"
          style={{
            gridTemplateColumns: TREE_GRID_COLUMNS,
            paddingLeft: TREE_PANEL_INSET,
            paddingRight: TREE_PANEL_INSET,
            borderColor: t.border,
            color: t.textLight,
            backgroundColor: t.chatBg,
          }}
        >
          <span className="pl-6">Service &amp; Operation</span>
          <span>Timeline</span>
          <span className="text-right">Duration</span>
        </div>

        <div className="flex-1 overflow-y-auto overflow-x-hidden min-h-0">
          {[...byTrace.entries()].map(([traceId, traceEvents]) => {
            const traceOpen = expandedTraces.has(traceId);
            const forest = buildEventForest(traceEvents);
            const { start, spanMs } = traceWindow(traceEvents);
            const traceDuration = formatSpanDuration(spanMs);

            return (
              <div key={traceId}>
                <TreeRow
                  depth={0}
                  expanded={traceOpen}
                  hasChildren
                  onToggle={() => toggleTrace(traceId)}
                  onSelect={() => toggleTrace(traceId)}
                  label={
                    <span className="flex items-center gap-2 min-w-0">
                      <FileJson className="w-3.5 h-3.5 shrink-0" style={{ color: t.blue }} />
                      <span className="text-[11px] font-mono font-semibold truncate" style={{ color: t.blue }}>
                        TRACE {traceId}
                      </span>
                      <span className="text-[9px] shrink-0" style={{ color: t.textMuted }}>
                        {traceEvents.length} spans
                      </span>
                    </span>
                  }
                  bar={{ leftPct: 0, widthPct: 100, color: `${t.blue}55` }}
                  durationLabel={traceDuration}
                />

                {traceOpen &&
                  forest.map((node) => (
                    <EventNodeRows
                      key={node.event.event_id}
                      node={node}
                      traceEvents={traceEvents}
                      traceStart={start}
                      traceSpanMs={spanMs}
                      depth={1}
                      expandedEvents={expandedEvents}
                      expandedSections={expandedSections}
                      toggleEvent={toggleEvent}
                      toggleSection={toggleSection}
                      selectedEventId={selectedEventId}
                      selectEvent={selectEvent}
                    />
                  ))}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
