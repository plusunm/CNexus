"""Kernel enforce mode flags."""

from __future__ import annotations

import os


def enforce_mode() -> bool:
    """CP-3 reality gate — non-kernel execution paths are invalid."""
    flag = os.environ.get("KERNEL_ENFORCE_MODE", "1").strip().lower()
    return flag not in ("0", "false", "no", "off")


def hard_lock_mode() -> bool:
    """CP-3 final lock — no legacy/bypass paths (compile + runtime)."""
    flag = os.environ.get("KERNEL_HARD_LOCK_MODE", "1").strip().lower()
    return flag not in ("0", "false", "no", "off")


def legacy_allowed() -> bool:
    """Legacy execution fallback — disabled under hard lock."""
    if hard_lock_mode():
        return False
    flag = os.environ.get("KERNEL_LEGACY_ALLOW", "0").strip().lower()
    return flag in ("1", "true", "yes", "on")


def execution_via_kernel_required() -> bool:
    """Kernel path mandatory."""
    from core.kernel.kernel import kernel_enabled

    return kernel_enabled() or enforce_mode() or hard_lock_mode()
