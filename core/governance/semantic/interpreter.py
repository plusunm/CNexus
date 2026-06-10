"""Re-export — canonical implementation in core.governance.l2."""

from core.governance.semantic.compat import (
    SemanticAlignmentInterpreter,
    build_semantic_snapshot,
)

__all__ = ["SemanticAlignmentInterpreter", "build_semantic_snapshot"]
