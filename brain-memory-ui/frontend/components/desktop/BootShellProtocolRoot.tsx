"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useMindConnection, useMindStore } from "@/cnexus-kernel";
import { isRuntimeReady } from "@/lib/api";
import {
  bootPhaseFromRustState,
  emitBootHeartbeat,
} from "@/lib/bootProtocol";
import { useFloatingBarStore } from "@/lib/floatingBarStore";
import { useTauriDesktopSync } from "@/hooks/useTauriDesktopSync";
import {
  bootFallbackDemo,
  getBootState,
  grantUiRender,
  initTauriDesktop,
  isRuntimeBootTimedOut,
  isTauriDesktop,
  listenFloatRevealed,
  listenRuntimeBootTimeout,
  listenRuntimeBundleMissing,
  listenRuntimeInitFailed,
  listenRuntimeReady,
  listenRuntimeSpawnFailed,
  getRuntimeBootFailure,
  fetchRuntimeWarmHealth,
  revealTauriFloatWindow,
  showTauriFloatWindow,
  syncTauriFloatWindow,
} from "@/lib/tauriDesktop";
import { bi, bootL } from "@/lib/spine/labels";
import { BootShell } from "./BootShell";

type Props = { children: React.ReactNode };

const POLL_MS = 500;
const READY_PROBE_ATTEMPTS = 12;
const READY_PROBE_INTERVAL_MS = 250;
const BOOT_FALLBACK_MS = 125_000;
const FLOAT_BOOT_SETTLE_MS = 1_000;

