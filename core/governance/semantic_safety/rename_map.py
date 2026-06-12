"""Semantic Safety v2 rename registry."""

from __future__ import annotations

import json
from pathlib import Path

_MAP_PATH = Path(__file__).with_name("rename_map.json")
_DATA = json.loads(_MAP_PATH.read_text(encoding="utf-8"))

RENAME_MAP: dict[str, str] = _DATA["renames"]
DEPRECATED_ALIASES: dict[str, str] = {v: k for k, v in RENAME_MAP.items()}
OUTPUT_FIELD_RENAMES: dict[str, str] = _DATA["output_field_renames"]
CDG_CONTROL_EXEMPT: frozenset[str] = frozenset(_DATA["cdg_control_layer_exempt"])
