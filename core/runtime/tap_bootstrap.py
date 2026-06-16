"""Bootstrap execution tap persistence from runtime base_dir."""

from __future__ import annotations

from typing import Optional

_configured_base: Optional[str] = None


def configure_execution_tap_persistence(base_dir: str) -> None:
    global _configured_base
    from core.runtime.execution_tap import get_execution_tap

    _configured_base = str(base_dir)
    tap = get_execution_tap()
    tap.set_persist_base(base_dir)
    tap.hydrate_from_disk()


def hydrate_execution_stores_sync(base_dir: str) -> None:
    """Sync disk hydrate — MUST run off the asyncio event loop (Fix Contract L2)."""
    from core.kernel.identity.index_v1 import configure_identity_graph_index
    from core.spine.identity.store import configure_identity_store
    from core.spine.token.token_store import configure_token_store

    configure_execution_tap_persistence(base_dir)
    configure_identity_store(base_dir)
    configure_identity_graph_index(base_dir)
    configure_token_store(base_dir)


def maybe_persist_tap_event(row: dict) -> None:
    if not _configured_base:
        return
    from core.runtime.tap_storage import ExecutionTapLog

    ExecutionTapLog(_configured_base).append(row)
