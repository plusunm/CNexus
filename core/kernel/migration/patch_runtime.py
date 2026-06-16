"""One-shot runtime patching — inject Execution Interceptor at boot."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Union

from core.kernel.kernel import ExecutionKernel
from core.kernel.migration.runtime_proxy import RuntimeProxy

if TYPE_CHECKING:
    from brain_memory.runtime import BrainMemoryRuntime


def migration_enabled() -> bool:
    flag = os.environ.get("KERNEL_MIGRATION_ENABLED", "1").strip().lower()
    return flag not in ("0", "false", "no", "off")


def patch_runtime(runtime: "BrainMemoryRuntime") -> Union["BrainMemoryRuntime", RuntimeProxy]:
    """Wrap runtime with interceptor proxy; kernel always holds the raw executor."""
    if not migration_enabled():
        return runtime
    kernel = ExecutionKernel(runtime)
    return RuntimeProxy(runtime, kernel)


def create_kernel_for(runtime: "BrainMemoryRuntime") -> ExecutionKernel:
    """Shared kernel factory — always bound to unwrapped runtime."""
    return ExecutionKernel(runtime)
