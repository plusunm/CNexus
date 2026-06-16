"use client";

import clsx from "clsx";
import { ChevronDown, ChevronRight } from "lucide-react";
import { useState } from "react";
import { filterSpineEvents, uniqueSpineValues } from "@/lib/spineMapper";
import type { SpineEvent } from "@/lib/spineTypes";
import { useSpineStore } from "@/lib/spineStore";
import { useMindTheme } from "../MindUiProvider";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  const t = useMindTheme();
  const [open, setOpen] = useState(true);
  return (
    <div className="border-b pb-3" style={{ borderColor: t.border }}>
      <button
        type="button"
        className="w-full flex items-center gap-1 text-left text-[11px] font-medium mb-2 uppercase tracking-wide"
        style={{ color: t.textMuted }}
        onClick={() => setOpen((v) => !v)}
      >
        {open ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
        {title}
      </button>
      {open && children}
    </div>
  );
}

function CheckRow({
  label,
  checked,
  onChange,
  color,
}: {
  label: string;
  checked: boolean;
  onChange: () => void;
  color?: string;
}) {
  const t = useMindTheme();
  return (
    <label className="flex items-center gap-2 py-1 cursor-pointer text-[11px]" style={{ color: t.textMuted }}>
      <input type="checkbox" checked={checked} onChange={onChange} className="accent-cyan-400" />
      {color && <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: color }} />}
      <span style={{ color: checked ? t.text : t.textMuted }}>{label}</span>
    </label>
  );
}

const TYPE_COLORS: Record<string, string> = {
  dispatch: "#3B82F6",
  recall: "#6b8cae",
  write_intent: "#A78BFA",
  cdg: "#c9a227",
  capture: "#34D399",
  ir: "#F87171",
  chat: "#94A3B8",
  control: "#F87171",
};

const DECISION_COLORS = { ALLOW: "#34D399", WARN: "#FBBF24", REJECT: "#F87171" };

type Props = { events: SpineEvent[] };

export function DebuggerFilterSidebar({ events }: Props) {
  const t = useMindTheme();
  const filters = useSpineStore((s) => s.filters);
  const searchQuery = useSpineStore((s) => s.searchQuery);
  const activeTraceId = useSpineStore((s) => s.activeTraceId);
  const setFilters = useSpineStore((s) => s.setFilters);
  const setSearchQuery = useSpineStore((s) => s.setSearchQuery);
  const setActiveTraceId = useSpineStore((s) => s.setActiveTraceId);
  const resetFilters = useSpineStore((s) => s.resetFilters);

  const unique = uniqueSpineValues(events);
  const visible = filterSpineEvents(events, filters, searchQuery, activeTraceId);

  const toggle = (group: keyof typeof filters, value: string) => {
    const set = new Set(filters[group]);
    if (set.has(value)) set.delete(value);
    else set.add(value);
    setFilters({ ...filters, [group]: [...set] });
  };

  return (
    <aside
      className="w-[220px] shrink-0 border-r overflow-y-auto max-h-[calc(100vh-120px)] p-3 space-y-3"
      style={{ borderColor: t.border, backgroundColor: t.chatBg }}
    >
      <div>
        <p className="text-[10px] uppercase tracking-wider mb-2" style={{ color: t.textLight }}>
          Spine Query
        </p>
        <input
          type="search"
          placeholder="trace / event / kind…"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full px-2.5 py-2 rounded-lg text-[11px] border outline-none"
          style={{ backgroundColor: t.surface, borderColor: t.border, color: t.text }}
        />
      </div>

      <Section title="Trace">
        <select
          value={activeTraceId ?? ""}
          onChange={(e) => setActiveTraceId(e.target.value || null)}
          className="w-full px-2 py-1.5 rounded text-[11px] border outline-none"
          style={{ backgroundColor: t.surface, borderColor: t.border, color: t.text }}
        >
          <option value="">All traces</option>
          {unique.traces.map((tr) => (
            <option key={tr} value={tr}>
              {tr.slice(0, 16)}…
            </option>
          ))}
        </select>
      </Section>

      <Section title="Event Type">
        {unique.eventTypes.map((type) => (
          <CheckRow
            key={type}
            label={type}
            color={TYPE_COLORS[type]}
            checked={filters.eventTypes.length === 0 || filters.eventTypes.includes(type)}
            onChange={() => toggle("eventTypes", type)}
          />
        ))}
      </Section>

      <Section title="Mutability">
        {unique.mutability.map((m) => (
          <CheckRow
            key={m}
            label={m}
            checked={filters.mutability.length === 0 || filters.mutability.includes(m)}
            onChange={() => toggle("mutability", m)}
          />
        ))}
      </Section>

      <Section title="Caller">
        {unique.callers.map((c) => (
          <CheckRow
            key={c}
            label={c}
            checked={filters.callers.length === 0 || filters.callers.includes(c)}
            onChange={() => toggle("callers", c)}
          />
        ))}
      </Section>

      <Section title="Decision">
        {(["ALLOW", "WARN", "REJECT"] as const).map((d) => (
          <CheckRow
            key={d}
            label={d}
            color={DECISION_COLORS[d]}
            checked={filters.decisions.length === 0 || filters.decisions.includes(d)}
            onChange={() => toggle("decisions", d)}
          />
        ))}
      </Section>

      <div className="flex gap-2 pt-1">
        <button
          type="button"
          onClick={resetFilters}
          className="flex-1 py-1.5 rounded text-[10px] border"
          style={{ borderColor: t.border, color: t.textMuted }}
        >
          Reset
        </button>
      </div>

      <p className="text-[10px]" style={{ color: t.textLight }}>
        {visible.length} / {events.length} events
      </p>
    </aside>
  );
}
