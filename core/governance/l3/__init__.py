"""L3 — Cognitive Governance Boundary Layer (G0 probe + G1 constraint geometry)."""

from __future__ import annotations

from typing import Any

from core.governance.l3.arbitration_engine import ArbitrationDecision, ArbitrationSimulator
from core.governance.l3.arbitration_engine import ArbitrationEngine  # deprecated v1 alias
from core.governance.l3.authority_router import AuthorityRouter
from core.governance.l3.boundary_registry import BoundaryRegistry, default_registry
from core.governance.l3.constraint_graph import ConstraintGraphBuilder
from core.governance.l3.constraint_model import ConstraintGraph
from core.governance.l3.l3g1_report import L3G1Report, L3G1Reporter
from core.governance.l3.leakage_probe import LeakageProbe
from core.governance.l3.report import L3G0Report
from core.governance.l3.types import AuthorityLevel, Boundary, L3G0ReportPayload, RoutingDecision
from core.governance.l3.execution_shadow import (
    L3G2Report,
    build_execution_scenarios,
    derive_system_state,
)
from core.governance.l3.execution_shadow.l3g2_report import L3G2Reporter
from core.governance.l3.execution_shadow.shadow_engine import ConstraintExecutionShadowEngine
from core.governance.l3.field_optimization import (
    AttractorMap,
    FieldOptimizationSimulator,
    L3G3Report,
    PowerFieldBuilder,
    StabilitySolver,
)
from core.governance.l3.field_optimization.l3g3_report import L3G3Reporter
from core.governance.l3.meta import (
    DriftAnalyzer,
    L3G4Report,
    ObserverModel,
    ReflexivityEngine,
    SelfModelExtractor,
    StructuralModelExtractor,
)
from core.governance.l3.meta.l3g4_report import L3G4Reporter
from core.governance.l3.meta_meta import L3G5Report
from core.governance.l3.meta_meta.l3g5_report import L3G5Reporter
from core.governance.l3.collapse_stability import L3G6Report
from core.governance.l3.collapse_stability import build_l3_g6_report as assemble_l3_g6_report
from core.governance.l3.collapse_stability import derive_collapse_system_state
from core.governance.l3.g7 import L3G7Report
from core.governance.l3.g7 import build_l3_g7_report as assemble_l3_g7_report
from core.governance.l3.g7 import derive_l3_bundle_from_stack
from core.governance.l3.violation_scorer import ViolationScorer

__all__ = [
    "ArbitrationDecision",
    "ArbitrationSimulator",
    "ArbitrationEngine",
    "AuthorityLevel",
    "AuthorityRouter",
    "Boundary",
    "BoundaryRegistry",
    "ConstraintGraph",
    "ConstraintGraphBuilder",
    "L3G0Report",
    "L3G0ReportPayload",
    "L3G1Report",
    "L3G1Reporter",
    "L3G2Report",
    "L3G3Report",
    "L3G4Report",
    "L3G5Report",
    "L3G6Report",
    "L3G7Report",
    "LeakageProbe",
    "RoutingDecision",
    "ViolationScorer",
    "build_l3_g0_report",
    "build_l3_g1_report",
    "build_l3_g2_report",
    "build_l3_g3_report",
    "build_l3_g4_report",
    "build_l3_g5_report",
    "build_l3_g6_report",
    "build_l3_g7_report",
    "default_registry",
    "primary_l3_signal_from_probe",
    "signals_from_l2_stack",
]


