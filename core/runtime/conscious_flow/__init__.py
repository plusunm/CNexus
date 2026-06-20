"""L4 conscious flow — parallel simulation sandbox (Σ.T only)."""

from core.runtime.conscious_flow.simulation_engine import (
    SimulationEngine,
    append_simulation_trace,
    build_simulation_context,
    estimate_branch_stability,
    rule_based_branch_simulator,
    schedule_background_simulation,
)
from core.runtime.conscious_flow.types import (
    CandidateResponse,
    SimulatedTraj,
    SimulationBudget,
    ThoughtBranch,
)

__all__ = [
    "CandidateResponse",
    "SimulatedTraj",
    "SimulationBudget",
    "SimulationEngine",
    "ThoughtBranch",
    "append_simulation_trace",
    "build_simulation_context",
    "estimate_branch_stability",
    "rule_based_branch_simulator",
    "schedule_background_simulation",
]
