"use client";

import { useSyncExternalStore } from "react";
import {
  getRuntimeReachabilitySnapshot,
  subscribeRuntimeReachabilityStore,
  type RuntimeReachabilityView,
} from "@/cnexus-kernel/runtimeReachabilityStore";

export function useRuntimeReachability(): RuntimeReachabilityView {
  return useSyncExternalStore(
    subscribeRuntimeReachabilityStore,
    getRuntimeReachabilitySnapshot,
    getRuntimeReachabilitySnapshot,
  );
}

export type { RuntimeReachabilityView, ConnectionPhase } from "@/cnexus-kernel/runtimeReachabilityStore";
