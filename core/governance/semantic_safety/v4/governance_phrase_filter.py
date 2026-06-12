"""Semantic Safety v4 — governance-like phrase detection (scan only)."""

from __future__ import annotations

GOVERNANCE_TRIGGERS: tuple[str, ...] = (
    "should enforce",
    "must optimize",
    "policy decision",
    "system chooses",
    "recommended action",
    "apply correction",
    "trigger mitigation",
    "must control",
    "shall execute",
    "governance decision",
)


class GovernancePhraseFilter:
    """Detect governance-shaped language in text fields."""

    def scan(self, text: str) -> list[str]:
        lowered = text.lower()
        return [phrase for phrase in GOVERNANCE_TRIGGERS if phrase in lowered]

    def scan_tree(self, node: object) -> list[str]:
        hits: list[str] = []
        if isinstance(node, str):
            hits.extend(self.scan(node))
        elif isinstance(node, dict):
            for value in node.values():
                hits.extend(self.scan_tree(value))
        elif isinstance(node, list):
            for item in node:
                hits.extend(self.scan_tree(item))
        return sorted(set(hits))