/** Desktop root wrapper — Invariant A shell + boot FSM + Rust heartbeat protocol. */
export function BootShellProtocolRoot({ children }: Props) {
  const { hydrated, configReady, selectPreference } = useMindConnection();
  const barHydrated = useFloatingBarStore((s) => s.hydrated);
  const hydrateBar = useFloatingBarStore((s) => s.hydrate);
  const stage = useFloatingBarStore((s) => s.stage);
  const pinned = useFloatingBarStore((s) => s.pinned);
  const setStage = useFloatingBarStore((s) => s.setStage);

  useTauriDesktopSync();
  const [bootMode, setBootMode] = useState<"idle" | "runtime" | "demo">("idle");
  const [floatActive, setFloatActive] = useState(false);
  const [degraded, setDegraded] = useState(false);
  const [bootFailureDetail, setBootFailureDetail] = useState<string | undefined>();
  const [rustState, setRustState] = useState(0);
  const shownRef = useRef(false);
  const bootingRef = useRef(false);
  const lastPhase = useRef("");

  const configLoading = !hydrated || !configReady;

  useEffect(() => {
    if (!isTauriDesktop()) return;
    hydrateBar();
    void initTauriDesktop();
  }, [hydrateBar]);

  const tryShowFloat = useCallback(
    async (demoFallback: boolean) => {
      if (shownRef.current || bootingRef.current) return;
      if (!hydrated || !configReady || !barHydrated) return;

      bootingRef.current = true;
      try {
        if (demoFallback) {
          selectPreference("demo");
          await bootFallbackDemo();
        } else {
          const rustState = await getBootState();
          await useMindStore.getState().syncSystemCapability();
          const alreadyReady =
            rustState >= 2 || useMindStore.getState().runtimeOperationalReady;
          if (!alreadyReady) {
            await new Promise((r) => window.setTimeout(r, FLOAT_BOOT_SETTLE_MS));
          }
          let ok = alreadyReady;
          for (let i = 0; i < READY_PROBE_ATTEMPTS && !ok; i++) {
            await useMindStore.getState().syncSystemCapability();
            ok = useMindStore.getState().runtimeOperationalReady;
            if (!ok) {
              ok = await isRuntimeReady({ wsTimeoutMs: 2000 });
            }
            if (!ok) {
              await new Promise((r) => window.setTimeout(r, READY_PROBE_INTERVAL_MS));
            }
          }
          if (!ok) {
            for (let i = 0; i < 4 && !ok; i++) {
              await useMindStore.getState().syncSystemCapability();
              ok =
                useMindStore.getState().runtimeOperationalReady ||
                (await isRuntimeReady({ wsTimeoutMs: 2000, skipWs: true }));
              if (!ok) {
                await new Promise((r) => window.setTimeout(r, READY_PROBE_INTERVAL_MS));
              }
            }
          }
          if (!ok) {
            const state = await getBootState();
            if (state >= 2) ok = true;
          }
          if (!ok) {
            setDegraded(true);
            // Keep runtime preference — kernel enters fallback until sidecar is ready.
            await grantUiRender().catch(() => undefined);
          } else {
            await grantUiRender();
          }
        }
        await syncTauriFloatWindow(stage, pinned);
        await showTauriFloatWindow();
        shownRef.current = true;
        setFloatActive(true);
      } catch (err) {
        console.error("[cnexus] failed to show float window", err);
        setDegraded(true);
        try {
          await revealTauriFloatWindow();
          if (stage === "dock") setStage("bar");
          shownRef.current = true;
          setFloatActive(true);
        } catch (revealErr) {
          console.error("[cnexus] reveal float fallback failed", revealErr);
        }
      } finally {
        bootingRef.current = false;
      }
    },
    [hydrated, configReady, barHydrated, stage, pinned, selectPreference, setStage],
  );

  const syncBootModeFromRust = useCallback(async () => {
    if (!isTauriDesktop() || shownRef.current) return;

    const state = await getBootState();
    if (state >= 4) {
      shownRef.current = true;
      setFloatActive(true);
      return;
    }
    if (state >= 2) {
      setBootMode((mode) => (mode === "idle" ? "runtime" : mode));
      return;
    }
    if (await isRuntimeBootTimedOut()) {
      setDegraded(true);
      setBootMode((mode) => (mode === "idle" ? "runtime" : mode));
    }
  }, []);

  useEffect(() => {
    if (!isTauriDesktop()) return;
    let unlisten: (() => void) | undefined;
    void listenFloatRevealed(() => {
      shownRef.current = true;
      setFloatActive(true);
      if (useFloatingBarStore.getState().stage === "dock") {
        setStage("bar");
      }
    }).then((fn) => {
      unlisten = fn;
    });
    return () => unlisten?.();
  }, [setStage]);

  useEffect(() => {
    if (!isTauriDesktop() || !hydrated || !configReady) return;
    selectPreference("runtime");
    setBootMode((mode) => (mode === "idle" ? "runtime" : mode));
  }, [hydrated, configReady, selectPreference]);

  const resolveBootFailureLabel = useCallback((reason: string | null | undefined) => {
    if (!reason) return undefined;
    if (reason === "bundle_missing") return bi(bootL.runtimeBundleMissing);
    return `${bi(bootL.runtimeInitFailed)}: ${reason}`;
  }, []);

  useEffect(() => {
    if (!isTauriDesktop()) return;
    let unlistenReady: (() => void) | undefined;
    let unlistenTimeout: (() => void) | undefined;
    let unlistenBundle: (() => void) | undefined;
    let unlistenInit: (() => void) | undefined;
    let unlistenSpawn: (() => void) | undefined;
    let cancelled = false;

    void (async () => {
      unlistenReady = await listenRuntimeReady(() => {
        setBootMode("runtime");
        selectPreference("runtime");
        setBootFailureDetail(undefined);
      });
      unlistenTimeout = await listenRuntimeBootTimeout(() => {
        setDegraded(true);
        setBootMode("runtime");
      });
      unlistenBundle = await listenRuntimeBundleMissing(() => {
        setDegraded(true);
        setBootFailureDetail(bi(bootL.runtimeBundleMissing));
      });
      unlistenInit = await listenRuntimeInitFailed((msg) => {
        setDegraded(true);
        setBootFailureDetail(`${bi(bootL.runtimeInitFailed)}: ${msg}`);
      });
      unlistenSpawn = await listenRuntimeSpawnFailed((msg) => {
        setDegraded(true);
        setBootFailureDetail(`${bi(bootL.runtimeSpawnFailed)}: ${msg}`);
      });
      if (!cancelled) {
        const failure = await getRuntimeBootFailure();
        const label = resolveBootFailureLabel(failure);
        if (label) {
          setDegraded(true);
          setBootFailureDetail(label);
        }
        await syncBootModeFromRust();
      }
    })();

    const fallback = window.setTimeout(() => {
      if (!shownRef.current) {
        setDegraded(true);
        setBootMode((mode) => (mode === "idle" ? "runtime" : mode));
      }
    }, BOOT_FALLBACK_MS);

    return () => {
      cancelled = true;
      unlistenReady?.();
      unlistenTimeout?.();
      unlistenBundle?.();
      unlistenInit?.();
      unlistenSpawn?.();
      window.clearTimeout(fallback);
    };
  }, [syncBootModeFromRust, selectPreference, resolveBootFailureLabel]);

  useEffect(() => {
    if (bootMode === "runtime") void tryShowFloat(false);
    if (bootMode === "demo") void tryShowFloat(true);
  }, [bootMode, tryShowFloat]);

  useEffect(() => {
    if (!isTauriDesktop() || shownRef.current) return;
    const retry = window.setInterval(() => {
      if (shownRef.current) return;
      void syncBootModeFromRust();
      if (degraded && !bootFailureDetail) {
        void fetchRuntimeWarmHealth().then((warm) => {
          if (warm?.init_error) {
            setBootFailureDetail(`${bi(bootL.runtimeInitFailed)}: ${warm.init_error}`);
          }
        });
        void getRuntimeBootFailure().then((failure) => {
          const label = resolveBootFailureLabel(failure);
          if (label) setBootFailureDetail(label);
        });
      }
    }, POLL_MS);
    return () => window.clearInterval(retry);
  }, [syncBootModeFromRust, degraded, bootFailureDetail, resolveBootFailureLabel]);

  useEffect(() => {
    if (!isTauriDesktop()) return;

    let cancelled = false;

    const poll = async () => {
      const state = await getBootState().catch(() => 0);
      if (cancelled) return;
      setRustState(state);

      const phase = configLoading
        ? "config"
        : bootPhaseFromRustState(state, {
            degraded,
            floatContent: floatActive,
          });

      if (phase !== lastPhase.current) {
        lastPhase.current = phase;
        void emitBootHeartbeat({
          phase,
          rustBootState: state,
          mounted: true,
          detail: configLoading ? bi(bootL.initProduct) : rustState === 1 ? bi(bootL.runtimeStarting) : undefined,
        });
      }
    };

    void poll();
    const id = window.setInterval(() => void poll(), POLL_MS);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, [configLoading, floatActive, degraded]);

  if (!isTauriDesktop()) {
    return <>{children}</>;
  }

  const showOverlay = configLoading || !floatActive;
  const overlayPhase = configLoading
    ? "config"
    : bootPhaseFromRustState(rustState, { degraded, floatContent: floatActive });
  const contentVisible = !configLoading && floatActive;

  const bootDetail = configLoading
    ? bi(bootL.initProduct)
    : bootFailureDetail
      ? bootFailureDetail
      : rustState === 1
        ? bi(bootL.runtimeStarting)
        : degraded
          ? bi(bootL.degraded)
          : undefined;

  return (
    <div className="relative w-full h-full min-h-0 overflow-hidden">
      {showOverlay && (
        <div className="absolute inset-0 z-10">
          <BootShell
            phase={overlayPhase}
            rustBootState={rustState}
            detail={bootDetail}
          />
        </div>
      )}
      {contentVisible ? (
        <div className="relative w-full h-full min-h-0 overflow-hidden">{children}</div>
      ) : null}
    </div>
  );
}
