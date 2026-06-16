"""CP-3 runtime migration — transparent kernel interceptor."""

from core.kernel.migration.patch_runtime import (
    create_kernel_for,
    migration_enabled,
    patch_runtime,
)
from core.kernel.migration.runtime_proxy import RuntimeProxy

__all__ = [
    "RuntimeProxy",
    "create_kernel_for",
    "migration_enabled",
    "patch_runtime",
]
