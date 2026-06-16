"""Runtime config bootstrap — compute-aware policy application."""

from __future__ import annotations

from typing import Any, Dict, Tuple

from core.compute_policy import ComputePolicy, apply_compute_aware_config
from core.compute_profile import ComputeProfile


def apply_runtime_profile(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Apply compute-aware runtime policy. Returns merged config."""
    merged, _, _ = apply_compute_aware_config(cfg)
    return merged


def apply_runtime_profile_with_meta(
    cfg: Dict[str, Any],
) -> Tuple[Dict[str, Any], ComputeProfile, ComputePolicy]:
    return apply_compute_aware_config(cfg)
