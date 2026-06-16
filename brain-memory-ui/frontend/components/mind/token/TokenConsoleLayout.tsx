"use client";

import { useCallback, useEffect } from "react";
import { fetchRuntimeTokenTraces, fetchTokenField, fetchTokenObservatory } from "@/lib/token/api";
import { useMindOverview } from "@/cnexus-kernel";
import { useMindStore } from "@/cnexus-kernel/MindStore";
import { bi, biSection, tokenL } from "@/lib/spine/labels";
import { useTokenStore } from "@/lib/token/tokenStore";
import { useMindTheme } from "../MindUiProvider";
import { TokenTabs } from "./TokenTabs";
import { TokenTraceBar } from "./TokenTraceBar";
import { TokenTraceList } from "./TokenTraceList";
import { TokenEventInspector } from "./TokenEventInspector";
import { TokenOverviewPanel } from "./panels/TokenOverviewPanel";
import { TokenEventsPanel } from "./panels/TokenEventsPanel";
import { TokenFieldPanel } from "./panels/TokenFieldPanel";
import { TokenBindingPanel } from "./panels/TokenBindingPanel";
import { TokenInfluencePanel } from "./panels/TokenInfluencePanel";
import { TokenIdentityPanel } from "./panels/TokenInspectorPanel";

export function TokenConsoleLayout() {
  const t = useMindTheme();
  const { isLive } = useMindOverview();
  const runtimeOperationalReady = useMindStore((s) => s.runtimeOperationalReady);
  const {
    traces,
    setTraces,
    report,
    setReport,
    loading,
    setLoading,
    reportLoading,
    setReportLoading,
    error,
    setError,
    tab,
    selectedTraceId,
    setSelectedTraceId,
    setTraceInput,
    selectedEventId,
    setSelectedEventId,
  } = useTokenStore();

  const loadObservatory = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      let obs = await fetchTokenObservatory(100).catch(() => null);
      if (!obs?.token_traces?.length) {
        obs = await fetchRuntimeTokenTraces();
      }
      setTraces(obs.token_traces);
    } catch (e) {
      setTraces([]);
      setError(e instanceof Error ? e.message : "load failed");
    } finally {
      setLoading(false);
    }
  }, [setTraces, setLoading, setError]);

  const loadTrace = useCallback(
    async (traceId: string) => {
      const tid = traceId.trim();
      if (!tid) return;
      setReportLoading(true);
      setError(null);
      setSelectedTraceId(tid);
      setTraceInput(tid);
      setSelectedEventId(null);
      try {
        const data = await fetchTokenField(tid);
        setReport(data);
      } catch (e) {
        setReport(null);
        setError(e instanceof Error ? e.message : "trace load failed");
      } finally {
        setReportLoading(false);
      }
    },
    [setReport, setReportLoading, setError, setSelectedTraceId, setTraceInput, setSelectedEventId],
  );

  useEffect(() => {
    void loadObservatory();
  }, [loadObservatory]);

  useEffect(() => {
    if (runtimeOperationalReady) void loadObservatory();
  }, [runtimeOperationalReady, loadObservatory]);

  const traceSummary = traces.find((x) => x.trace_id === selectedTraceId) ?? null;
  const events = report?.token_events ?? [];

  const renderMain = () => {
    if (loading && !traces.length) {
      return (
        <p className="p-4 text-sm" style={{ color: t.textMuted }}>
          {bi(tokenL.loading)}
        </p>
      );
    }

    switch (tab) {
      case "overview":
        return <TokenOverviewPanel traces={traces} />;
      case "events":
        return report ? (
          <TokenEventsPanel
            events={events}
            selectedEventId={selectedEventId}
            onSelect={setSelectedEventId}
          />
        ) : (
          <EmptyTraceHint />
        );
      case "field":
        return report ? (
          <TokenFieldPanel report={report} onSelectEvent={setSelectedEventId} />
        ) : (
          <EmptyTraceHint />
        );
      case "binding":
        return report ? (
          <TokenBindingPanel report={report} onSelectSpine={setSelectedEventId} />
        ) : (
          <EmptyTraceHint />
        );
      case "influence":
        return report ? <TokenInfluencePanel report={report} /> : <EmptyTraceHint />;
      case "identity":
        return <TokenIdentityPanel report={report} traceSummary={traceSummary} />;
      default:
        return null;
    }
  };

  return (
    <div
      className="flex h-[calc(100vh-9rem)] max-h-[calc(100vh-9rem)] rounded-xl border overflow-hidden"
      style={{ borderColor: t.border }}
    >
      <div className="flex flex-col flex-1 min-w-0 min-h-0 overflow-hidden" style={{ backgroundColor: t.surface }}>
        <header className="px-4 py-3 border-b shrink-0 space-y-3" style={{ borderColor: t.border }}>
          <div>
            <h2 className="text-sm font-semibold" style={{ color: t.text }}>
              {biSection(tokenL.consoleTitle)}
            </h2>
            <p className="text-[11px]" style={{ color: t.textMuted }}>
              {biSection(tokenL.consoleSubtitle)}
            </p>
          </div>
          <TokenTraceBar onRefreshObservatory={() => void loadObservatory()} observatoryLoading={loading} />
          <TokenTabs />
        </header>

        {error ? (
          <p className="px-4 pt-3 text-sm" style={{ color: t.red }}>
            {error}
          </p>
        ) : null}

        {reportLoading ? (
          <p className="px-4 text-xs" style={{ color: t.textMuted }}>
            {bi(tokenL.loadingField)}
          </p>
        ) : null}

        <div
          className="grid grid-cols-1 lg:grid-cols-12 gap-0 lg:gap-px flex-1 min-h-0 h-0 overflow-hidden lg:grid-rows-1"
          style={{ backgroundColor: t.border }}
        >
          <div
            className="lg:col-span-2 p-3 flex flex-col min-h-0 overflow-hidden shrink-0 lg:shrink lg:h-full"
            style={{ backgroundColor: t.surface }}
          >
            <TokenTraceList
              traces={traces}
              selectedTraceId={selectedTraceId}
              onSelect={(id) => void loadTrace(id)}
            />
          </div>

          <div
            className="lg:col-span-7 p-3 min-h-0 overflow-hidden flex flex-col"
            style={{ backgroundColor: t.surface }}
          >
            <div className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden cnexus-trace-list-scroll">
              {renderMain()}
            </div>
          </div>

          <div
            className="lg:col-span-3 p-3 min-h-0 overflow-auto border-t lg:border-t-0"
            style={{ backgroundColor: t.surface, borderColor: t.border }}
          >
            <TokenEventInspector report={report} selectedEventId={selectedEventId} />
          </div>
        </div>
      </div>
    </div>
  );
}

function EmptyTraceHint() {
  const t = useMindTheme();
  return (
    <p className="text-sm opacity-60 p-4" style={{ color: t.textMuted }}>
      {bi(tokenL.selectTrace)}
    </p>
  );
}
