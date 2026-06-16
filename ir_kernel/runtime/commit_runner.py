"""CommitRunner — apply pending_commits to Σ_cognitive."""

from __future__ import annotations

from typing import Any, Dict, List

from ir_kernel.adapters.runtime_facade import RuntimeFacade
from ir_kernel.schema.sigma_exec import CommitEvent, SigmaExec


class CommitRunner:
    def run(self, facade: RuntimeFacade, sigma: SigmaExec, *, enabled: bool = True) -> List[Dict[str, Any]]:
        if not enabled or not sigma.pending_commits:
            return []
        events = list(sigma.pending_commits)
        results = facade.apply_commits(events)
        sigma.pending_commits.clear()
        return results
