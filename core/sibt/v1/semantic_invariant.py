"""SIBT v1 — semantic invariant layer (Layer 0, single source of truth)."""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

SemanticLayer = Dict[str, Any]

_ENTITY_HINTS = {
    "runtime": "system_component",
    "scheduler": "system_component",
    "ui": "interface",
    "memory": "system_component",
    "llm": "system_component",
    "cluster": "system_component",
    "prompt": "concept",
    "intent": "concept",
    "translation": "process",
    "翻译": "process",
    "界面": "interface",
    "运行时": "system_component",
    "调度器": "system_component",
}

_RELATION_PATTERNS = [
    (re.compile(r"(\w+)\s+depends?\s+on\s+(\w+)", re.I), "depends_on"),
    (re.compile(r"(\w+)\s+requires?\s+(\w+)", re.I), "requires"),
    (re.compile(r"(\S+)\s*依赖\s*(\S+)"), "depends_on"),
    (re.compile(r"(\S+)\s*→\s*(\S+)"), "flows_to"),
]

_CONSTRAINT_PATTERNS = [
    (re.compile(r"no\s+(\w[\w\s-]*)", re.I), "no {0}"),
    (re.compile(r"low\s+latency", re.I), "low latency"),
    (re.compile(r"不允许\s*([^，。；]+)"), "no {0}"),
    (re.compile(r"低延迟"), "low latency"),
    (re.compile(r"语义漂移"), "no semantic drift"),
    (re.compile(r"semantic\s+drift", re.I), "no semantic drift"),
]

_INTENT_HINTS = {
    "need": "improvement_goal",
    "improve": "improvement_goal",
    "fix": "remediation_goal",
    "optimize": "optimization_goal",
    "需要": "improvement_goal",
    "优化": "optimization_goal",
    "改进": "improvement_goal",
    "问题": "issue_report",
    "issue": "issue_report",
    "goal": "system_or_user_goal",
    "目标": "system_or_user_goal",
}


@dataclass
class SemanticInvariant:
    intent: str
    entities: List[Dict[str, str]] = field(default_factory=list)
    relations: List[Dict[str, str]] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    meaning_atoms: List[str] = field(default_factory=list)
    source_lang: str = "auto"

    def to_layer(self) -> SemanticLayer:
        return {
            "intent": self.intent,
            "entities": list(self.entities),
            "relations": list(self.relations),
            "constraints": list(self.constraints),
            "meaning_atoms": list(self.meaning_atoms),
        }

    def invariant_id(self) -> str:
        payload = json.dumps(self.to_layer(), sort_keys=True, ensure_ascii=False)
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]
        return f"SIV-{digest}"

    def atom_fingerprint(self) -> frozenset[str]:
        return frozenset(_normalize_atom(a) for a in self.meaning_atoms if _normalize_atom(a))


def _normalize_atom(atom: str) -> str:
    return re.sub(r"\s+", " ", atom.strip().lower())


def detect_language(text: str) -> str:
    if not text.strip():
        return "en"
    cjk = len(re.findall(r"[\u4e00-\u9fff]", text))
    latin = len(re.findall(r"[A-Za-z]", text))
    return "zh" if cjk >= latin else "en"


def _split_atoms(text: str) -> List[str]:
    chunks = re.split(r"[。；;!\n]+|(?<=[.!?])\s+", text.strip())
    atoms: List[str] = []
    for chunk in chunks:
        part = chunk.strip(" ,·-—")
        if len(part) >= 2:
            atoms.append(part)
    if not atoms and text.strip():
        atoms.append(text.strip())
    return atoms


def _extract_entities(text: str, atoms: List[str]) -> List[Dict[str, str]]:
    found: Dict[str, str] = {}
    corpus = " ".join(atoms).lower()
    for name, etype in _ENTITY_HINTS.items():
        if name.lower() in corpus or name in text:
            key = name.lower() if name.isascii() else name
            found[key] = etype
    for token in re.findall(r"\b[A-Za-z][A-Za-z0-9_]{2,}\b", text):
        low = token.lower()
        if low not in found:
            found[low] = "entity"
    return [{"name": k, "type": v} for k, v in sorted(found.items())]


def _extract_relations(text: str) -> List[Dict[str, str]]:
    relations: List[Dict[str, str]] = []
    for pattern, rtype in _RELATION_PATTERNS:
        for match in pattern.finditer(text):
            src, dst = match.group(1).strip(), match.group(2).strip()
            if src and dst:
                relations.append({"from": src.lower(), "to": dst.lower(), "type": rtype})
    return relations


def _extract_constraints(text: str) -> List[str]:
    constraints: List[str] = []
    for pattern, template in _CONSTRAINT_PATTERNS:
        for match in pattern.finditer(text):
            if "{" in template:
                constraints.append(template.format(match.group(1).strip()))
            else:
                constraints.append(template)
    return sorted(set(constraints))


def _infer_intent(text: str, atoms: List[str]) -> str:
    corpus = (text + " " + " ".join(atoms)).lower()
    for hint, intent in _INTENT_HINTS.items():
        if hint in corpus:
            return intent
    return "system_or_user_goal"


def parse_to_semantic_invariant(text: str, *, source_lang: Optional[str] = None) -> SemanticInvariant:
    """Compress arbitrary language input into structured semantic invariant (Layer 0)."""
    raw = str(text or "").strip()
    lang = source_lang or detect_language(raw)
    atoms = _split_atoms(raw)
    return SemanticInvariant(
        intent=_infer_intent(raw, atoms),
        entities=_extract_entities(raw, atoms),
        relations=_extract_relations(raw),
        constraints=_extract_constraints(raw),
        meaning_atoms=atoms,
        source_lang=lang,
    )


def merge_invariants(a: SemanticInvariant, b: SemanticInvariant) -> SemanticInvariant:
    """Merge two invariants — union atoms/entities with structural preservation."""
    atoms = list(dict.fromkeys(a.meaning_atoms + b.meaning_atoms))
    entities = list({(e["name"], e["type"]): e for e in a.entities + b.entities}.values())
    relations = list(
        {(r["from"], r["to"], r["type"]): r for r in a.relations + b.relations}.values()
    )
    constraints = sorted(set(a.constraints + b.constraints))
    return SemanticInvariant(
        intent=a.intent if a.intent != "system_or_user_goal" else b.intent,
        entities=entities,
        relations=relations,
        constraints=constraints,
        meaning_atoms=atoms,
        source_lang=a.source_lang,
    )
