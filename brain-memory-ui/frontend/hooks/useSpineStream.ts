"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { cnexusProductApi } from "@/lib/api";
import { useMindOverview } from "@/cnexus-kernel";
import { DEMO_SPINE_EVENTS } from "@/lib/demoSpineEvents";
import { buildSpineFromGtbs, buildSpineFromRuntimeLogs } from "@/lib/spineMapper";
import { useSpineStore } from "@/lib/spineStore";
import { useMindStore } from "@/cnexus-kernel/MindStore";
import type { SpineEvent } from "@/lib/spineTypes";
import { SPINE_LIVE_POLL_MS } from "@/lib/uiPollIntervals";

export type SpineEmptyReason = "offline" | "no_events" | null;

export function useSpineStream(limit = 400) {
  const { isDemo, isLive, isWarming } = useMindOverview();
  const runtimeOperationalReady = useMindStore((s) => s.runtimeOperationalReady);
  const [initialLoading, setInitialLoading] = useState(!isDemo);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [emptyReason, setEmptyReason] = useState<SpineEmptyReason>(null);
  const setEvents = useSpineStore((s) => s.setEvents);
  const appendEvents = useSpineStore((s) => s.appendEvents);
  const streamMode = useSpineStore((s) => s.streamMode);
  const hasLoadedRef = useRef(isDemo);

  const applyEvents = useCallback(
    (incoming: SpineEvent[]) => {
      if (incoming.length === 0) {
        setEmptyReason(hasLoadedRef.current ? null : "no_events");
        return;
      }
      if (!hasLoadedRef.current || useSpineStore.getState().events.length === 0) {
        setEvents(incoming);
      } else {
        appendEvents(incoming);
      }
      hasLoadedRef.current = true;
      setEmptyReason(null);
    },
    [appendEvents, setEvents],
  );

  const refresh = useCallback(
    async (opts?: { initial?: boolean }) => {
      if (isDemo) {
        setEvents(DEMO_SPINE_EVENTS);
        setInitialLoading(false);
        setRefreshing(false);
        setError(null);
        setEmptyReason(null);
        hasLoadedRef.current = true;
        return;
      }
      if (!isLive && !isWarming) {
        setInitialLoading(false);
        setRefreshing(false);
        setError(null);
        setEmptyReason("offline");
        return;
      }

      const background = !opts?.initial && hasLoadedRef.current;
      if (background) setRefreshing(true);
      else setInitialLoading(true);

      try {
        const payload = await cnexusProductApi.gtbsEvents(limit);
        let events = buildSpineFromGtbs(payload.events ?? []);
        if (events.length === 0) {
          const logPayload = await cnexusProductApi.runtimeLogs(Math.min(limit, 120));
          events = buildSpineFromRuntimeLogs(logPayload.logs ?? []);
        }
        applyEvents(events);
        setError(null);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load spine");
        if (!hasLoadedRef.current) setEmptyReason("offline");
      } finally {
        setInitialLoading(false);
        setRefreshing(false);
      }
    },
    [applyEvents, isDemo, isLive, isWarming, limit, setEvents],
  );

  useEffect(() => {
    void refresh({ initial: !hasLoadedRef.current });
  }, [refresh]);

  useEffect(() => {
    if (runtimeOperationalReady) void refresh();
  }, [runtimeOperationalReady, refresh]);

  useEffect(() => {
    if (isDemo || !isLive || streamMode !== "live") return;
    const id = window.setInterval(() => void refresh(), SPINE_LIVE_POLL_MS);
    return () => window.clearInterval(id);
  }, [isDemo, isLive, streamMode, refresh]);

  return {
    loading: initialLoading,
    initialLoading,
    refreshing,
    error,
    refresh,
    isDemo,
    isLive,
    isWarming,
    emptyReason,
  };
}
