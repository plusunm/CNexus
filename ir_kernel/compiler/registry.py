"""Compiler plugins — template → G."""

from __future__ import annotations

import hashlib
import json
from typing import Callable, Dict

from ir_kernel.schema.graph import IRGraph

CompilerFn = Callable[..., IRGraph]

_REGISTRY: Dict[str, CompilerFn] = {}


def register(name: str, fn: CompilerFn) -> None:
    _REGISTRY[name] = fn


def compile_template(name: str, **kwargs) -> IRGraph:
    if name not in _REGISTRY:
        raise KeyError(f"unknown_template:{name}")
    return _REGISTRY[name](**kwargs)


def list_templates() -> list[str]:
    return sorted(_REGISTRY.keys())


def compute_graph_id(template_name: str, template_version: str, payload: dict) -> str:
    raw = json.dumps(
        {"template": template_name, "version": template_version, "payload": payload},
        sort_keys=True,
        ensure_ascii=False,
    )
    return f"g_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"
