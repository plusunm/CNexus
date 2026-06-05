# -*- coding: utf-8 -*-
"""Load plugin config: default.json + env overrides."""

from __future__ import annotations

import json
import os
from typing import Any, Dict


def load_plugin_config(overrides: Dict[str, Any] | None = None) -> Dict[str, Any]:
    cfg: Dict[str, Any] = {}
    plugin_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    default_path = os.path.join(plugin_dir, "config", "default.json")
    if os.path.isfile(default_path):
        with open(default_path, encoding="utf-8") as f:
            cfg.update(json.load(f))
    if overrides:
        cfg.update(overrides)
    if os.environ.get("OLLAMA_HOST"):
        cfg["ollama_host"] = os.environ["OLLAMA_HOST"]
    if os.environ.get("OLLAMA_MODELS"):
        cfg["ollama_models"] = os.environ["OLLAMA_MODELS"]
    if os.environ.get("LLM_MODEL"):
        cfg["llm_model"] = os.environ["LLM_MODEL"]
    return cfg
