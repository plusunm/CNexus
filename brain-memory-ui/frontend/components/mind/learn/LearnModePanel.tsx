"use client";

import { useState, type ReactNode, useEffect } from "react";
import { BookOpen, Brain, ChevronDown, ChevronUp, Loader2, Search, Wrench } from "lucide-react";
import { useQueryStore } from "@/lib/queryStore";
import { useKernelLearn } from "@/hooks/useKernelLearn";
import { useMindTheme } from "../MindUiProvider";
import type { LearnDisplayMode } from "@/lib/kernelRecord";
import { fetchExecutionRecord, fetchRecentTraceIds } from "@/lib/kernelRecord";
import { ExecutionRecordTruthPanel } from "../query/ExecutionRecordTruthPanel";

const MODE_OPTIONS: { id: LearnDisplayMode; label: string; icon: typeof BookOpen }[] = [
  { id: "learn", label: "学习模式", icon: BookOpen },
  { id: "hybrid", label: "混合模式", icon: Brain },
  { id: "engineer", label: "工程模式", icon: Wrench },
];

const MODE_BADGE: Record<string, { label: string; color: string }> = {
  fast: { label: "快速路径", color: "#22c55e" },
  standard: { label: "标准路径", color: "#3b82f6" },
  deep: { label: "深度执行", color: "#a855f7" },
};

