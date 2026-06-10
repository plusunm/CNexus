"""Reality Bus — backward-compatible facade over RealityManifold."""

from core.governance.cdg.reality_manifold import RealityFrame, RealityManifold

RealityBus = RealityManifold

__all__ = ["RealityBus", "RealityFrame", "RealityManifold"]
