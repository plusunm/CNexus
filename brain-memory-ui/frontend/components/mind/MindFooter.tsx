"use client";

import { CheckCircle2 } from "lucide-react";
import { useMindOverview } from "@/cnexus-kernel";
import { bi, biSection, footerL } from "@/lib/spine/labels";
import { useMindTheme } from "./MindUiProvider";
import type { MindTheme } from "./themes/types";

const PRINCIPLES = [
  "Memory First — 记忆优先",
  "Chat as Explorer — 对话即探索",
  "Goal Driven — 目标驱动",
  "Observability — 可观测",
  "Governance Before Mutation — 变更前先治理",
];

function FooterBlock({
  title,
  accent,
  t,
  children,
}: {
  title: string;
  accent: string;
  t: MindTheme;
  children: React.ReactNode;
}) {
  return (
    <div
      className="rounded-lg border p-3"
      style={{ backgroundColor: t.bg, borderColor: t.border, borderTopWidth: 3, borderTopColor: accent }}
    >
      <p className="text-xs font-semibold mb-2" style={{ color: t.text }}>
        {title}
      </p>
      {children}
    </div>
  );
}

export function MindFooter() {
  const t = useMindTheme();
  const { overview, runtimeState } = useMindOverview();
  const synthGen = (overview.goal_layer as { synthesis_generation?: number } | undefined)
    ?.synthesis_generation;
  const wm = runtimeState?.working_memory_count ?? 0;
  const metrics = runtimeState?.metrics?.counters ?? {};

  return (
    <footer className="mt-4 grid grid-cols-1 lg:grid-cols-3 gap-3">
      <FooterBlock title={biSection(footerL.dataFlowGuide)} accent={t.purple} t={t}>
        <ul className="text-[11px] space-y-1" style={{ color: t.textMuted }}>
          <li>
            <span style={{ color: t.purple }}>●</span> {bi(footerL.chatFlow)}
          </li>
          <li>
            <span style={{ color: t.blue }}>●</span> {bi(footerL.browseFlow)}
          </li>
          <li>
            <span style={{ color: t.green }}>●</span> {bi(footerL.importFlow)}
          </li>
          {synthGen != null && (
            <li className="pt-1" style={{ color: t.textLight }}>
              Synthesis gen #{synthGen} · WM {wm}
            </li>
          )}
        </ul>
      </FooterBlock>

      <FooterBlock title={biSection(footerL.corePrinciples)} accent={t.blue} t={t}>
        <ul className="space-y-1">
          {PRINCIPLES.map((p) => (
            <li key={p} className="flex items-start gap-1.5 text-[11px]" style={{ color: t.textMuted }}>
              <CheckCircle2 className="w-3.5 h-3.5 shrink-0 mt-0.5" style={{ color: t.green }} />
              {p}
            </li>
          ))}
        </ul>
      </FooterBlock>

      <FooterBlock title={biSection(footerL.p4Loop)} accent={t.green} t={t}>
        <div
          className="flex items-center justify-center gap-2 py-3 text-[10px] flex-wrap"
          style={{ color: t.textMuted }}
        >
          <span
            className="px-3 py-1.5 rounded-full border font-medium"
            style={{ borderColor: t.purple, color: t.purple, backgroundColor: t.purpleSoft }}
          >
            Goal Layer
          </span>
          <span style={{ color: t.textLight }}>→</span>
          <span
            className="px-3 py-1.5 rounded-full border font-medium"
            style={{ borderColor: t.blue, color: t.blue, backgroundColor: t.blueSoft }}
          >
            Future Actions
          </span>
          <span style={{ color: t.textLight }}>→</span>
          <span
            className="px-3 py-1.5 rounded-full border font-medium"
            style={{ borderColor: t.green, color: t.green, backgroundColor: t.greenSoft }}
          >
            Governance
          </span>
          <span className="w-full text-center mt-1" style={{ color: t.textLight }}>
            {overview.system.governance_label} · {bi(footerL.health)} {overview.system.health_label}
            {Object.keys(metrics).length > 0
              ? ` · ${Object.keys(metrics).length} metrics`
              : ""}
          </span>
        </div>
      </FooterBlock>
    </footer>
  );
}
