"use client";

import { Loader2, Sparkles } from "lucide-react";
import type { CognitiveOutput } from "@/lib/cognitiveTypes";
import { isReleaseBuild } from "@/lib/releaseBuild";
import { bi, homeL } from "@/lib/spine/labels";
import { useMindTheme } from "../MindUiProvider";

type Props = {
  data: CognitiveOutput;
  loading?: boolean;
  refreshing?: boolean;
  error?: string | null;
  isExample?: boolean;
  isEmpty?: boolean;
};

/** 运行摘要子页 — CSE 叙事 */
export function ValueSummaryPanel({ data, loading, refreshing, error, isExample, isEmpty }: Props) {
  const t = useMindTheme();
  const narrative = data.narrative?.trim();

  return (
    <section
      className="rounded-2xl border overflow-hidden relative"
      style={{ borderColor: t.purple, backgroundColor: t.surface }}
    >
      {loading && (
        <div
          className="absolute inset-0 flex items-center justify-center backdrop-blur-[1px] z-10"
          style={{ backgroundColor: "rgba(7,11,20,0.45)" }}
        >
          <Loader2 className="w-5 h-5 animate-spin" style={{ color: t.purple }} />
        </div>
      )}

      <div
        className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 px-4 py-3 border-b"
        style={{ borderColor: t.border, backgroundColor: t.chatBg }}
      >
        <div className="flex items-center gap-2 min-w-0">
          <Sparkles className="w-4 h-4 shrink-0" style={{ color: t.purple }} />
          <h3 className="text-sm font-semibold" style={{ color: t.text }}>
            {bi(homeL.valueSummary)}
          </h3>
          {refreshing && !loading && (
            <span
              className="w-1.5 h-1.5 rounded-full shrink-0 animate-pulse"
              style={{ backgroundColor: t.purple }}
              title="更新中"
            />
          )}
          {isExample && !isReleaseBuild && (
            <span
              className="text-[10px] px-1.5 py-0.5 rounded-full shrink-0"
              style={{ backgroundColor: t.purpleSoft, color: t.purple }}
            >
              {bi(homeL.example)}
            </span>
          )}
        </div>
      </div>

      <div className="px-4 py-4">
        {error && !loading && (
          <p className="text-sm" style={{ color: t.orange }}>
            {bi(homeL.valueLoadError)} — {error}
          </p>
        )}
        {!error && narrative && (
          <p className="text-sm leading-relaxed" style={{ color: t.text }}>
            {narrative}
          </p>
        )}
        {!error && !narrative && !loading && (
          <p className="text-sm leading-relaxed" style={{ color: t.textMuted }}>
            {bi(isEmpty ? homeL.valueEmptyLive : homeL.valueEmptyIdle)}
          </p>
        )}
      </div>
    </section>
  );
}
