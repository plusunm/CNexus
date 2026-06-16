import type {
  DriftSummaryView,
  ExecutionIdentityView,
  SpineFrontContractV1,
} from "./contract";

/** Unified identity view for EIV header + panel. */
export type ExecutionIdentityBundle = {
  id: string;
  stability: number;
  drift: boolean;
  equivalent_traces: string[];
  drift_variants: string[];
  signatures: {
    graph: string;
    state: string;
    control: string;
    causal: string;
  };
  identity_note?: string;
  raw?: ExecutionIdentityView;
};

export function buildIdentityBundle(contract: SpineFrontContractV1): ExecutionIdentityBundle | null {
  const raw = contract.meta.identity;
  if (!raw?.identity) return null;

  const drift = contract.meta.drift_summary;
  const epistemic = contract.explanation.explain_v3?.epistemic_score;
  const stability = computeStability(drift, epistemic);

  const sig = raw.signatures ?? {};
  return {
    id: raw.identity,
    stability,
    drift: Boolean(raw.identity_drift || raw.identity_mismatch || drift?.identity_drift),
    equivalent_traces: raw.equivalent_traces ?? [],
    drift_variants: raw.drift_variants ?? [],
    signatures: {
      graph: sig.graph ?? "—",
      state: sig.state ?? "—",
      control: sig.control ?? "—",
      causal: sig.causal ?? "—",
    },
    identity_note: contract.explanation.explain_v3?.identity_note as string | undefined,
    raw,
  };
}

function computeStability(
  drift: DriftSummaryView | undefined,
  epistemic: number | undefined,
): number {
  const driftScore = drift?.score ?? 1;
  const ep = epistemic ?? driftScore;
  return Math.round(Math.min(1, driftScore * ep) * 100) / 100;
}
