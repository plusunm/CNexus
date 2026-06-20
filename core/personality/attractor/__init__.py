"""L3-2 Attractor — dynamic identity stabilization (Σ.S recalibration)."""

from core.personality.attractor.delta_constraint import clamp_scalar_step
from core.personality.attractor.recalibration_loop import (
    build_inner_monologue_prompt,
    parse_recalibration_response,
    propose_sigma_s_updates,
    run_attractor_recalibration,
)

__all__ = [
    "build_inner_monologue_prompt",
    "clamp_scalar_step",
    "parse_recalibration_response",
    "propose_sigma_s_updates",
    "run_attractor_recalibration",
]
