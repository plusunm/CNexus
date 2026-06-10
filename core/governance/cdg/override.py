"""Reality Override Engine — cognitive hard-brake surgery."""

from __future__ import annotations

import copy
import logging
from typing import Any, Dict, List

from core.governance.cdg.reality_bus import RealityFrame

logger = logging.getLogger("G1.CDG.Hypervisor")


class RealityOverrideEngine:
    """Prune ungrounded cognition when reality coupling fails."""

    def execute(self, state: Dict[str, Any], reality: List[RealityFrame]) -> Dict[str, Any]:
        logger.critical("REALITY OVERRIDE EXECUTED — cognitive surgery started")
        safe = copy.deepcopy(state)
        valid_ids = {f.event_id for f in reality}

        safe["memory"] = [
            m
            for m in safe.get("memory", [])
            if m.get("causal_parent") in valid_ids or not m.get("is_synthetic")
        ]

        safe["narrative"] = [
            n
            for n in safe.get("narrative", [])
            if n.get("grounding_ref") in valid_ids or not n.get("is_synthetic", True)
        ]

        for belief in safe.get("beliefs", []):
            prov = belief.get("provenance")
            if belief.get("confidence", 0) > 0.7 and prov and prov not in valid_ids:
                belief["confidence"] = float(belief["confidence"]) * 0.25
                belief["status"] = "downgraded_by_reality"

        flags = list(safe.get("flags", []))
        if "REALITY_OVERRIDE_APPLIED" not in flags:
            flags.append("REALITY_OVERRIDE_APPLIED")
        safe["flags"] = flags
        safe["plasticity_modifier"] = float(safe.get("plasticity_modifier", 1.0)) * 1.8
        return safe
