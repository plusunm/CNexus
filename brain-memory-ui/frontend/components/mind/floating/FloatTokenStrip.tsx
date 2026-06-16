"use client";

import { useCallback, useEffect, useState } from "react";
import { Coins, Loader2, RefreshCw } from "lucide-react";
import { useMindConnection, useMindOverview } from "@/cnexus-kernel";
import { useMindStore } from "@/cnexus-kernel/MindStore";
import { fetchRuntimeTokenTraces, fetchTokenObservatory } from "@/lib/token/api";
import { COST_COLOR } from "@/lib/token/format";
import type { TokenTrace } from "@/lib/token/types";
import { floatTy } from "@/lib/floatTypography";
import { bi, floatL, tokenL } from "@/lib/spine/labels";
import { isTauriDesktop, openTauriDashboard } from "@/lib/tauriDesktop";
import { EXECUTION_STATUS_POLL_MS } from "@/lib/uiPollIntervals";
import { useMindTheme } from "../MindUiProvider";

const TOKEN_CONSOLE_ROUTE = "/shell?layout=overview&view=token";

type Props = {
  traces: TokenTrace[];
  loading: boolean;
  error: string | null;
  onRefresh: () => void;
  traceMaxHeight?: number;
  isLive?: boolean;
  emptyHint?: string | null;
};

export function FloatTokenStrip({
  traces,
  loading,
  error,
  onRefresh,
  traceMaxHeight = 140,
  isLive = false,
  emptyHint = null,
}: Props) {
  const t = useMindTheme();
  const total = traces.reduce((s, x) => s + x.total, 0);
  const totalIn = traces.reduce((s, x) => s + x.tokens_in, 0);
  const totalOut = traces.reduce((s, x) => s + x.tokens_out, 0);

  const openTokenConsole = useCallback(() => {
    if (isTauriDesktop()) {
      void openTauriDashboard(TOKEN_CONSOLE_ROUTE);
      return;
    }
    if (typeof window === "undefined") return;
    const url = `${window.location.origin}${TOKEN_CONSOLE_ROUTE}`;
    window.open(url, "_blank", "noopener,noreferrer");
  }, []);

  return (
    <section
      className="shrink-0 flex flex-col min-h-0 border-t h-full"
      style={{ borderColor: t.border, backgroundColor: "rgba(0,0,0,0.12)" }}
      data-cnexus-float-token-strip
      data-no-drag
    >
      <div className="flex items-center justify-between gap-2 px-2.5 py-1.5 shrink-0">
        <div className="flex items-center gap-1.5 min-w-0">
          <Coins className="w-3.5 h-3.5 shrink-0" style={{ color: t.orange }} />
          <span className={`${floatTy.label} truncate`} style={{ color: t.text }}>
            {bi(floatL.tokenStrip)}
          </span>
        </div>
        <div className="flex items-center gap-1 shrink-0">
          <button
            type="button"
            onClick={onRefresh}
            disabled={loading}
            className="p-1 rounded border disabled:opacity-50"
            style={{ borderColor: t.border, color: t.textMuted }}
            aria-label="refresh"
          >
            <RefreshCw className={`w-3 h-3 ${loading ? "animate-spin" : ""}`} />
          </button>
          <button
            type="button"
            onClick={openTokenConsole}
            className={`${floatTy.link} px-2 py-1 rounded border whitespace-nowrap`}
            style={{ borderColor: t.border, color: t.textMuted }}
          >
            {bi(floatL.openTokenConsole)}
          </button>
        </div>
      </div>

      <div className={`grid grid-cols-3 gap-1.5 px-2.5 pb-2 ${floatTy.mono} shrink-0`}>
        <Stat label={tokenL.totalTokens.zh} value={total} color={t.text} />
        <Stat label={tokenL.tokensIn.zh} value={totalIn} color={t.blue} />
        <Stat label={tokenL.tokensOut.zh} value={totalOut} color={t.green} />
      </div>

      <div
        className="flex-1 min-h-0 overflow-y-auto cnexus-float-scroll px-2 pb-2"
        style={{ maxHeight: traceMaxHeight }}
      >
        {loading && traces.length === 0 ? (
          <p className={`${floatTy.caption} flex items-center gap-1.5 py-2`} style={{ color: t.textMuted }}>
            <Loader2 className="w-3 h-3 animate-spin" />
            {bi(floatL.tokenLoading)}
          </p>
        ) : null}
        {error && !loading ? (
          <p className={`${floatTy.caption} py-1`} style={{ color: t.orange }}>
            {error}
          </p>
        ) : null}
        {!loading && !error && traces.length === 0 ? (
          <p className={`${floatTy.caption} py-1`} style={{ color: t.textMuted }}>
            {emptyHint ?? (isLive ? bi(floatL.tokenEmptyLive) : bi(floatL.tokenEmpty))}
          </p>
        ) : null}
        {traces.slice(0, 12).map((trace) => (
          <div
            key={trace.trace_id}
            className={`flex items-center justify-between gap-2 py-1.5 border-b last:border-0 ${floatTy.mono}`}
            style={{ borderColor: t.border }}
          >
            <span className="truncate min-w-0" style={{ color: t.textMuted }}>
              {trace.trace_id.slice(0, 14)}
            </span>
            <span className="shrink-0" style={{ color: COST_COLOR[trace.cost_level] ?? t.text }}>
              {trace.total}
            </span>
            <span className="shrink-0 opacity-60" style={{ color: t.textLight }}>
              {trace.mode}
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}

function Stat({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className={`rounded-md border px-2 py-1.5 text-center ${floatTy.mono}`} style={{ borderColor: "rgba(128,128,128,0.25)" }}>
      <p className="opacity-70 truncate">{label}</p>
      <p style={{ color }}>{value}</p>
    </div>
  );
}

export function useFloatTokenTraces() {
  const { runtimeEnabled } = useMindConnection();
  const { isLive, isWarming } = useMindOverview();
  const runtimeOperationalReady = useMindStore((s) => s.runtimeOperationalReady);
  const [traces, setTraces] = useState<TokenTrace[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!isLive && !isWarming) {
      setTraces([]);
      setError(null);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      let obs = await fetchTokenObservatory(50).catch(() => null);
      if (!obs?.token_traces?.length) {
        obs = await fetchRuntimeTokenTraces();
      }
      setTraces(obs?.token_traces ?? []);
    } catch (e) {
      setTraces([]);
      setError(e instanceof Error ? e.message : "load failed");
    } finally {
      setLoading(false);
    }
  }, [isLive, isWarming]);

  useEffect(() => {
    if (!runtimeEnabled) {
      setTraces([]);
      return;
    }
    void refresh();
    const id = window.setInterval(() => void refresh(), EXECUTION_STATUS_POLL_MS);
    return () => window.clearInterval(id);
  }, [runtimeEnabled, refresh]);

  useEffect(() => {
    if (runtimeOperationalReady) void refresh();
  }, [runtimeOperationalReady, refresh]);

  const emptyHint =
    !isLive && !isWarming ? bi(floatL.tokenOffline) : traces.length === 0 && !loading ? bi(floatL.tokenEmptyLive) : null;

  return { traces, loading, error, refresh, isLive, emptyHint };
}
