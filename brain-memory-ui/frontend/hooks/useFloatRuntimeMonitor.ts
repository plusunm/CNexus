"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { isTauriDesktop, listenRuntimeReady } from "@/lib/tauriDesktop";
import { useMindStore } from "@/cnexus-kernel/MindStore";
import {
  markRuntimeReachabilityBooting,
  markRuntimeReachabilityReady,
} from "@/cnexus-kernel/runtimeReachabilityStore";
import { useMindConnection } from "@/cnexus-kernel/MindConnectionProvider";
import {
  POLL_TIER_MS,
  READY_STREAK_FOR_IDLE,
  type PollTier,
} from "@/lib/floatRuntimeMonitorConfig";

export type RuntimeConnectionPhase = "offline" | "warming" | "ready" | "checking";

type Options = {
  /** Float bar/expanded visible — not dock / not tray-hidden */
  isExposed?: boolean;
  /** Connection dialog open → boost tier */
  boost?: boolean;
};

function resolvePollTier(
  shouldPoll: boolean,
  boost: boolean,
  phase: RuntimeConnectionPhase,
  readyStreak: number,
): PollTier {
  if (!shouldPoll) return "off";
  if (boost) return "boost";
  if (phase !== "ready") return "watch";
  if (readyStreak >= READY_STREAK_FOR_IDLE) return "idle";
  return "watch";
}

/**
 * Read-only Runtime connection monitor for float UI.
 * Polls status only — does not warm, restart, or auto-recover runtime.
 */
export function useFloatRuntimeMonitor({ isExposed = true, boost = false }: Options = {}) {
  const { preference } = useMindConnection();
  const syncSystemCapability = useMindStore((s) => s.syncSystemCapability);

  const [phase, setPhase] = useState<RuntimeConnectionPhase>("checking");
  const [tier, setTier] = useState<PollTier>("off");
  const [bootPhase, setBootPhase] = useState<string | null>(null);
  const [ready, setReady] = useState(false);
  const [reason, setReason] = useState<string | null>(null);
  const [progress, setProgress] = useState<number | null>(null);

  const phaseRef = useRef<RuntimeConnectionPhase>("checking");
  const readyStreakRef = useRef(0);
  const pollInFlight = useRef(false);
  const boostRef = useRef(boost);
  const isExposedRef = useRef(isExposed);

  boostRef.current = boost;
  isExposedRef.current = isExposed;

  const shouldPoll = preference === "runtime" && isExposed;

  const applyTierFromProbe = useCallback(
    (nextPhase: RuntimeConnectionPhase) => {
      if (nextPhase === "ready") {
        readyStreakRef.current += 1;
      } else {
        readyStreakRef.current = 0;
      }
      const nextTier = resolvePollTier(
        shouldPoll,
        boostRef.current,
        nextPhase,
        readyStreakRef.current,
      );
      setTier(nextTier);
      return nextTier;
    },
    [shouldPoll],
  );

  const runProbe = useCallback(async (): Promise<RuntimeConnectionPhase> => {
    if (!shouldPoll) {
      phaseRef.current = "offline";
      setPhase("offline");
      setTier("off");
      readyStreakRef.current = 0;
      return "offline";
    }

    if (pollInFlight.current) return phaseRef.current;
    pollInFlight.current = true;
    try {
      await syncSystemCapability();
      const store = useMindStore.getState();
      const result = store.runtimeOperationalReady
        ? "ready"
        : store.runtimeReachable
          ? "warming"
          : "offline";
      const bootPhase = store.runtimeBootPhase;

      const next: RuntimeConnectionPhase = result;
      phaseRef.current = next;
      setPhase(next);
      setBootPhase(bootPhase);
      setReady(store.runtimeOperationalReady);
      setReason(store.runtimeBootReason);
      setProgress(store.runtimeOperationalReady ? 100 : store.runtimeBootProgress);

      if (result === "ready") {
        markRuntimeReachabilityReady(bootPhase);
      } else if (result === "warming") {
        markRuntimeReachabilityBooting(bootPhase);
      }

      applyTierFromProbe(next);
      return next;
    } catch {
      phaseRef.current = "offline";
      setPhase("offline");
      readyStreakRef.current = 0;
      setTier(resolvePollTier(shouldPoll, boostRef.current, "offline", 0));
      return "offline";
    } finally {
      pollInFlight.current = false;
    }
  }, [applyTierFromProbe, shouldPoll, syncSystemCapability]);

  useEffect(() => {
    if (!shouldPoll) {
      readyStreakRef.current = 0;
      phaseRef.current = "offline";
      setPhase("offline");
      setTier("off");
      return;
    }

    setTier(
      resolvePollTier(true, boostRef.current, phaseRef.current, readyStreakRef.current),
    );
    void runProbe();
  }, [shouldPoll, runProbe]);

  useEffect(() => {
    if (!shouldPoll) return;
    setTier(
      resolvePollTier(true, boost, phaseRef.current, readyStreakRef.current),
    );
  }, [boost, shouldPoll]);

  useEffect(() => {
    if (!shouldPoll || tier === "off") return;

    const ms = POLL_TIER_MS[tier];
    const id = window.setInterval(() => void runProbe(), ms);
    return () => window.clearInterval(id);
  }, [shouldPoll, tier, runProbe]);

  useEffect(() => {
    if (!shouldPoll || !isTauriDesktop()) return;

    let unlisten: (() => void) | undefined;
    let cancelled = false;
    void listenRuntimeReady(() => {
      void runProbe();
    }).then((fn) => {
      if (cancelled) {
        fn();
        return;
      }
      unlisten = fn;
    });

    return () => {
      cancelled = true;
      unlisten?.();
    };
  }, [shouldPoll, runProbe]);

  return useMemo(
    () => ({
      phase,
      tier,
      bootPhase,
      ready,
      reason,
      progress,
      isLive: phase === "ready",
      isWarming: phase === "warming",
      isOffline: phase === "offline",
      isChecking: phase === "checking",
      runProbe,
    }),
    [phase, tier, bootPhase, ready, reason, progress, runProbe],
  );
}
