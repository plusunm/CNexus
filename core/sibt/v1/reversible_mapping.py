"""SIBT v1 — reversible mapping layer (Layer 2) + back-check engine."""

from __future__ import annotations

import difflib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.sibt.v1.language_projection import LanguageProjectorV1, get_language_projector
from core.sibt.v1.semantic_invariant import SemanticInvariant, parse_to_semantic_invariant

LossReport = Dict[str, Any]
SIBTResult = Dict[str, Any]


@dataclass
class ReversibleMapping:
    zh_sentence: str
    en_sentence: str
    maps_to: str
    loss_check: Dict[str, List[str]] = field(default_factory=dict)


def compare_atom_sets(source: SemanticInvariant, target: SemanticInvariant) -> Dict[str, List[str]]:
    src = source.atom_fingerprint()
    dst = target.atom_fingerprint()
    missing = sorted(src - dst)
    extra = sorted(dst - src)
    return {"missing_atoms": missing, "extra_atoms": extra}


def compare_structure(source: SemanticInvariant, target: SemanticInvariant) -> List[str]:
    distorted: List[str] = []
    src_rel = {(r["from"], r["to"], r["type"]) for r in source.relations}
    dst_rel = {(r["from"], r["to"], r["type"]) for r in target.relations}
    for rel in src_rel - dst_rel:
        distorted.append(f"missing_relation:{rel[0]}->{rel[1]}:{rel[2]}")
    for rel in dst_rel - src_rel:
        distorted.append(f"extra_relation:{rel[0]}->{rel[1]}:{rel[2]}")
    src_constraints = set(source.constraints)
    dst_constraints = set(target.constraints)
    for c in src_constraints - dst_constraints:
        distorted.append(f"missing_constraint:{c}")
    for c in dst_constraints - src_constraints:
        distorted.append(f"extra_constraint:{c}")
    return distorted


def faithfulness_score(source: SemanticInvariant, projected_text: str) -> float:
    reparsed = parse_to_semantic_invariant(projected_text)
    src_atoms = source.atom_fingerprint()
    dst_atoms = reparsed.atom_fingerprint()
    if not src_atoms and not dst_atoms:
        return 1.0
    union = src_atoms | dst_atoms
    if not union:
        return 1.0
    return len(src_atoms & dst_atoms) / len(union)


def text_similarity(a: str, b: str) -> float:
    if not a and not b:
        return 1.0
    return difflib.SequenceMatcher(None, a.strip(), b.strip()).ratio()


def naturalness_heuristic(text: str, lang: str) -> float:
    if not text.strip():
        return 0.0
    if lang == "zh":
        machine_markers = ["该系统", "请注意", "以下是", "翻译结果"]
        penalty = sum(1 for m in machine_markers if m in text)
        return max(0.0, 1.0 - penalty * 0.15)
    literal_markers = ["this is a", "please note", "translation:", "the following"]
    penalty = sum(1 for m in literal_markers if m.lower() in text.lower())
    return max(0.0, 1.0 - penalty * 0.15)


class BackCheckEngineV1:
    """Validate semantic / structural / round-trip consistency."""

    def __init__(self, projector: Optional[LanguageProjectorV1] = None) -> None:
        self.projector = projector or get_language_projector()

    def run(
        self,
        source: SemanticInvariant,
        zh_text: str,
        en_text: str,
        *,
        original_input: str = "",
        source_lang: str = "auto",
    ) -> Dict[str, Any]:
        atom_loss = compare_atom_sets(source, parse_to_semantic_invariant(zh_text))
        en_siv = parse_to_semantic_invariant(en_text, source_lang="en")
        en_atom_loss = compare_atom_sets(source, en_siv)
        structural = compare_structure(source, en_siv)

        round_zh = self.projector.project_zh(en_siv)
        round_siv = parse_to_semantic_invariant(round_zh)
        round_atom_loss = compare_atom_sets(source, round_siv)

        zh_faith = faithfulness_score(source, zh_text)
        en_faith = faithfulness_score(source, en_text)
        reversibility = (
            faithfulness_score(source, round_zh)
            + text_similarity(original_input, round_zh) if source_lang == "zh" else faithfulness_score(source, round_zh)
        ) / 2.0

        return {
            "semantic_consistency": {
                "zh_missing": atom_loss["missing_atoms"],
                "zh_extra": atom_loss["extra_atoms"],
                "en_missing": en_atom_loss["missing_atoms"],
                "en_extra": en_atom_loss["extra_atoms"],
            },
            "structural_consistency": structural,
            "round_trip": {
                "s_prime_match": source.invariant_id() == round_siv.invariant_id()
                or not round_atom_loss["missing_atoms"],
                "zh_round_text": round_zh,
                "zh_similarity": text_similarity(original_input, round_zh) if original_input else 1.0,
            },
            "naturalness": {
                "zh": naturalness_heuristic(zh_text, "zh"),
                "en": naturalness_heuristic(en_text, "en"),
            },
            "faithfulness": {"zh": zh_faith, "en": en_faith},
            "reversibility_score": round(reversibility, 4),
            "loss_report": {
                "missing_atoms": sorted(
                    set(atom_loss["missing_atoms"]) | set(en_atom_loss["missing_atoms"])
                ),
                "extra_atoms": sorted(set(atom_loss["extra_atoms"]) | set(en_atom_loss["extra_atoms"])),
                "distorted_relations": structural,
            },
        }


def build_reversible_mapping(
    siv: SemanticInvariant,
    zh_text: str,
    en_text: str,
) -> ReversibleMapping:
    zh_loss = compare_atom_sets(siv, parse_to_semantic_invariant(zh_text))
    en_loss = compare_atom_sets(siv, parse_to_semantic_invariant(en_text))
    return ReversibleMapping(
        zh_sentence=zh_text,
        en_sentence=en_text,
        maps_to=siv.invariant_id(),
        loss_check={
            "missing_atoms": sorted(
                set(zh_loss["missing_atoms"]) | set(en_loss["missing_atoms"])
            ),
            "extra_atoms": sorted(set(zh_loss["extra_atoms"]) | set(en_loss["extra_atoms"])),
        },
    )