def signals_from_l2_stack(base_dir: str, window_days: int = 7) -> list[dict]:
    """
    L2→L3 coupling harness: derive probe signals from live L2 stack outputs.
    All signals remain observational / interpretive — never governance.
    """
    from core.governance.l2.attractor import build_attractor_inference_report
    from core.governance.l2.fusion import build_fusion_report

    signals: list[dict] = []
    fusion = build_fusion_report(base_dir, window_days=window_days)
    signals.append(
        {
            "source": "l2_fusion",
            "type": "interpretation",
            "payload": {"coupling_matrix": fusion.coupling_matrix},
        }
    )
    for key in ("drift_convergence", "coupled_stability", "meta_consistency"):
        signals.append(
            {
                "source": "l2_fusion",
                "type": "interpretation",
                "payload": {"narrative": fusion.fusion_summaries.get(key, "")},
            }
        )

    attractor = build_attractor_inference_report(base_dir, window_days=window_days)
    signals.append(
        {
            "source": "l2_attractor",
            "type": "interpretation",
            "payload": {"field_regime": attractor.field_regime},
        }
    )
    signals.append(
        {
            "source": "l2_attractor",
            "type": "observation",
            "payload": {"dominant_attractors": attractor.dominant_attractors},
        }
    )

    lock_in = float(attractor.risk_surface.get("lock_in_risk", 0.0))
    if lock_in >= 0.5:
        signals.append(
            {
                "source": "l2_attractor",
                "type": "governance_attempt",
                "target": "runtime",
                "confidence": lock_in,
                "payload": {"hint": "elevated lock-in — would-be steer signal (blocked)"},
            }
        )

    signals.append(
        {
            "source": "phase_c",
            "type": "observation",
            "payload": {"stream": "ecology_metrics.jsonl"},
        }
    )
    return signals


def build_l3_g0_report(
    base_dir: str | None = None,
    *,
    window_days: int = 7,
    use_l2_coupling: bool = True,
) -> L3G0Report:
    """End-to-end L3-G0 probe: registry + router + leakage probe + report."""
    registry = default_registry()
    router = AuthorityRouter()
    probe = LeakageProbe(router)

    if use_l2_coupling and base_dir:
        test_signals = signals_from_l2_stack(base_dir, window_days=window_days)
    else:
        test_signals = [
            {"source": "l2_fusion", "type": "interpretation", "payload": {}},
            {"source": "phase_c", "type": "observation", "payload": {}},
            {
                "source": "l2_fusion",
                "type": "governance_attempt",
                "target": "runtime",
                "confidence": 0.85,
                "payload": {},
            },
        ]

    for sig in test_signals:
        probe.record(sig)

    return L3G0Report(probe.summary(), registry=registry, probe=probe)


def primary_l3_signal_from_probe(probe: LeakageProbe) -> dict[str, Any]:
    """Pick highest-severity signal for G1 arbitration simulation."""
    g0_summary = probe.summary()
    best: dict[str, Any] | None = None
    best_priority = -1

    priority = {
        AuthorityLevel.GOVERNANCE_ATTEMPT: 3,
        AuthorityLevel.INTERPRETATION: 2,
        AuthorityLevel.OBSERVATION: 1,
    }

    for event in probe.events:
        sig = dict(event["signal"])
        sig["g0_summary"] = g0_summary
        level = event["level"]
        p = priority.get(level, 0)
        if level == AuthorityLevel.GOVERNANCE_ATTEMPT and not sig.get("target"):
            sig["target"] = "runtime"
        if p > best_priority:
            best_priority = p
            best = sig

    if best is None:
        return {"type": "observation", "source": "none", "g0_summary": g0_summary}
    return best


def build_l3_g1_report(
    l3_signals: dict[str, Any] | None = None,
    *,
    base_dir: str | None = None,
    window_days: int = 7,
    use_l2_coupling: bool = True,
) -> L3G1Report:
    """
    L3-G1 pipeline: graph → score → simulate arbitration → report only.
    """
    if l3_signals is None:
        g0 = build_l3_g0_report(
            base_dir,
            window_days=window_days,
            use_l2_coupling=use_l2_coupling and base_dir is not None,
        )
        if g0.probe is None:
            raise RuntimeError("L3-G0 report missing probe for G1 pipeline")
        l3_signals = primary_l3_signal_from_probe(g0.probe)

    scorer = ViolationScorer()
    score = scorer.score(l3_signals)
    l3_signals = {**l3_signals, "intensity": score, "violation_score": score}

    builder = ConstraintGraphBuilder()
    graph = builder.build_from_l3_signals(l3_signals)

    engine = ArbitrationSimulator()
    decision = engine.simulate(graph, l3_signals)

    return L3G1Reporter().render(graph, decision, score)