export function LearnModePanel() {
  const t = useMindTheme();
  const query = useQueryStore((s) => s.query);
  const setQuery = useQueryStore((s) => s.setQuery);
  const kernelRecord = useQueryStore((s) => s.kernelRecord);
  const setKernelRecord = useQueryStore((s) => s.setKernelRecord);
  const [localTrace, setLocalTrace] = useState(query);
  const [displayMode, setDisplayMode] = useState<LearnDisplayMode>("learn");
  const [engineerOpen, setEngineerOpen] = useState(false);
  const [lookupError, setLookupError] = useState<string | null>(null);
  const [lookupLoading, setLookupLoading] = useState(false);
  const [recentTraces, setRecentTraces] = useState<string[]>([]);

  const activeTrace = (localTrace || query || kernelRecord?.trace_id || "").trim();
  const { learn, loading, error, refresh } = useKernelLearn(activeTrace || null);

  const handleLookup = async (overrideId?: string) => {
    const id = (overrideId ?? localTrace).trim();
    if (!id) return;
    if (overrideId) setLocalTrace(overrideId);
    setLookupLoading(true);
    setLookupError(null);
    setQuery(id);
    try {
      await refresh(id);
      try {
        const record = await fetchExecutionRecord(id);
        setKernelRecord(record);
      } catch {
        setKernelRecord(null);
      }
    } catch (e) {
      setLookupError(e instanceof Error ? e.message : String(e));
    } finally {
      setLookupLoading(false);
    }
  };

  useEffect(() => {
    void (async () => {
      const ids = await fetchRecentTraceIds(12);
      setRecentTraces(ids);
      const seed = (query || kernelRecord?.trace_id || localTrace || "").trim();
      if (!seed && ids[0]) {
        await handleLookup(ids[0]);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- bootstrap recent trace once
  }, []);

  const modeBadge = learn ? MODE_BADGE[learn.mode] ?? MODE_BADGE.standard : null;

  return (
    <div className="w-full max-w-[960px] space-y-4">
      <header className="rounded-xl border p-4" style={{ borderColor: t.border, backgroundColor: t.surface }}>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="text-lg font-semibold flex items-center gap-2" style={{ color: t.text }}>
              <BookOpen className="w-5 h-5" style={{ color: t.purple }} />
              认知教学模式
            </h1>
            <p className="text-[12px] mt-1" style={{ color: t.textMuted }}>
              把一次 AI 执行翻译成人类能理解的故事（基于 ExecutionRecord 单真相）
            </p>
          </div>
          <div className="flex rounded-lg border overflow-hidden" style={{ borderColor: t.border }}>
            {MODE_OPTIONS.map((opt) => (
              <button
                key={opt.id}
                type="button"
                onClick={() => setDisplayMode(opt.id)}
                className="flex items-center gap-1.5 px-3 py-1.5 text-[11px] transition-colors"
                style={{
                  backgroundColor: displayMode === opt.id ? t.purpleSoft : t.chatBg,
                  color: displayMode === opt.id ? t.text : t.textMuted,
                }}
              >
                <opt.icon className="w-3.5 h-3.5" />
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        <div className="mt-4 flex gap-2">
          <input
            value={localTrace}
            onChange={(e) => setLocalTrace(e.target.value)}
            placeholder="输入 trace_id 查看 AI 做了什么…"
            className="flex-1 rounded-lg border px-3 py-2 text-sm font-mono"
            style={{
              borderColor: t.border,
              backgroundColor: t.chatBg,
              color: t.text,
            }}
          />
          <button
            type="button"
            onClick={() => void handleLookup()}
            disabled={lookupLoading || !localTrace.trim()}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium"
            style={{ backgroundColor: t.purple, color: "#fff" }}
          >
            {lookupLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
            解读
          </button>
        </div>
        {lookupError ? (
          <p className="text-[11px] mt-2" style={{ color: t.red }}>{lookupError}</p>
        ) : null}
        {recentTraces.length > 0 ? (
          <div className="mt-3 flex flex-wrap gap-1.5">
            <span className="text-[10px] w-full" style={{ color: t.textMuted }}>
              最近可查询的 trace_id：
            </span>
            {recentTraces.map((tid) => (
              <button
                key={tid}
                type="button"
                className="text-[10px] font-mono px-2 py-0.5 rounded border"
                style={{ borderColor: t.border, color: t.textMuted }}
                onClick={() => void handleLookup(tid)}
              >
                {tid.length > 18 ? `${tid.slice(0, 18)}…` : tid}
              </button>
            ))}
          </div>
        ) : null}
      </header>

      {!activeTrace ? (
        <EmptyHint t={t} />
      ) : loading || lookupLoading ? (
        <div className="flex items-center justify-center py-20 gap-2" style={{ color: t.textMuted }}>
          <Loader2 className="w-5 h-5 animate-spin" />
          正在生成认知解释…
        </div>
      ) : error ? (
        <div className="rounded-xl border p-6 text-center" style={{ borderColor: t.border, color: t.red }}>
          {error}
        </div>
      ) : learn ? (
        <div className="space-y-4">
          <Section title="📌 摘要" t={t}>
            <p style={{ color: t.text }}>{learn.summary}</p>
            {modeBadge ? (
              <span
                className="inline-block mt-2 text-[11px] px-2 py-0.5 rounded-full border"
                style={{ borderColor: modeBadge.color, color: modeBadge.color }}
              >
                {modeBadge.label} · {learn.execution_tier}
              </span>
            ) : null}
          </Section>

          {(displayMode === "learn" || displayMode === "hybrid") && (
            <>
              <Section title="👶 初学者视角" t={t}>
                <PreBlock text={learn.beginner_view} t={t} />
              </Section>
              <Section title="🧑 进阶视角" t={t}>
                <PreBlock text={learn.intermediate_view} t={t} />
              </Section>
              <Section title="📖 执行故事" t={t}>
                <PreBlock text={learn.execution_story} t={t} />
              </Section>
              <Section title="🧠 使用的记忆" t={t}>
                <ul className="space-y-1 text-[13px]" style={{ color: t.text }}>
                  {learn.memory_view.map((m, i) => (
                    <li key={i}>• {m}</li>
                  ))}
                </ul>
              </Section>
              <Section title="⚙️ 为什么是这样回答" t={t}>
                <p className="text-[13px]" style={{ color: t.text }}>{learn.why_this_result}</p>
              </Section>
              <Section title="⏱ 快慢原因" t={t}>
                <p className="text-[13px]" style={{ color: t.text }}>{learn.why_it_feels_fast_or_slow}</p>
              </Section>
              <Section title="🧬 心智模型" t={t}>
                <PreBlock text={learn.mental_model} t={t} />
              </Section>
            </>
          )}

          {(displayMode === "engineer" || displayMode === "hybrid") && (
            <div className="rounded-xl border overflow-hidden" style={{ borderColor: t.border }}>
              <button
                type="button"
                className="w-full flex items-center justify-between px-4 py-3 text-left"
                style={{ backgroundColor: t.surface }}
                onClick={() => setEngineerOpen((v) => !v)}
              >
                <span className="text-sm font-medium flex items-center gap-2" style={{ color: t.text }}>
                  <Wrench className="w-4 h-4" />
                  工程视图（Expert + Kernel Record）
                </span>
                {engineerOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
              </button>
              {engineerOpen || displayMode === "engineer" ? (
                <div>
                  <Section title="🧠 Expert View" t={t} nested>
                    <PreBlock text={learn.expert_view} t={t} mono />
                  </Section>
                  {kernelRecord && kernelRecord.trace_id === learn.trace_id ? (
                    <ExecutionRecordTruthPanel record={kernelRecord} />
                  ) : null}
                </div>
              ) : null}
            </div>
          )}
        </div>
      ) : null}
    </div>
  );
}

function Section({
  title,
  children,
  t,
  nested,
}: {
  title: string;
  children: ReactNode;
  t: ReturnType<typeof useMindTheme>;
  nested?: boolean;
}) {
  return (
    <div
      className={nested ? "border-t" : "rounded-xl border"}
      style={{
        borderColor: t.border,
        backgroundColor: nested ? t.chatBg : t.surface,
      }}
    >
      <div className="px-4 py-2 border-b text-[11px] font-semibold uppercase tracking-wide" style={{ borderColor: t.border, color: t.textMuted }}>
        {title}
      </div>
      <div className="px-4 py-3">{children}</div>
    </div>
  );
}

function PreBlock({
  text,
  t,
  mono,
}: {
  text: string;
  t: ReturnType<typeof useMindTheme>;
  mono?: boolean;
}) {
  return (
    <pre
      className={`text-[13px] leading-relaxed whitespace-pre-wrap ${mono ? "font-mono text-[11px]" : ""}`}
      style={{ color: t.text }}
    >
      {text}
    </pre>
  );
}

function EmptyHint({ t }: { t: ReturnType<typeof useMindTheme> }) {
  return (
    <div
      className="rounded-xl border p-8 text-center"
      style={{ borderColor: t.border, backgroundColor: t.surface, color: t.textMuted }}
    >
      <Brain className="w-10 h-10 mx-auto mb-3 opacity-50" />
      <p className="text-sm">在 Query 控制台执行一次对话后，将 trace_id 粘贴到上方</p>
      <p className="text-[11px] mt-2">或从执行 Spine 视图复制 trace_id 来查看 AI 做了什么</p>
    </div>
  );
}
