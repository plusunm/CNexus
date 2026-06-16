"use client";

import { Brain, Dna, Heart } from "lucide-react";
import { useMindOverview } from "@/cnexus-kernel";
import { EMPTY_PERSONALITY_OBSERVATION } from "@/lib/runtimeTypes";
import { useMindTheme } from "../MindUiProvider";

function MetricBar({ label, value, valueLabel, accent }: {
  label: string;
  value: number;
  valueLabel: string;
  accent: string;
}) {
  const t = useMindTheme();
  const pct = Math.round(Math.max(0, Math.min(1, value)) * 100);
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-[11px]">
        <span style={{ color: t.textMuted }}>{label}</span>
        <span style={{ color: t.text }}>{valueLabel}</span>
      </div>
      <div className="h-1.5 rounded-full overflow-hidden" style={{ backgroundColor: t.border }}>
        <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, backgroundColor: accent }} />
      </div>
    </div>
  );
}

/** 人格观测 — 情绪与 DNA 特质 */
export function PersonalityObservationPanel() {
  const t = useMindTheme();
  const { overview, isLive, isDemo } = useMindOverview();
  const personality = overview.personality ?? EMPTY_PERSONALITY_OBSERVATION;
  const { emotion, dna } = personality;
  const offline = !isLive && !isDemo;

  return (
    <section
      className="rounded-2xl border overflow-hidden"
      style={{ borderColor: t.border, backgroundColor: t.surface }}
    >
      <div
        className="flex items-center gap-2 px-4 py-3 border-b"
        style={{ borderColor: t.border, backgroundColor: t.chatBg }}
      >
        <Brain className="w-4 h-4 shrink-0" style={{ color: t.purple }} />
        <div className="min-w-0">
          <h3 className="text-sm font-semibold" style={{ color: t.text }}>人格观测</h3>
          <p className="text-[11px]" style={{ color: t.textMuted }}>
            情绪引擎 · DNA 特质
          </p>
        </div>
        {offline && (
          <span className="ml-auto text-[10px] px-2 py-0.5 rounded-full" style={{ backgroundColor: t.orangeSoft, color: t.orange }}>
            等待连接
          </span>
        )}
      </div>

      <div className="p-4 grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="rounded-xl border p-3 space-y-3" style={{ borderColor: t.border, backgroundColor: t.bg }}>
          <div className="flex items-center gap-2">
            <Heart className="w-3.5 h-3.5" style={{ color: t.red }} />
            <p className="text-xs font-semibold" style={{ color: t.text }}>情绪状态</p>
            <span className="ml-auto text-[10px]" style={{ color: t.textLight }}>{emotion.last_updated_ago}</span>
          </div>
          <p className="text-lg font-semibold" style={{ color: t.text }}>
            {emotion.primary_emotion_label}
            <span className="text-sm font-normal ml-2" style={{ color: t.textMuted }}>
              强度 {emotion.intensity_label}
            </span>
          </p>
          <div className="grid grid-cols-3 gap-2 text-[11px]" style={{ color: t.textMuted }}>
            <span>效价: {emotion.valence_label}</span>
            <span>唤醒: {emotion.arousal_label}</span>
            <span>支配: {emotion.dominance_label}</span>
          </div>
          <MetricBar label="情绪强度" value={emotion.intensity} valueLabel={emotion.intensity_label} accent={t.red} />
          <MetricBar label="唤醒度" value={emotion.arousal} valueLabel={emotion.arousal_label} accent={t.orange} />
        </div>

        <div className="rounded-xl border p-3 space-y-3" style={{ borderColor: t.border, backgroundColor: t.bg }}>
          <div className="flex items-center gap-2">
            <Dna className="w-3.5 h-3.5" style={{ color: t.blue }} />
            <p className="text-xs font-semibold" style={{ color: t.text }}>人格 DNA</p>
            <span className="ml-auto text-[10px]" style={{ color: t.textLight }}>
              v{dna.version} · {dna.mutation_count} 次变异
            </span>
          </div>
          <div className="grid grid-cols-2 gap-2 text-[11px]" style={{ color: t.textMuted }}>
            <span>自我一致: {dna.self_consistency_label}</span>
            <span>整体稳定: {dna.overall_stability_label}</span>
          </div>
          <div className="space-y-2 max-h-[180px] overflow-y-auto pr-1">
            {(dna.traits.length ? dna.traits : []).map((trait) => (
              <MetricBar
                key={trait.key}
                label={trait.label}
                value={trait.value}
                valueLabel={trait.value_label}
                accent={t.blue}
              />
            ))}
            {!dna.traits.length && (
              <p className="text-[11px]" style={{ color: t.textMuted }}>暂无 DNA 特质数据</p>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
