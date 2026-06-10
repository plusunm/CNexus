"""CDG — advisory epistemic governance control plane (MSEGS v1.0)."""

from core.governance.cdg.audit_logger import GovernanceAuditLogger
from core.governance.cdg.cdg_kernel import CDGConfig, CDGKernel, GovernanceDecision, GovernanceParamSuggestion
from core.governance.cdg.epistemic_view import EpistemicView
from core.governance.cdg.control_types import ControlSignal, ControlStepResult, EnergyGradient
from core.governance.cdg.gradient_controller import EnergyGradientController
from core.governance.cdg.graph_fingerprint import graph_fingerprint
from core.governance.cdg.invariant_reference import InvariantReferenceManifold, ReferencePoint
from core.governance.cdg.lyapunov_monitor import DescentMonitor, DescentSnapshot, LyapunovMonitor, LyapunovSnapshot
from core.governance.cdg.lyapunov_verifier import (
    LyapunovVerifier,
    ReferenceDeviationVerifier,
    VerificationSnapshot,
)
from core.governance.cdg.os_projection import frames_from_os_events, ingest_os_projection
from core.governance.cdg.reality_bus import RealityBus, RealityFrame, RealityManifold
from core.governance.cdg.stability_energy import (
    EnergySnapshot,
    EnergyStepResult,
    OscillationSpectrum,
    OscillationSpectrumModel,
    StabilityEnergyLayer,
    oscillation_potential,
)
from core.governance.cdg.state_adapter import apply_cdg_state, empty_cdg_state, snapshot_cdg_state
from core.governance.cdg.types import (
    AttractorState,
    CDGInteraction,
    CDGCycleRecord,
    DriftSnapshot,
    GovernanceVerdict,
)

__all__ = [
    "AttractorState",
    "CDGCycleRecord",
    "CDGConfig",
    "CDGInteraction",
    "CDGKernel",
    "ControlSignal",
    "ControlStepResult",
    "DriftSnapshot",
    "EnergyGradient",
    "EnergyGradientController",
    "EnergySnapshot",
    "EnergyStepResult",
    "GovernanceAuditLogger",
    "GovernanceDecision",
    "GovernanceVerdict",
    "graph_fingerprint",
    "InvariantReferenceManifold",
    "DescentMonitor",
    "DescentSnapshot",
    "EpistemicView",
    "GovernanceParamSuggestion",
    "LyapunovMonitor",
    "LyapunovSnapshot",
    "LyapunovVerifier",
    "ReferenceDeviationVerifier",
    "OscillationSpectrum",
    "OscillationSpectrumModel",
    "RealityBus",
    "RealityFrame",
    "RealityManifold",
    "ReferencePoint",
    "StabilityEnergyLayer",
    "VerificationSnapshot",
    "apply_cdg_state",
    "empty_cdg_state",
    "frames_from_os_events",
    "ingest_os_projection",
    "oscillation_potential",
    "snapshot_cdg_state",
]
