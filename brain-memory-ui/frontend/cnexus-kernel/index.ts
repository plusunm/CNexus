/**
 * CNexus Product Kernel — public surface only.
 * Shells import from here; no direct store/WS/API in UI components.
 */

export { useMindStore } from "./MindStore";
export { useMindOverview } from "./useMindOverview";
export type { MindOverview } from "./useMindOverview";

export {
  assertMindOverviewContract,
  extractMindSignals,
  healthColor,
} from "./MindOverviewContract";
export type {
  MindSignals,
  MindGoalSignal,
  MindConflictSignal,
  MindHealthSignal,
  MindMemorySignal,
} from "./MindOverviewContract";

export {
  CONNECTION_LABELS,
  EFFECTIVE_MODE_LABELS,
  loadConnectionPreference,
  saveConnectionPreference,
  clearConnectionPreference,
  resolveEffectiveMode,
  type ConnectionPreference,
  type EffectiveConnectionMode,
  /** @deprecated */ loadConnectionMode,
  /** @deprecated */ saveConnectionMode,
  /** @deprecated */ clearConnectionMode,
  /** @deprecated */ type MindConnectionMode,
} from "./connectionMode";

export { MindConnectionProvider, useMindConnection } from "./MindConnectionProvider";
export { MindRuntimeBridge } from "./MindRuntimeBridge";
export { MindKernelProvider } from "./MindKernelProvider";
export { useRuntimeReachability } from "@/hooks/useRuntimeReachability";
export type { RuntimeReachabilityView, ConnectionPhase } from "./runtimeReachabilityStore";

export type { ShellLayout, ShellPanel, OverviewView } from "./shellTypes";
export { parseShellLayout, parseShellPanel, parseOverviewView } from "./shellTypes";

export {
  getEdition,
  setEdition,
  parseEdition,
  getEditionProfile,
  defaultConnectionPreference,
  resolveEdition,
  loadStoredEdition,
  saveStoredEdition,
  loadStoredLicense,
  saveStoredLicense,
  EDITION_PROFILES,
  type CnexusEdition,
  type EditionProfile,
} from "./edition";
