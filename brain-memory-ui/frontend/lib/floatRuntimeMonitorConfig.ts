import { FLOAT_IDLE_PROBE_MS } from "./uiPollIntervals";

/** Poll tiers for float Runtime monitor — Plan B layered exit. */
export type PollTier = "off" | "boost" | "watch" | "idle";

export const POLL_TIER_MS: Record<Exclude<PollTier, "off">, number> = {
  boost: 500,
  watch: 2_500,
  idle: FLOAT_IDLE_PROBE_MS,
};

/** Consecutive ready probes before dropping to idle heartbeat. */
export const READY_STREAK_FOR_IDLE = 3;
