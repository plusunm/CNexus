"""Lightweight runtime warm metadata — safe for /health and warming ready payloads."""

from __future__ import annotations

import os
import time
from typing import Optional

_runtime_warming: bool = False
_runtime_init_error: Optional[str] = None
_runtime_last_warm_mono: float = 0.0
_RUNTIME_WARM_COOLDOWN_SEC = float(os.environ.get("CNEXUS_RUNTIME_WARM_COOLDOWN_SEC", "60"))


def reset_runtime_warm_status() -> None:
    global _runtime_warming, _runtime_init_error, _runtime_last_warm_mono
    _runtime_warming = False
    _runtime_init_error = None
    _runtime_last_warm_mono = 0.0


def mark_runtime_warming_flag(active: bool) -> None:
    global _runtime_warming
    _runtime_warming = active


def record_runtime_warm_attempt(*, init_error: Optional[str] = None) -> None:
    global _runtime_init_error, _runtime_last_warm_mono
    _runtime_init_error = init_error
    _runtime_last_warm_mono = time.monotonic()


def clear_runtime_init_error() -> None:
    global _runtime_init_error
    _runtime_init_error = None


def runtime_warm_meta() -> dict:
    now = time.monotonic()
    in_cooldown = (
        _runtime_last_warm_mono > 0
        and (now - _runtime_last_warm_mono) < _RUNTIME_WARM_COOLDOWN_SEC
    )
    return {
        "warming": _runtime_warming,
        "init_error": _runtime_init_error,
        "last_attempt_mono": _runtime_last_warm_mono,
        "cooldown_sec": _RUNTIME_WARM_COOLDOWN_SEC,
        "in_cooldown": in_cooldown,
    }


def can_retry_runtime_warm(*, force: bool = False, runtime_loaded: bool = False) -> bool:
    if force:
        return True
    if runtime_loaded or _runtime_warming:
        return False
    return not runtime_warm_meta()["in_cooldown"]
