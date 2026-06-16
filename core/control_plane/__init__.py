"""CNexus control plane — Phase 0 dispatch + Phase 1 decision overlay."""



from core.control_plane.audit import audit_decision

from core.control_plane.decision_engine import Decision, DecisionEngine, DecisionType

from core.control_plane.dispatch import AuthorityDispatcher

from core.control_plane.exceptions import ControlDecisionRejected

from core.control_plane.legacy_adapter import (
    LEGACY_CALLER,
    LEGACY_CHANNEL,
    LEGACY_OPENAI_CHANNEL,
    LEGACY_V1_CHANNEL,
    LegacyDispatchAdapter,
)

from core.control_plane.guards import dispatch_context, is_dispatch_active

from core.control_plane.registry import enforce_route_entry, resolve_registry_entry

from core.control_plane.types import DispatchContext, RouteKind, build_dispatch_context



__all__ = [

    "AuthorityDispatcher",

    "LegacyDispatchAdapter",
    "LEGACY_CALLER",
    "LEGACY_CHANNEL",
    "LEGACY_V1_CHANNEL",
    "LEGACY_OPENAI_CHANNEL",

    "ControlDecisionRejected",

    "Decision",

    "DecisionEngine",

    "DecisionType",

    "DispatchContext",

    "RouteKind",

    "audit_decision",

    "build_dispatch_context",

    "dispatch_context",

    "enforce_route_entry",

    "is_dispatch_active",

    "resolve_registry_entry",

]


