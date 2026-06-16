"use client";

import { RefreshCw, Search } from "lucide-react";
import { fetchTokenField } from "@/lib/token/api";
import { bi, tokenL } from "@/lib/spine/labels";
import { useTokenStore } from "@/lib/token/tokenStore";
import { useMindTheme } from "../MindUiProvider";

type Props = {
  onRefreshObservatory: () => void;
  observatoryLoading?: boolean;
};

export function TokenTraceBar({ onRefreshObservatory, observatoryLoading }: Props) {
  const t = useMindTheme();
  const {
    traceInput,
    setTraceInput,
    setSelectedTraceId,
    setReport,
    setReportLoading,
    setError,
    setSelectedEventId,
  } = useTokenStore();

  const loadTrace = async (traceId: string) => {
    const tid = traceId.trim();
    if (!tid) return;
    setReportLoading(true);
    setError(null);
    setSelectedTraceId(tid);
    setSelectedEventId(null);
    try {
      const report = await fetchTokenField(tid);
      setReport(report);
    } catch (e) {
      setReport(null);
      setError(e instanceof Error ? e.message : "load failed");
    } finally {
      setReportLoading(false);
    }
  };

  return (
    <div className="flex flex-wrap items-center gap-2">
      <input
        value={traceInput}
        onChange={(e) => setTraceInput(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") void loadTrace(traceInput);
        }}
        placeholder={bi(tokenL.tracePlaceholder)}
        className="flex-1 min-w-[200px] text-sm px-3 py-2 rounded-lg border outline-none font-mono"
        style={{ borderColor: t.border, backgroundColor: t.chatBg, color: t.text }}
      />
      <button
        type="button"
        onClick={() => void loadTrace(traceInput)}
        className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium"
        style={{ backgroundColor: t.blue, color: "#fff" }}
      >
        <Search className="w-4 h-4" />
        {bi(tokenL.loadTrace)}
      </button>
      <button
        type="button"
        onClick={onRefreshObservatory}
        className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm border"
        style={{ borderColor: t.border, color: t.textMuted }}
      >
        <RefreshCw className={`w-4 h-4 ${observatoryLoading ? "animate-spin" : ""}`} />
        {bi(tokenL.refresh)}
      </button>
    </div>
  );
}
