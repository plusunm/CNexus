"""
Phase A — Frozen Episodic Anchor registry (append-only observability).

High reality-impact events are recorded as immutable anchors.
Does NOT mutate runtime memory or block writes (Constitutional A2/A5).
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class FrozenEpisodicAnchor:
    """Immutable anchor record — append interpretation only, never rewrite truth."""

    anchor_id: str
    event_ref: str
    content_preview: str
    reality_impact_score: float
    source: str
    ts: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "anchor_id": self.anchor_id,
            "event_ref": self.event_ref,
            "content_preview": self.content_preview,
            "reality_impact_score": round(self.reality_impact_score, 4),
            "source": self.source,
            "ts": self.ts,
            "metadata": self.metadata,
            "immutable": True,
            "rewrite_forbidden": True,
        }


class FrozenEpisodicAnchorRegistry:
    """
    Append-only anchor log under observability/frozen_anchors.jsonl.

    Observer-only: records high-impact grounding events for reconstruction audit.
    """

    REALITY_IMPACT_THRESHOLD = 0.72

    def __init__(self, base_dir: str | Path) -> None:
        root = Path(base_dir)
        self._dir = root / "observability"
        self._path = self._dir / "frozen_anchors.jsonl"

    @property
    def path(self) -> Path:
        return self._path

    def read_all(self) -> list[dict[str, Any]]:
        if not self._path.exists():
            return []
        rows: list[dict[str, Any]] = []
        with open(self._path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
        return rows

    def record(self, anchor: FrozenEpisodicAnchor) -> Path:
        self._dir.mkdir(parents=True, exist_ok=True)
        with open(self._path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(anchor.to_dict(), ensure_ascii=False) + "\n")
        return self._path

    def assess_shadow_observation(self, row: dict[str, Any]) -> Optional[FrozenEpisodicAnchor]:
        """Build anchor candidate without persisting."""
        context = row.get("context") or {}
        proposal = row.get("proposal") or {}
        score = self._reality_impact_score(context, proposal, row)
        if score < self.REALITY_IMPACT_THRESHOLD:
            return None

        event_ref = (
            context.get("grounding_event_id")
            or context.get("capture_id")
            or context.get("memory_id")
            or f"shadow-{row.get('timestamp', 'unknown')}"
        )
        preview = str(proposal.get("content_preview") or context.get("layer") or "episodic event")[:120]

        return FrozenEpisodicAnchor(
            anchor_id=f"anchor-{uuid.uuid4().hex[:12]}",
            event_ref=str(event_ref),
            content_preview=preview,
            reality_impact_score=score,
            source=str(proposal.get("source") or context.get("phase") or "shadow"),
            metadata={
                "phase": context.get("phase"),
                "declared_stores": proposal.get("target_stores"),
                "observation_ts": row.get("timestamp"),
            },
        )

    def evaluate_shadow_observation(self, row: dict[str, Any]) -> Optional[FrozenEpisodicAnchor]:
        anchor = self.assess_shadow_observation(row)
        if anchor:
            self.record(anchor)
        return anchor

    @staticmethod
    def _reality_impact_score(
        context: dict[str, Any],
        proposal: dict[str, Any],
        row: dict[str, Any],
    ) -> float:
        score = 0.0
        if context.get("grounding_event_id"):
            score += 0.35
        if context.get("phase") == "interaction":
            score += 0.25
        if context.get("layer") in ("goal", "identity", "belief"):
            score += 0.2
        if "reality" in (proposal.get("target_stores") or []):
            score += 0.15
        pvr = row.get("proposal_vs_reality") or {}
        if pvr.get("cross_store_consistency") is not None:
            score += float(pvr["cross_store_consistency"]) * 0.15
        return min(score, 1.0)

    def scan_and_record(self, shadow_rows: List[dict[str, Any]]) -> List[FrozenEpisodicAnchor]:
        """Scan shadow stream and append anchors for qualifying events."""
        existing_refs = {r.get("event_ref") for r in self.read_all()}
        recorded: list[FrozenEpisodicAnchor] = []
        for row in shadow_rows:
            anchor = self.assess_shadow_observation(row)
            if anchor and anchor.event_ref not in existing_refs:
                self.record(anchor)
                existing_refs.add(anchor.event_ref)
                recorded.append(anchor)
        return recorded
