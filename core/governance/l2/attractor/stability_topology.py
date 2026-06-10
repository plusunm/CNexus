"""
GTBS-L2.5 — stability topology signature from latent attractor field.
"""

from __future__ import annotations

from core.governance.l2.attractor.types import AttractorField, TopologySignature


def compute_topology(field: AttractorField, *, strength_threshold: float = 0.35) -> TopologySignature:
    """Derive cluster topology and lock-in probability (observational only)."""
    if not field.attractors:
        return TopologySignature(
            cluster_count=0,
            dominant_attractor="",
            entropy_gradient=0.0,
            lock_in_probability=0.0,
        )

    strong = [a for a in field.attractors if a.strength >= strength_threshold]
    cluster_count = max(1, len(strong))
    dominant = max(field.attractors, key=lambda a: a.strength)
    max_strength = dominant.strength

    entropy_gradient = round(field.global_entropy * field.coupling_density, 4)
    lock_in = min(
        1.0,
        field.coupling_density * max_strength * (1.0 - field.global_entropy * 0.5),
    )

    collapsing = sum(1 for a in field.attractors if a.stability_class == "collapsing")
    if collapsing >= 2:
        lock_in = min(1.0, lock_in + 0.1)

    return TopologySignature(
        cluster_count=cluster_count,
        dominant_attractor=dominant.attractor_id,
        entropy_gradient=entropy_gradient,
        lock_in_probability=round(lock_in, 4),
    )
