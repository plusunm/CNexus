"""Backward-compatible re-exports — use core.self_model instead."""

from core.self_model.self_model import SelfModel
from core.self_model.store import SelfModelStore

__all__ = ["SelfModel", "SelfModelStore"]
