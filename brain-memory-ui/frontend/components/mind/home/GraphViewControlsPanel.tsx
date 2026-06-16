"use client";

import { ChevronDown, ChevronRight } from "lucide-react";
import { useState } from "react";
import type { FactorGraph } from "@/lib/factorGraphModel";
import { FACTOR_TAG_LABEL } from "@/lib/factorGraphModel";
import type { GraphViewSettings } from "@/lib/graphViewModel";
import { useMindTheme } from "../MindUiProvider";

type Props = {
  settings: GraphViewSettings;
  onChange: (next: GraphViewSettings) => void;
  graph: FactorGraph;
};

function Section({
  title,
  defaultOpen = true,
  children,
}: {
  title: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
}) {
  const t = useMindTheme();
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div
      className="rounded-lg border p-2 min-h-0 min-w-0 h-full flex flex-col overflow-hidden"
      style={{ borderColor: t.border, backgroundColor: t.chatBg }}
    >
      <button
        type="button"
        className="w-full flex items-center gap-1.5 text-left text-xs font-semibold mb-1 shrink-0"
        style={{ color: t.text }}
        onClick={() => setOpen((v) => !v)}
      >
        {open ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
        {title}
      </button>
      {open && (
        <div className="flex-1 min-h-0 overflow-y-auto flex flex-col justify-center gap-0.5">
          {children}
        </div>
      )}
    </div>
  );
}

function SliderRow({
  label,
  value,
  min,
  max,
  step,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  onChange: (v: number) => void;
}) {
  const t = useMindTheme();
  return (
    <label className="block mb-2 last:mb-0">
      <div className="flex justify-between text-[10px] mb-0.5" style={{ color: t.textMuted }}>
        <span className="truncate pr-1">{label}</span>
        <span className="shrink-0">{value.toFixed(2).replace(/\.00$/, "")}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full accent-cyan-400"
      />
    </label>
  );
}

function ToggleRow({ label, checked, onChange }: { label: string; checked: boolean; onChange: (v: boolean) => void }) {
  const t = useMindTheme();
  return (
    <label className="flex items-center justify-between text-[10px] py-1 cursor-pointer gap-2" style={{ color: t.textMuted }}>
      <span className="truncate">{label}</span>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className="w-8 h-4 rounded-full relative shrink-0"
        style={{ backgroundColor: checked ? t.blue : t.border }}
      >
        <span
          className="absolute top-0.5 w-3 h-3 rounded-full bg-white transition-all"
          style={{ left: checked ? "1rem" : "0.125rem" }}
        />
      </button>
    </label>
  );
}

const GROUP_SWATCH: Record<string, string> = {
  goal: "#34D399",
  belief: "#c9a227",
  episode: "#6b8cae",
  identity: "#F87171",
  insight: "#34D399",
  term: "#64748B",
};

export function GraphViewControlsPanel({ settings, onChange, graph }: Props) {
  const t = useMindTheme();
  const patch = (p: Partial<GraphViewSettings>) => onChange({ ...settings, ...p });

  const groupCounts = graph.nodes.reduce<Record<string, number>>((acc, n) => {
    acc[n.tag] = (acc[n.tag] ?? 0) + 1;
    return acc;
  }, {});

  return (
    <aside
      className="min-w-0 w-full h-full p-2.5 overflow-hidden box-border"
      style={{ backgroundColor: `${t.surface}ee` }}
    >
      <div className="grid grid-cols-2 grid-rows-2 gap-2 min-w-0 w-full h-full">
        <Section title="Filters">
          <input
            type="search"
            placeholder="Search..."
            value={settings.search}
            onChange={(e) => patch({ search: e.target.value })}
            className="w-full px-2 py-1.5 rounded-md text-[10px] border mb-1.5 outline-none"
            style={{ backgroundColor: t.bg, borderColor: t.border, color: t.text }}
          />
          <ToggleRow label="Tags" checked={settings.tagsOnly} onChange={(v) => patch({ tagsOnly: v })} />
          <ToggleRow label="Orphans" checked={settings.orphansOnly} onChange={(v) => patch({ orphansOnly: v })} />
        </Section>

        <Section title="Groups">
          <ul className="space-y-1 mb-1 flex-1 min-h-0 overflow-y-auto">
            {Object.entries(groupCounts).map(([tag, count]) => (
              <li key={tag} className="flex items-center gap-1.5 text-[10px]" style={{ color: t.textMuted }}>
                <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: GROUP_SWATCH[tag] ?? t.textMuted }} />
                <span className="truncate" style={{ color: t.text }}>{FACTOR_TAG_LABEL[tag as keyof typeof FACTOR_TAG_LABEL] ?? tag}</span>
                <span className="ml-auto shrink-0">{count}</span>
              </li>
            ))}
          </ul>
          <button
            type="button"
            className="w-full py-1.5 rounded-md text-[10px] font-medium"
            style={{ backgroundColor: "#5eead4", color: "#0f172a" }}
          >
            New group
          </button>
        </Section>

        <Section title="Display">
          <ToggleRow label="Arrows" checked={settings.showArrows} onChange={(v) => patch({ showArrows: v })} />
          <SliderRow label="Text fade" value={settings.textFade} min={0} max={1} step={0.05} onChange={(v) => patch({ textFade: v })} />
          <SliderRow label="Node size" value={settings.nodeSize} min={0.5} max={2} step={0.1} onChange={(v) => patch({ nodeSize: v })} />
          <SliderRow label="Link width" value={settings.linkThickness} min={0.3} max={3} step={0.1} onChange={(v) => patch({ linkThickness: v })} />
          <button
            type="button"
            onClick={() => patch({ animate: !settings.animate })}
            className="w-full py-1.5 rounded-md text-[10px] font-medium mt-0.5"
            style={{ backgroundColor: settings.animate ? "#5eead4" : t.border, color: settings.animate ? "#0f172a" : t.textMuted }}
          >
            {settings.animate ? "Animate ON" : "Animate"}
          </button>
        </Section>

        <Section title="Forces">
          <SliderRow label="Center" value={settings.centerForce} min={0} max={0.3} step={0.01} onChange={(v) => patch({ centerForce: v })} />
          <SliderRow label="Repel" value={settings.repelForce} min={20} max={300} step={5} onChange={(v) => patch({ repelForce: v })} />
          <SliderRow label="Link" value={settings.linkForce} min={0.01} max={0.15} step={0.005} onChange={(v) => patch({ linkForce: v })} />
          <SliderRow label="Distance" value={settings.linkDistance} min={30} max={160} step={2} onChange={(v) => patch({ linkDistance: v })} />
        </Section>
      </div>
    </aside>
  );
}
