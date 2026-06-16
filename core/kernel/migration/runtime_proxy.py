"""RuntimeProxy — intercept runtime calls and route through kernel."""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from core.kernel.enforce.exceptions import KernelViolation
from core.kernel.migration.auto_wrap import (
    BYPASS_KERNEL,
    KERNEL_INTERNAL,
    should_intercept,
    strip_kernel_flags,
)
from core.kernel.migration.intent_mapper import map_runtime_call

if TYPE_CHECKING:
    from brain_memory.runtime import BrainMemoryRuntime
    from core.kernel.kernel import ExecutionKernel


class RuntimeProxy:
    """Transparent proxy: external runtime.xxx() → kernel.execute(intent) → runtime.xxx()."""

    def __init__(self, runtime: "BrainMemoryRuntime", kernel: "ExecutionKernel") -> None:
        object.__setattr__(self, "_runtime", runtime)
        object.__setattr__(self, "_kernel", kernel)

    @property
    def kernel(self) -> "ExecutionKernel":
        return object.__getattribute__(self, "_kernel")

    @property
    def runtime(self) -> "BrainMemoryRuntime":
        return object.__getattribute__(self, "_runtime")

    def unwrap(self) -> "BrainMemoryRuntime":
        return object.__getattribute__(self, "_runtime")

    def __getattr__(self, name: str) -> Any:
        runtime = object.__getattribute__(self, "_runtime")
        attr = getattr(runtime, name)

        if not callable(attr) or not should_intercept(name):
            return attr

        kernel = object.__getattribute__(self, "_kernel")

        def wrapped(*args: Any, **kwargs: Any) -> Any:
            if kwargs.get(KERNEL_INTERNAL):
                return attr(*args, **kwargs)
            if kwargs.get(BYPASS_KERNEL):
                from core.kernel.enforce.gate import get_enforce_gate
                from core.kernel.enforce.mode import hard_lock_mode

                get_enforce_gate().block_bypass()
                if hard_lock_mode():
                    raise KernelViolation("KERNEL_BYPASS_FORBIDDEN")
                return attr(*args, **kwargs)

            intent = map_runtime_call(name, args, kwargs, source="runtime_proxy")
            explicit_trace = kwargs.get("trace_id")
            if explicit_trace and not intent.trace_id:
                intent.trace_id = str(explicit_trace)
            record = kernel.execute(intent)
            if hasattr(record, "to_legacy_response"):
                return record.to_legacy_response()
            return record

        return wrapped

    def __setattr__(self, name: str, value: Any) -> None:
        runtime = object.__getattribute__(self, "_runtime")
        setattr(runtime, name, value)

    def __repr__(self) -> str:
        runtime = object.__getattribute__(self, "_runtime")
        return f"RuntimeProxy({runtime!r})"
