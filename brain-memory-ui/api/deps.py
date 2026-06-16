import logging
import os
import sys
import threading
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Resolve cognitive core root (wheel dist uses BRAIN_MEMORY_ROOT=/app)
ROOT = Path(os.environ.get("BRAIN_MEMORY_ROOT", Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(ROOT))
os.environ.setdefault("BRAIN_MEMORY_ROOT", str(ROOT))
os.environ.setdefault(
    "BM_MEMORY_DIR",
    str(Path(os.environ.get("ProgramData", "C:/ProgramData")) / "cnexus" / "data"),
)

from brain_memory import BrainMemoryRuntime
from core.control_plane.dispatch import AuthorityDispatcher
from core.control_plane.legacy_adapter import LegacyDispatchAdapter
from core.kernel.migration.patch_runtime import create_kernel_for, migration_enabled, patch_runtime
from core.kernel.kernel import ExecutionKernel
from core.runtime.boot_protocol import mark_runtime_spawned, mark_runtime_warming
from core.runtime.thread_registry import COGNITIVE_WARM_ROLE, RUNTIME_WARM_ROLE, register_warm_thread
from core.llm_client import LLMClient
from core.model_registry import ModelRegistry
from core.skill.skill_registry import SkillRegistry, build_default_skill_registry

_runtime: Optional[BrainMemoryRuntime] = None
_runtime_core: Optional[BrainMemoryRuntime] = None
_dispatcher: Optional[AuthorityDispatcher] = None
_legacy_adapter: Optional[LegacyDispatchAdapter] = None
_kernel: Optional[ExecutionKernel] = None
_registry: Optional[ModelRegistry] = None
_skills: Optional[SkillRegistry] = None
_runtime_lock = threading.Lock()
_runtime_warming = False
from api.runtime_warm_status import (
    can_retry_runtime_warm as _can_retry_runtime_warm,
    clear_runtime_init_error,
    mark_runtime_warming_flag,
    record_runtime_warm_attempt,
    runtime_warm_meta,
)


class RuntimeNotReady(Exception):
    """Raised when BrainMemoryRuntime is still initializing — avoid blocking the API event loop."""


def can_retry_runtime_warm(*, force: bool = False) -> bool:
    return _can_retry_runtime_warm(force=force, runtime_loaded=_runtime is not None)


def peek_runtime() -> Optional[BrainMemoryRuntime]:
    """Non-blocking: returns None while BrainMemoryRuntime is still initializing."""
    return _runtime_core or _runtime


def _create_runtime() -> BrainMemoryRuntime:
    global _runtime, _runtime_core, _kernel
    from core.paths import ensure_runtime_data_dirs, resolve_memory_dir

    memory_dir = resolve_memory_dir(ROOT, "memory")
    os.environ["BM_MEMORY_DIR"] = memory_dir
    ensure_runtime_data_dirs(memory_dir)
    mark_runtime_warming(True)
    core = BrainMemoryRuntime(project_root=str(ROOT))
    _runtime_core = core
    facade = patch_runtime(core)
    _runtime = facade
    if migration_enabled() and hasattr(facade, "kernel"):
        _kernel = facade.kernel  # type: ignore[attr-defined]
    else:
        _kernel = create_kernel_for(core)
    mark_runtime_spawned()
    return facade


def get_runtime() -> BrainMemoryRuntime:
    """Return loaded runtime only — never construct on the caller thread (Fix Contract L1)."""
    rt = peek_runtime()
    if rt is None:
        raise RuntimeNotReady("BrainMemoryRuntime is still initializing")
    return rt


def get_runtime_core() -> BrainMemoryRuntime:
    """Unwrapped executor — for dispatcher / kernel router (no double intercept)."""
    if _runtime_core is not None:
        return _runtime_core
    if _runtime is not None:
        return _runtime
    raise RuntimeNotReady("BrainMemoryRuntime is still initializing")


def warm_runtime_background(*, force: bool = False) -> None:
    """Start BrainMemoryRuntime init on a background thread (desktop boot probe must stay fast)."""
    global _runtime_warming
    if _runtime is not None or _runtime_warming:
        return
    if not can_retry_runtime_warm(force=force):
        return
    _runtime_warming = True
    mark_runtime_warming(True)
    mark_runtime_warming_flag(True)

    def _work() -> None:
        global _runtime_warming
        from api.runtime_log import runtime_log

        try:
            with _runtime_lock:
                if _runtime is None:
                    _create_runtime()
                    clear_runtime_init_error()
        except Exception as exc:
            err = f"{exc.__class__.__name__}: {exc}"
            record_runtime_warm_attempt(init_error=err)
            logger.exception("BrainMemoryRuntime init failed")
            try:
                from core.runtime.conflict_monitor import log_runtime_warm_failure

                log_runtime_warm_failure(err)
            except Exception:
                pass
            runtime_log(
                "error",
                "runtime_warm",
                "BrainMemoryRuntime init failed",
                error=err,
            )
        else:
            record_runtime_warm_attempt(init_error=None)
            try:
                from api.control_plane_workers import schedule_post_runtime_workers

                schedule_post_runtime_workers()
            except Exception:
                logger.exception("post-runtime worker schedule failed")
        finally:
            _runtime_warming = False
            mark_runtime_warming(False)
            mark_runtime_warming_flag(False)

    thread = threading.Thread(target=_work, name="cnexus-runtime-warm", daemon=True)
    register_warm_thread(RUNTIME_WARM_ROLE, thread)
    thread.start()


def start_cognitive_warmup_background() -> None:
    """Detached cognitive warmup — never blocks control-plane health/ready."""
    import time

    from core.runtime.boot_protocol import (
        cognitive_disabled,
        is_hydrate_complete,
    )

    if cognitive_disabled():
        return

    def _work() -> None:
        for _ in range(240):
            if peek_runtime() is not None and is_hydrate_complete():
                break
            time.sleep(0.5)
        try:
            runtime = peek_runtime()
            if runtime is None:
                logger.warning("Cognitive warmup skipped: runtime pointer missing")
                return
            core = _runtime_core or runtime
            from core.runtime.cognitive_warmup_adapter import run_cognitive_warmup_ticks

            run_cognitive_warmup_ticks(core)
        except Exception:
            logger.exception("Cognitive warmup failed — holding BOOT_3 (no optimistic BOOT_4)")

    thread = threading.Thread(target=_work, name="cnexus-cognitive-warm", daemon=True)
    register_warm_thread(COGNITIVE_WARM_ROLE, thread)
    thread.start()


def get_dispatcher() -> AuthorityDispatcher:
    global _dispatcher
    if _dispatcher is None:
        with _runtime_lock:
            if _dispatcher is None:
                _dispatcher = AuthorityDispatcher(get_runtime_core())
    return _dispatcher


def get_legacy_adapter() -> LegacyDispatchAdapter:
    global _legacy_adapter
    if _legacy_adapter is None:
        with _runtime_lock:
            if _legacy_adapter is None:
                _legacy_adapter = LegacyDispatchAdapter(get_dispatcher())
    return _legacy_adapter


def get_kernel() -> ExecutionKernel:
    get_runtime()
    if _kernel is None:
        raise RuntimeNotReady("ExecutionKernel not ready")
    return _kernel


def get_registry() -> ModelRegistry:
    global _registry
    if _registry is None:
        with _runtime_lock:
            if _registry is None:
                _registry = ModelRegistry(str(ROOT / "config"))
    return _registry


def get_llm() -> LLMClient:
    return get_runtime().llm_client


def get_skill_registry() -> SkillRegistry:
    global _skills
    if _skills is None:
        with _runtime_lock:
            if _skills is None:
                _skills = build_default_skill_registry(get_runtime())
    return _skills
