"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Cpu, Check, Loader2, Play, Plug } from "lucide-react";
import { useMindConnection } from "../MindConnectionProvider";
import { useMindTheme } from "../MindUiProvider";
import { useOllamaStatus } from "@/hooks/useOllamaStatus";
import { getCognitiveSourceMetaForRuntime } from "@/lib/cognitiveSource";
import { resolveRuntimeConnectionDisplay } from "@/lib/runtimeConnection";
import { isTauriDesktop } from "@/lib/tauriDesktop";
import { isReleaseBuild } from "@/lib/releaseBuild";
import { bi, connectionL } from "@/lib/spine/labels";
import { floatTy } from "@/lib/floatTypography";
import { BootPhaseRail } from "./BootPhaseRail";
import { FloatingMiniDialog } from "./FloatingMiniDialog";
import { useFloatRuntimeMonitorContext } from "./FloatRuntimeMonitorContext";
import { useMindStore } from "@/cnexus-kernel/MindStore";
import { useMindOverview } from "@/cnexus-kernel";
import { useRuntimeStatus } from "@/hooks/useRuntimeStatus";

function stopDrag(e: React.PointerEvent | React.MouseEvent) {
  e.stopPropagation();
}

type Props = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  compact?: boolean;
};

export function FloatConnectionControl({ open, onOpenChange, compact = false }: Props) {
  const t = useMindTheme();
  const { effectiveMode, selectPreference } = useMindConnection();
  const monitor = useFloatRuntimeMonitorContext();
  const { isLive, isWarming, isDemo } = useMindOverview();
  const runtimeStatus = useRuntimeStatus();
  const connection = resolveRuntimeConnectionDisplay({
    effectiveMode,
    isLive,
    isWarming,
    isDemo,
    monitorPhase: monitor.phase,
  });
  const meta = getCognitiveSourceMetaForRuntime({
    effectiveMode,
    isLive,
    isWarming,
    isDemo,
    monitorPhase: monitor.phase,
  });
  const { status: ollama, start: startOllama, refresh: refreshOllama } = useOllamaStatus();
  const runtimeBootPhase = useMindStore((s) => s.runtimeBootPhase);
  const runtimeL3Status = useMindStore((s) => s.runtimeL3Status);

  const [runtimeBusy, setRuntimeBusy] = useState(false);
  const [ollamaBusy, setOllamaBusy] = useState(false);
  const [runtimeHint, setRuntimeHint] = useState<string | null>(null);
  const [connectSuccess, setConnectSuccess] = useState(false);
  const wasLiveRef = useRef(connection.canUseRuntimeApi);

  const runtimeConnected = connection.canUseRuntimeApi;
  const runtimeColor = runtimeConnected ? t.green : monitor.isWarming ? t.orange : t.textMuted;
  const ollamaRunning = ollama.running;

  const ollamaColor = ollamaRunning ? t.green : ollama.installed || ollama.binaryFound ? t.orange : t.red;
  const ollamaLabel = ollamaRunning
    ? bi(connectionL.ollamaRunning)
    : runtimeConnected
      ? ollama.installed || ollama.binaryFound
        ? bi(connectionL.ollamaStopped)
        : bi(connectionL.ollamaMissing)
      : ollama.loading
        ? bi(connectionL.ollamaProbing)
        : bi(connectionL.ollamaNotFound);

  const statusColor = runtimeConnected
    ? t.green
    : isWarming || monitor.isWarming || monitor.isChecking
      ? t.orange
      : meta.badgeColor === "purple"
        ? t.purple
        : t.orange;

  const setPanelOpen = useCallback(
    (next: boolean) => {
      onOpenChange(next);
    },
    [onOpenChange],
  );

  const finishConnectSuccess = useCallback(() => {
    setConnectSuccess(true);
    setRuntimeHint(null);
    void useMindStore.getState().hydrateRuntimeData();
    void refreshOllama();
    window.setTimeout(() => setPanelOpen(false), 800);
  }, [refreshOllama, setPanelOpen]);

  useEffect(() => {
    if (!open) {
      wasLiveRef.current = connection.canUseRuntimeApi;
      setConnectSuccess(false);
      setRuntimeHint(null);
      return;
    }
    void monitor.runProbe();
    void refreshOllama();
  }, [open, monitor, connection.canUseRuntimeApi, refreshOllama]);

  useEffect(() => {
    if (!open) return;
    if (connection.canUseRuntimeApi && !wasLiveRef.current && !runtimeBusy) {
      finishConnectSuccess();
    }
    wasLiveRef.current = connection.canUseRuntimeApi;
  }, [open, connection.canUseRuntimeApi, runtimeBusy, finishConnectSuccess]);

  const connectRuntime = useCallback(async () => {
    setRuntimeBusy(true);
    setConnectSuccess(false);
    setRuntimeHint(null);
    selectPreference("runtime");

    let keepBusy = false;
    try {
      const result = await monitor.runProbe();
      if (result === "ready") {
        finishConnectSuccess();
      } else if (result === "warming") {
        setRuntimeHint(runtimeStatus.label);
        keepBusy = true;
      } else {
        setRuntimeHint(
          isTauriDesktop()
            ? bi(connectionL.runtimeNotReadyDev)
            : bi(connectionL.runtimeNotReadyLocal),
        );
      }
    } catch (err) {
      setRuntimeHint(
        err instanceof Error ? err.message : bi(connectionL.runtimeNotReadyLocal),
      );
    } finally {
      if (!keepBusy) {
        setRuntimeBusy(false);
      }
    }
  }, [finishConnectSuccess, monitor, runtimeStatus.label, selectPreference]);

  useEffect(() => {
    if (!runtimeBusy || connection.canUseRuntimeApi) {
      if (connection.canUseRuntimeApi && runtimeBusy) {
        finishConnectSuccess();
        setRuntimeBusy(false);
      }
      return;
    }
    const id = window.setInterval(() => {
      void monitor.runProbe().then((result) => {
        if (result === "ready") {
          finishConnectSuccess();
          setRuntimeBusy(false);
        }
      });
    }, 2000);
    return () => window.clearInterval(id);
  }, [runtimeBusy, connection.canUseRuntimeApi, monitor, finishConnectSuccess]);

  const handleStartOllama = useCallback(async () => {
    if (!runtimeConnected) {
      setRuntimeHint(bi(connectionL.connectRuntimeFirst));
      return;
    }
    setOllamaBusy(true);
    try {
      await startOllama();
    } finally {
      setOllamaBusy(false);
    }
  }, [runtimeConnected, startOllama]);

  const runtimeStatusLabel = monitor.isChecking
    ? bi(connectionL.runtimeConnecting)
    : runtimeConnected
      ? bi(connectionL.runtimeConnected)
      : isWarming || monitor.isWarming
        ? runtimeStatus.label
        : effectiveMode === "fallback"
          ? bi(connectionL.runtimeDisconnected)
          : bi(connectionL.runtimeConnecting);

  const connectTitle = bi(connectionL.connectServices);

  return (
    <>
      <button
        type="button"
        className={
          compact
            ? "relative p-1 rounded-md transition hover:brightness-110 cursor-pointer shrink-0"
            : `inline-flex items-center gap-1 px-2 py-0.5 rounded-md border ${floatTy.btn} transition hover:brightness-110 cursor-pointer shrink-0 whitespace-nowrap`
        }
        style={
          compact
            ? {
                color: statusColor,
                backgroundColor: runtimeConnected ? `${t.green}18` : `${t.orange}18`,
                border: `1px solid ${runtimeConnected ? `${t.green}55` : `${t.orange}55`}`,
              }
            : {
                color: statusColor,
                backgroundColor: runtimeConnected ? `${t.green}18` : `${t.orange}18`,
                borderColor: runtimeConnected ? `${t.green}55` : `${t.orange}55`,
              }
        }
        title={connectTitle}
        aria-label={connectTitle}
        aria-expanded={open}
        onPointerDown={stopDrag}
        onClick={(e) => {
          e.stopPropagation();
          setPanelOpen(!open);
        }}
      >
        {compact ? (
          <>
            <Plug className="w-3.5 h-3.5" />
            <span
              className="absolute top-0.5 right-0.5 w-1.5 h-1.5 rounded-full"
              style={{
                backgroundColor: statusColor,
                boxShadow: runtimeConnected ? `0 0 6px ${statusColor}` : undefined,
              }}
            />
          </>
        ) : (
          <>
            <span
              className="w-1.5 h-1.5 rounded-full shrink-0"
              style={{ backgroundColor: statusColor, boxShadow: runtimeConnected ? `0 0 6px ${statusColor}` : undefined }}
            />
            {connectTitle}
          </>
        )}
      </button>

      {open && (
        <FloatingMiniDialog
          title={bi(connectionL.localServices)}
          subtitle={bi(connectionL.localServicesSub)}
          onClose={() => setPanelOpen(false)}
          width={320}
          placement="panel"
        >
          <div className={`space-y-3 ${floatTy.body}`}>
            <section
              className="rounded-lg border p-3 space-y-2"
              style={{ borderColor: t.border, backgroundColor: "rgba(255,255,255,0.03)" }}
            >
              <div className="flex items-start gap-2">
                <Cpu className="w-4 h-4 shrink-0 mt-0.5" style={{ color: runtimeColor }} />
                <div className="min-w-0 flex-1">
                  <p className={floatTy.label} style={{ color: t.text }}>
                    {runtimeStatusLabel}
                  </p>
                  <p className={`${floatTy.caption} mt-0.5`} style={{ color: t.textMuted }}>
                    REST 127.0.0.1:8000 · WS /ws/state
                  </p>
                  {(monitor.isWarming || monitor.isChecking) && runtimeBootPhase && (
                    <div className="mt-2">
                      <BootPhaseRail phase={runtimeBootPhase} l3={runtimeL3Status} />
                    </div>
                  )}
                </div>
              </div>
              <button
                type="button"
                className={`w-full inline-flex items-center justify-center gap-1.5 rounded-md py-2 ${floatTy.btn} text-white disabled:opacity-60`}
                style={{ backgroundColor: connectSuccess || runtimeConnected ? t.green : t.blue }}
                disabled={runtimeBusy || connectSuccess}
                onClick={() => void connectRuntime()}
              >
                {runtimeBusy ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : connectSuccess || runtimeConnected ? (
                  <Check className="w-3.5 h-3.5" />
                ) : (
                  <Play className="w-3.5 h-3.5" />
                )}
                {runtimeBusy
                  ? bi(connectionL.runtimeConnecting)
                  : connectSuccess
                    ? bi(connectionL.runtimeConnected)
                    : runtimeConnected
                      ? bi(connectionL.reconnectRuntime)
                      : bi(connectionL.connectRuntime)}
              </button>
            </section>

            <section
              className="rounded-lg border p-3 space-y-2"
              style={{ borderColor: t.border, backgroundColor: "rgba(255,255,255,0.03)" }}
            >
              <div className="flex items-center gap-2">
                <span
                  className="w-2 h-2 rounded-full shrink-0"
                  style={{
                    backgroundColor: ollamaColor,
                    boxShadow: ollamaRunning ? `0 0 6px ${ollamaColor}` : undefined,
                  }}
                />
                <div className="min-w-0 flex-1">
                  <p className={floatTy.label} style={{ color: t.text }}>
                    {ollamaLabel}
                  </p>
                  <p className={`${floatTy.caption} mt-0.5`} style={{ color: t.textMuted }}>
                    {runtimeConnected ? ollama.host : bi(connectionL.ollamaOfflineProbe)}
                  </p>
                </div>
              </div>
              <button
                type="button"
                className={`w-full inline-flex items-center justify-center gap-1.5 rounded-md py-2 ${floatTy.btn} disabled:opacity-60`}
                style={{
                  color: t.text,
                  backgroundColor: `${t.green}22`,
                  border: `1px solid ${t.green}55`,
                }}
                disabled={ollamaBusy || ollamaRunning || !runtimeConnected}
                onClick={() => void handleStartOllama()}
              >
                {ollamaBusy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
                {ollamaRunning ? bi(connectionL.ollamaAlreadyRunning) : ollamaBusy ? bi(connectionL.ollamaStarting) : bi(connectionL.startOllama)}
              </button>
              {!runtimeConnected && ollamaRunning && (
                <p className={floatTy.caption} style={{ color: t.orange }}>
                  {bi(connectionL.ollamaNeedsRuntime)}
                </p>
              )}
            </section>

            {connectSuccess && (
              <p
                className={`${floatTy.caption} leading-relaxed rounded-md px-2 py-1.5`}
                style={{ color: t.green, backgroundColor: `${t.green}14` }}
              >
                {bi(connectionL.runtimeConnectedSuccess)}
              </p>
            )}

            {runtimeHint && (
              <p className={`${floatTy.caption} leading-relaxed rounded-md px-2 py-1.5`} style={{ color: t.orange, backgroundColor: `${t.orange}14` }}>
                {runtimeHint}
              </p>
            )}

            {isTauriDesktop() && !isReleaseBuild && (
              <p className={`${floatTy.caption} leading-relaxed`} style={{ color: t.textLight }}>
                {bi(connectionL.devSidecarHint)}{" "}
                <span className="font-mono">python -m api.main</span>。
              </p>
            )}
          </div>
        </FloatingMiniDialog>
      )}
    </>
  );
}
