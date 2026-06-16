"use client";

import { useMindOverview } from "@/cnexus-kernel";
import { useMindTheme } from "./MindUiProvider";
import type { MindTheme } from "./themes/types";

function CardShell({
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
      className="rounded-xl border p-4 flex flex-col min-h-[140px] shadow-sm"
      style={{ backgroundColor: t.surface, borderColor: t.border }}
    >
      <div className="flex items-center gap-2 mb-3">
        <span className="w-2 h-2 rounded-full" style={{ backgroundColor: accent }} />
        <span className="text-sm font-semibold" style={{ color: accent }}>
          {title}
        </span>
      </div>
      {children}
    </div>
  );
}

export function StatusCardsRow() {
  const t = useMindTheme();
  const { overview } = useMindOverview();
  const { goal, identity, belief, focus } = overview.cards;
  const trackBg = t.border;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3 mb-3">
      <div id="goals">
        <CardShell title="当前长期目标" accent={t.blue} t={t}>
          <p className="text-sm font-medium mb-2 line-clamp-2" style={{ color: t.text }}>
            {goal.title}
          </p>
          <div className="h-2 rounded-full mb-3 overflow-hidden" style={{ backgroundColor: trackBg }}>
            <div
              className="h-full rounded-full transition-all duration-500"
              style={{
                width: `${Math.round((goal.progress ?? 0) * 100)}%`,
                backgroundColor: t.blue,
              }}
            />
          </div>
          <div className="grid grid-cols-3 gap-1 text-[11px]" style={{ color: t.textMuted }}>
            <span>Progress: {goal.progress_label}</span>
            <span>Alignment: {goal.alignment_label}</span>
            <span>
              Priority:{" "}
              <b style={{ color: goal.priority_label === "高" ? t.red : t.text }}>
                {goal.priority_label}
              </b>
            </span>
          </div>
        </CardShell>
      </div>

      <CardShell title="我的身份" accent={t.blue} t={t}>
        <p className="text-sm font-medium mb-3 leading-snug line-clamp-3" style={{ color: t.text }}>
          {identity.summary}
        </p>
        <div className="grid grid-cols-3 gap-1 text-[11px] mt-auto" style={{ color: t.textMuted }}>
          <span>稳定性: {identity.stability_label}</span>
          <span>一致性: {identity.consistency_label}</span>
          <span>更新: {identity.updated_ago}</span>
        </div>
      </CardShell>

      <div id="beliefs">
        <CardShell title="我的信念" accent={t.green} t={t}>
          <p className="text-sm font-medium mb-3 leading-snug line-clamp-3" style={{ color: t.text }}>
            {belief.content}
          </p>
          <div className="grid grid-cols-3 gap-1 text-[11px] mt-auto" style={{ color: t.textMuted }}>
            <span>置信度: {belief.confidence_label}</span>
            <span>证据数: {belief.evidence_count ?? 0}</span>
            <span>冲突数: {belief.conflict_count ?? 0}</span>
          </div>
        </CardShell>
      </div>

      <div id="focus">
        <CardShell title="工作焦点" accent={t.purple} t={t}>
          <p className="text-sm font-medium mb-3 leading-snug line-clamp-3" style={{ color: t.text }}>
            {focus.title}
          </p>
          <div className="grid grid-cols-3 gap-1 text-[11px] mt-auto" style={{ color: t.textMuted }}>
            <span>注意力: {focus.attention_label}</span>
            <span>持续: {focus.duration_label}</span>
            <span>相关目标: {focus.related_goals ?? 0}个</span>
          </div>
        </CardShell>
      </div>
    </div>
  );
}
