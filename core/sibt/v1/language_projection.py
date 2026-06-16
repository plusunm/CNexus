"""SIBT v1 — language projection layer (Layer 1, render not translate)."""

from __future__ import annotations

from typing import Dict, List

from core.sibt.v1.semantic_invariant import SemanticInvariant, detect_language

_INTENT_ZH: Dict[str, str] = {
    "system_or_user_goal": "系统与用户目标",
    "improvement_goal": "改进目标",
    "remediation_goal": "修复目标",
    "optimization_goal": "优化目标",
    "issue_report": "问题报告",
}

_INTENT_EN: Dict[str, str] = {
    "system_or_user_goal": "System and user goal",
    "improvement_goal": "Improvement goal",
    "remediation_goal": "Remediation goal",
    "optimization_goal": "Optimization goal",
    "issue_report": "Issue report",
}

_ATOM_ZH_HINTS: Dict[str, str] = {
    "ui language switching": "界面语言切换",
    "translation accuracy issue exists": "存在翻译准确度问题",
    "need prompt design improvement": "需要改进提示词设计",
    "low latency": "低延迟要求",
    "no blocking": "不允许阻塞",
    "no semantic drift": "不允许语义漂移",
    "runtime": "运行时",
    "scheduler": "调度器",
}


def _atom_to_zh(atom: str) -> str:
    low = atom.strip().lower()
    if detect_language(atom) == "zh":
        return atom.strip()
    if low in _ATOM_ZH_HINTS:
        return _ATOM_ZH_HINTS[low]
    if "translation" in low and "accuracy" in low:
        return "翻译准确度存在问题"
    if "language switching" in low or "语言切换" in atom:
        return "界面语言切换"
    if "prompt" in low and "design" in low:
        return "需要优化提示词设计"
    return atom.strip()


def _atom_to_en(atom: str) -> str:
    if detect_language(atom) == "en" and not any("\u4e00" <= c <= "\u9fff" for c in atom):
        return atom.strip()
    zh_to_en = {v: k for k, v in _ATOM_ZH_HINTS.items()}
    stripped = atom.strip()
    if stripped in zh_to_en:
        return zh_to_en[stripped].capitalize()
    if "界面" in atom and "语言" in atom:
        return "UI language switching"
    if "翻译" in atom and ("准确" in atom or "问题" in atom):
        return "Translation accuracy issue exists"
    if "提示词" in atom or "prompt" in atom.lower():
        return "Prompt design needs improvement"
    if "低延迟" in atom:
        return "Low latency requirement"
    if "阻塞" in atom:
        return "No blocking allowed"
    if "语义漂移" in atom:
        return "No semantic drift allowed"
    return stripped


def _constraint_zh(c: str) -> str:
    mapping = {
        "low latency": "低延迟",
        "no semantic drift": "禁止语义漂移",
        "no blocking": "禁止阻塞",
    }
    return mapping.get(c.lower(), c)


def _constraint_en(c: str) -> str:
    mapping = {
        "低延迟": "low latency",
        "禁止语义漂移": "no semantic drift",
        "禁止阻塞": "no blocking",
    }
    return mapping.get(c, c)


class LanguageProjectorV1:
    """Project semantic invariant to native system language — not literal translation."""

    def project_zh(self, siv: SemanticInvariant) -> str:
        intent_line = _INTENT_ZH.get(siv.intent, siv.intent)
        atom_lines = [_atom_to_zh(a) for a in siv.meaning_atoms]
        constraint_lines = [_constraint_zh(c) for c in siv.constraints]

        parts: List[str] = [f"【意图】{intent_line}"]
        if atom_lines:
            parts.append("【语义原子】" + "；".join(atom_lines))
        if siv.relations:
            rel_bits = [
                f"{r['from']}→{r['to']}({r['type']})" for r in siv.relations[:6]
            ]
            parts.append("【关系】" + "，".join(rel_bits))
        if constraint_lines:
            parts.append("【约束】" + "；".join(constraint_lines))
        return "\n".join(parts)

    def project_en(self, siv: SemanticInvariant) -> str:
        intent_line = _INTENT_EN.get(siv.intent, siv.intent)
        atom_lines = [_atom_to_en(a) for a in siv.meaning_atoms]
        constraint_lines = [_constraint_en(c) for c in siv.constraints]

        parts: List[str] = [f"[Intent] {intent_line}"]
        if atom_lines:
            parts.append("[Meaning atoms] " + "; ".join(atom_lines))
        if siv.relations:
            rel_bits = [
                f"{r['from']} -> {r['to']} ({r['type']})" for r in siv.relations[:6]
            ]
            parts.append("[Relations] " + ", ".join(rel_bits))
        if constraint_lines:
            parts.append("[Constraints] " + "; ".join(constraint_lines))
        return "\n".join(parts)


def get_language_projector() -> LanguageProjectorV1:
    return LanguageProjectorV1()