def build_l3_g2_report(
    l3_signals: dict[str, Any] | None = None,
    *,
    base_dir: str | None = None,
    window_days: int = 7,
    use_l2_coupling: bool = True,
) -> L3G2Report:
    """
    L3-G2 pipeline: scenarios → shadow simulate → impact report only.
    Chains G0/G1 for signal + violation score when base_dir provided.
    """
    g1_report = build_l3_g1_report(
        l3_signals,
        base_dir=base_dir,
        window_days=window_days,
        use_l2_coupling=use_l2_coupling and base_dir is not None,
    )

    if l3_signals is None:
        g0 = build_l3_g0_report(
            base_dir,
            window_days=window_days,
            use_l2_coupling=use_l2_coupling and base_dir is not None,
        )
        if g0.probe is None:
            raise RuntimeError("L3-G0 report missing probe for G2 pipeline")
        l3_signals = primary_l3_signal_from_probe(g0.probe)
    l3_signals = {**l3_signals, "violation_score": g1_report.violation_score}

    system_state = derive_system_state(
        base_dir=base_dir,
        window_days=window_days,
        l3_signals=l3_signals,
        g1_violation_score=g1_report.violation_score,
    )

    scenarios = build_execution_scenarios(l3_signals, g1_violation_score=g1_report.violation_score)
    engine = ConstraintExecutionShadowEngine()
    shadow_states = [engine.simulate(s, system_state) for s in scenarios]

    return L3G2Reporter().render(shadow_states, baseline_state=system_state)


def _resolve_l3_signals_for_pipeline(
    l3_signals: dict[str, Any] | None,
    *,
    base_dir: str | None,
    window_days: int,
    use_l2_coupling: bool,
) -> dict[str, Any]:
    if l3_signals is not None:
        return l3_signals
    g0 = build_l3_g0_report(
        base_dir,
        window_days=window_days,
        use_l2_coupling=use_l2_coupling and base_dir is not None,
    )
    if g0.probe is None:
        raise RuntimeError("L3-G0 report missing probe for G2/G3 pipeline")
    return primary_l3_signal_from_probe(g0.probe)


def build_l3_g3_report(
    l3_signals: dict[str, Any] | None = None,
    *,
    base_dir: str | None = None,
    window_days: int = 7,
    use_l2_coupling: bool = True,
) -> L3G3Report:
    """
    L3-G3 pipeline: G1 graph + G2 shadows → power field → stability → optimize (shadow only).
    """
    coupling = use_l2_coupling and base_dir is not None
    signals = _resolve_l3_signals_for_pipeline(
        l3_signals, base_dir=base_dir, window_days=window_days, use_l2_coupling=coupling
    )

    scorer = ViolationScorer()
    score = scorer.score(signals)
    signals = {**signals, "intensity": score, "violation_score": score}

    g1_graph = ConstraintGraphBuilder().build_from_l3_signals(signals)

    system_state = derive_system_state(
        base_dir=base_dir,
        window_days=window_days,
        l3_signals=signals,
        g1_violation_score=score,
    )
    scenarios = build_execution_scenarios(signals, g1_violation_score=score)
    shadow_engine = ConstraintExecutionShadowEngine()
    shadow_states = [shadow_engine.simulate(s, system_state) for s in scenarios]

    power_field = PowerFieldBuilder().build(g1_graph, shadow_states)
    landscape = StabilitySolver().analyze(power_field)
    attractors = AttractorMap().compute(power_field)
    optimization = FieldOptimizationSimulator().simulate(power_field, landscape)

    return L3G3Reporter().render(
        landscape,
        attractors,
        optimization,
        power_field=power_field,
    )


