"""L3-G0 — read-only boundary registry (authority topology description)."""

from __future__ import annotations

from core.governance.l3.types import Boundary


class BoundaryRegistry:
    """只读边界注册表，描述系统权力边界（S15: 不执行约束）。"""

    def __init__(self) -> None:
        self._registry: dict[str, Boundary] = {}

    def register(self, boundary: Boundary) -> None:
        if boundary.name in self._registry:
            raise ValueError(f"Boundary {boundary.name} already exists")
        self._registry[boundary.name] = boundary

    def get(self, name: str) -> Boundary | None:
        return self._registry.get(name)

    def all_boundaries(self) -> list[Boundary]:
        return list(self._registry.values())


def default_registry() -> BoundaryRegistry:
    """Canonical L3-G0 boundaries (descriptive only)."""
    registry = BoundaryRegistry()
    registry.register(
        Boundary(
            name="replay_layer",
            scope="semantic",
            description="Replay / audit truth — IMMUTABLE",
            immutable=True,
        )
    )
    registry.register(
        Boundary(
            name="l2_output",
            scope="l2_fusion",
            description="L2 解释输出边界 — READ_ONLY / ADVISORY",
            immutable=True,
        )
    )
    registry.register(
        Boundary(
            name="attractor_state",
            scope="attractor",
            description="Latent attractor field — OBSERVABLE ONLY (S16)",
            immutable=True,
        )
    )
    registry.register(
        Boundary(
            name="runtime",
            scope="runtime",
            description="系统执行边界 — RESTRICTED (sole mutation authority)",
            immutable=True,
        )
    )
    return registry
