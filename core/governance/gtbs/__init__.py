"""GTBS — Governance Transaction Boundary (v1.0 schema + v1.1 shadow + v1.2 capture pilot)."""

from core.governance.gtbs.capture_boundary import (
    CaptureMutationBoundary,
    GTBS_CAPTURE_MODE,
    GTBS_CAPTURE_VERSION,
)
from core.governance.gtbs.adapters.capture_adapter import infer_capture_target_stores
from core.governance.gtbs.divergence_analysis import DivergenceAnalyzer, DivergenceLandscapeReport
from core.governance.gtbs.divergence_collector import (
    GTBSShadowDivergenceCollector,
    get_shadow_collector,
)
from core.governance.gtbs.gatekeeper import (
    GTBS_SHADOW_MODE,
    GTBS_SHADOW_VERSION,
    RuntimeGatekeeper,
)
from core.governance.gtbs.transaction_log import GTBSTransactionLog
from core.governance.gtbs.types import (
    GTBS_STATUS,
    GTBS_VERSION,
    AuditTransactionEvent,
    GovernanceProposal,
    GovernanceTransaction,
    JustificationSource,
    OperationType,
    StateDelta,
    TargetStore,
    TransactionState,
)
from core.governance.gtbs.write_intent import (
    GTBS_WRITE_INTENT_MODE,
    GTBS_WRITE_INTENT_VERSION,
    MutabilityLevel,
    WriteIntent,
    WriteIntentKind,
    WriteProvenance,
)
from core.governance.gtbs.write_intent_bus import (
    WriteIntentBus,
    build_current_provenance,
    shadow_emit_enabled,
    write_intent_provenance_scope,
)

__all__ = [
    "GTBS_CAPTURE_MODE",
    "GTBS_CAPTURE_VERSION",
    "GTBS_SHADOW_MODE",
    "GTBS_SHADOW_VERSION",
    "GTBS_STATUS",
    "GTBS_VERSION",
    "CaptureMutationBoundary",
    "DivergenceAnalyzer",
    "DivergenceLandscapeReport",
    "GTBSShadowDivergenceCollector",
    "GTBSTransactionLog",
    "RuntimeGatekeeper",
    "get_shadow_collector",
    "infer_capture_target_stores",
    "GTBS_WRITE_INTENT_MODE",
    "GTBS_WRITE_INTENT_VERSION",
    "WriteIntent",
    "WriteIntentBus",
    "WriteIntentKind",
    "WriteProvenance",
    "MutabilityLevel",
    "build_current_provenance",
    "shadow_emit_enabled",
    "write_intent_provenance_scope",
    "AuditTransactionEvent",
    "GovernanceProposal",
    "GovernanceTransaction",
    "JustificationSource",
    "OperationType",
    "StateDelta",
    "TargetStore",
    "TransactionState",
]
