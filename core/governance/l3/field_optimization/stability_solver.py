"""L3-G3 — stability landscape solver over power field."""

from __future__ import annotations

import math

from core.governance.l3.field_optimization.types import PowerField, StabilityLandscape


class StabilitySolver:
    """Compute stability landscape metrics (observational / structural only)."""

    def analyze(self, field: PowerField) -> StabilityLandscape:
        if not field.nodes:
            return StabilityLandscape(
                entropy=0.0,
                lock_in_regions=0.0,
                diffusion_regions=1.0,
                bifurcation_points=0,
            )

        total_tension = sum(e.tension for e in field.edges)
        avg_elasticity = sum(n.elasticity for n in field.nodes.values()) / len(field.nodes)

        entropy = total_tension / (avg_elasticity + 1e-6)

        lock_in = sum(1 for n in field.nodes.values() if n.strength > 0.8) / len(field.nodes)
        diffusion = 1.0 - lock_in
        bifurcation = int(math.log1p(total_tension * 10))

        return StabilityLandscape(
            entropy=round(entropy, 4),
            lock_in_regions=round(lock_in, 4),
            diffusion_regions=round(diffusion, 4),
            bifurcation_points=bifurcation,
        )