def build_l3_g4_report(
    l3_signals: dict[str, Any] | None = None,
    *,
    base_dir: str | None = None,
    window_days: int = 7,
    use_l2_coupling: bool = True,
) -> L3G4Report:
    """
    L3-G4 pipeline: G0–G3 stack → self-model vs structural model → reflexivity → meta-drift report.
    """
    coupling = use_l2_coupling and base_dir is not None

    g0_report = build_l3_g0_report(
        base_dir if coupling else None,
        window_days=window_days,
        use_l2_coupling=coupling,
    )
    g1_report = build_l3_g1_report(
        l3_signals,
        base_dir=base_dir if coupling else None,
        window_days=window_days,
        use_l2_coupling=coupling,
    )
    g2_report = build_l3_g2_report(
        l3_signals,
        base_dir=base_dir if coupling else None,
        window_days=window_days,
        use_l2_coupling=coupling,
    )
    g3_report = build_l3_g3_report(
        l3_signals,
        base_dir=base_dir if coupling else None,
        window_days=window_days,
        use_l2_coupling=coupling,
    )

    stack = {
        "g0": g0_report.render(),
        "g1": g1_report.to_dict(),
        "g2": g2_report.to_dict(),
        "g3": g3_report.to_dict(),
    }

    self_ext = SelfModelExtractor()
    struct_ext = StructuralModelExtractor()
    self_model = self_ext.extract(stack)
    structural = struct_ext.extract(stack)
    gap = struct_ext.gap(self_model, structural)

    observer = ObserverModel().build(self_model, structural, stack)
    reflexivity = ReflexivityEngine().compute(self_model, structural, observer, gap)
    meta_state = DriftAnalyzer().analyze(reflexivity, self_model, structural, observer, gap)

    return L3G4Reporter().render(meta_state, reflexivity, observer)


def build_l3_g5_report(
    l3_signals: dict[str, Any] | None = None,
    *,
    base_dir: str | None = None,
    window_days: int = 7,
    use_l2_coupling: bool = True,
) -> L3G5Report:
    """
    L3-G5 pipeline: G4 reflexivity state → layer genesis → boundaries → ontology drift → meta-meta report.
    """
    g4_report = build_l3_g4_report(
        l3_signals,
        base_dir=base_dir,
        window_days=window_days,
        use_l2_coupling=use_l2_coupling,
    )
    return L3G5Reporter().build_report(g4_report.to_dict())


def build_l3_g6_report(
    l3_signals: dict[str, Any] | None = None,
    *,
    base_dir: str | None = None,
    window_days: int = 7,
    use_l2_coupling: bool = True,
) -> L3G6Report:
    """
    L3-G6 pipeline: G5 meta-meta state + G4 reflexivity → collapse detection → explainability anchors.
    """
    g4_report = build_l3_g4_report(
        l3_signals,
        base_dir=base_dir,
        window_days=window_days,
        use_l2_coupling=use_l2_coupling,
    )
    g5_report = build_l3_g5_report(
        l3_signals,
        base_dir=base_dir,
        window_days=window_days,
        use_l2_coupling=use_l2_coupling,
    )
    g5_payload = g5_report.to_dict()
    g4_payload = g4_report.to_dict()
    system_state = derive_collapse_system_state(g4_payload, g5_payload)
    return assemble_l3_g6_report(g5_payload, system_state)


def build_l3_g7_report(
    l3_signals: dict[str, Any] | None = None,
    *,
    base_dir: str | None = None,
    window_days: int = 7,
    use_l2_coupling: bool = True,
) -> L3G7Report:
    """
    L3-G7 pipeline: collapse G0–G6 stack into field/attractor/trace — no layer ontology.
    """
    g0_report = build_l3_g0_report(
        base_dir if use_l2_coupling and base_dir else None,
        window_days=window_days,
        use_l2_coupling=use_l2_coupling and base_dir is not None,
    )
    g3_report = build_l3_g3_report(
        l3_signals,
        base_dir=base_dir,
        window_days=window_days,
        use_l2_coupling=use_l2_coupling,
    )
    g4_report = build_l3_g4_report(
        l3_signals,
        base_dir=base_dir,
        window_days=window_days,
        use_l2_coupling=use_l2_coupling,
    )
    g5_report = build_l3_g5_report(
        l3_signals,
        base_dir=base_dir,
        window_days=window_days,
        use_l2_coupling=use_l2_coupling,
    )
    g6_report = build_l3_g6_report(
        l3_signals,
        base_dir=base_dir,
        window_days=window_days,
        use_l2_coupling=use_l2_coupling,
    )

    g0_payload = g0_report.render() if hasattr(g0_report, "render") else g0_report.to_dict()
    bundle = derive_l3_bundle_from_stack(
        g0=g0_payload,
        g3=g3_report.to_dict(),
        g4=g4_report.to_dict(),
        g5=g5_report.to_dict(),
        g6=g6_report.to_dict(),
    )
    return assemble_l3_g7_report(bundle)
