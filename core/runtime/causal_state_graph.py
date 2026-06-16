"""
CNexus Runtime — Causal State Machine Graph (verifiable state system analysis).

Models boot phases, ready gates, and wait-for dependencies as a graph so we can answer:
  - Which transitions are illegal (hard / soft / race)?
  - Which states are unreachable from INIT?
  - Which gates form deadlock cycles?

This is analysis infrastructure — not runtime control logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, FrozenSet, Iterable, List, Optional, Set, Tuple


class TransitionKind(str, Enum):
    CAUSAL = "causal"  # guard must hold; defined in T
    SOFT_ILLEGAL = "soft_illegal"  # edge exists but guard permanently false / violated
    HARD_ILLEGAL = "hard_illegal"  # edge not in T (removed from code)
    RACE = "race"  # time-consistency violation (dual-path)


@dataclass(frozen=True)
class Transition:
    id: str
    source: str
    target: str
    guard: str
    kind: TransitionKind = TransitionKind.CAUSAL
    enabled: bool = True  # False = removed / banned transition


@dataclass(frozen=True)
class WaitEdge:
    """A waits for B — edge in wait-for graph for deadlock detection."""

    waiter: str
    waits_for: str
    condition: str


@dataclass
class CausalStateGraph:
    states: FrozenSet[str]
    initial: str
    transitions: Tuple[Transition, ...]
    wait_edges: Tuple[WaitEdge, ...]
    terminal: FrozenSet[str] = frozenset()

    def outgoing(self, state: str, *, include_disabled: bool = False) -> List[Transition]:
        return [
            t
            for t in self.transitions
            if t.source == state and (include_disabled or (t.enabled and t.kind == TransitionKind.CAUSAL))
        ]

    def incoming(self, state: str) -> List[Transition]:
        return [t for t in self.transitions if t.target == state]


# ---------------------------------------------------------------------------
# CNexus boot + ready gate model (aligned with boot_protocol.py post-causal-fix)
# ---------------------------------------------------------------------------

# Boot phase nodes
S_INIT = "INIT"
S_BOOT_0 = "BOOT_0_API"
S_BOOT_1 = "BOOT_1_RUNTIME_SPAWNED"
S_BOOT_2 = "BOOT_2_HYDRATING"
S_BOOT_3 = "BOOT_3_COGNITIVE_WARMING"
S_BOOT_3_STALL = "BOOT_3_STALL"  # L3 not drained; honest non-ready phase
S_BOOT_4 = "BOOT_4_READY"

# Gate / observable nodes
G_L3_DRAIN = "GATE_L3_QUEUE_DRAINED"
G_ADAPTER_DONE = "GATE_ADAPTER_DONE"
G_BOOT4_CAUSAL = "GATE_BOOT4_CAUSAL_COMMIT"
G_READY_GATE = "GATE_READY_EVALUATION"
G_V5_CLUSTER = "GATE_V5_CLUSTER_IDLE"  # dev / v5 tier only
G_RUST_STRICT = "GATE_RUST_STATUS_READY"

S_STATUS_WARMING = "STATUS_WARMING"
S_STATUS_READY = "STATUS_READY"
S_UI_LIVE = "UI_RUNTIME_LIVE"


def build_cnexus_boot_graph() -> CausalStateGraph:
    """Formal transition relation T + wait-for edges for CNexus runtime boot."""
    states = frozenset(
        {
            S_INIT,
            S_BOOT_0,
            S_BOOT_1,
            S_BOOT_2,
            S_BOOT_3,
            S_BOOT_3_STALL,
            S_BOOT_4,
            G_L3_DRAIN,
            G_ADAPTER_DONE,
            G_BOOT4_CAUSAL,
            G_READY_GATE,
            G_V5_CLUSTER,
            G_RUST_STRICT,
            S_STATUS_WARMING,
            S_STATUS_READY,
            S_UI_LIVE,
        }
    )

    transitions: List[Transition] = [
        # --- Linear boot (causal) ---
        Transition("t_init_api", S_INIT, S_BOOT_0, "app_started"),
        Transition("t_spawn", S_BOOT_0, S_BOOT_1, "runtime_pointer != null"),
        Transition("t_hydrate_start", S_BOOT_1, S_BOOT_2, "hydrate_worker_started"),
        Transition(
            "t_hydrate_done_cog",
            S_BOOT_2,
            S_BOOT_3,
            "hydrate_complete && !cognitive_disabled",
        ),
        Transition(
            "t_hydrate_done_skip",
            S_BOOT_2,
            S_BOOT_4,
            "hydrate_complete && cognitive_disabled",
        ),
        # BOOT_3 → BOOT_4: ONLY causal path
        Transition(
            "t_l3_tick_drain",
            S_BOOT_3,
            G_L3_DRAIN,
            "scheduler.run_tick()",
        ),
        Transition("t_l3_empty", G_L3_DRAIN, G_ADAPTER_DONE, "queue_length == 0"),
        Transition("t_adapter_done", G_ADAPTER_DONE, G_BOOT4_CAUSAL, "adapter.done == true"),
        Transition("t_boot4_commit", G_BOOT4_CAUSAL, S_BOOT_4, "mark_cognitive_warmup_done() causal ok"),
        # Stall path (tick budget / timeout — no phase advance)
        Transition(
            "t_tick_budget",
            S_BOOT_3,
            S_BOOT_3_STALL,
            "tick_budget_exhausted && queue_length > 0",
        ),
        Transition(
            "t_stall_recover",
            S_BOOT_3_STALL,
            G_L3_DRAIN,
            "L3 continues draining",
        ),
        # Ready evaluation
        Transition(
            "t_ready_gate_pass",
            S_BOOT_4,
            G_READY_GATE,
            "phase == BOOT_4",
        ),
        Transition(
            "t_ready_gate_block_cog",
            G_READY_GATE,
            S_STATUS_WARMING,
            "_cognitive_warmup_blocks_ready()",
        ),
        Transition(
            "t_ready_gate_block_v5",
            G_READY_GATE,
            S_STATUS_WARMING,
            "v5_enabled && !cluster_idle",
        ),
        Transition(
            "t_ready_gate_ok",
            G_READY_GATE,
            S_STATUS_READY,
            "!blocks_ready && runtime_present && memory_ok",
        ),
        Transition(
            "t_rust_probe",
            S_STATUS_READY,
            G_RUST_STRICT,
            'JSON status == "ready" && runtime_pointer != false',
        ),
        Transition("t_ui_live", G_RUST_STRICT, S_UI_LIVE, "Tauri emit runtime-ready"),
        # Warming honest loop
        Transition(
            "t_warming_stay",
            S_STATUS_WARMING,
            S_STATUS_WARMING,
            "probe / poll",
        ),
        # --- BANNED (hard illegal — removed from code) ---
        Transition(
            "t_force_boot4_ticks",
            S_BOOT_3,
            S_BOOT_4,
            "tick_budget_exhausted (OPTIMISTIC)",
            kind=TransitionKind.HARD_ILLEGAL,
            enabled=False,
        ),
        Transition(
            "t_force_boot4_timeout",
            S_BOOT_3,
            S_BOOT_4,
            "cognitive_timeout 120s (OPTIMISTIC)",
            kind=TransitionKind.HARD_ILLEGAL,
            enabled=False,
        ),
        Transition(
            "t_force_boot4_exception",
            S_BOOT_3,
            S_BOOT_4,
            "warmup exception swallow (OPTIMISTIC)",
            kind=TransitionKind.HARD_ILLEGAL,
            enabled=False,
        ),
        # --- Soft illegal (edge in old design, guard inconsistent) ---
        Transition(
            "t_optimistic_boot4_ready_gate",
            S_BOOT_4,
            S_STATUS_READY,
            "BOOT_4 without L3 drain (INCONSISTENT)",
            kind=TransitionKind.SOFT_ILLEGAL,
            enabled=False,
        ),
        # --- Race transitions ---
        Transition(
            "t_skipws_ready",
            S_STATUS_WARMING,
            S_UI_LIVE,
            "JS probe skipWs / ready_fast (RACE)",
            kind=TransitionKind.RACE,
            enabled=False,
        ),
        Transition(
            "t_ws_ingest_ready",
            S_STATUS_WARMING,
            S_UI_LIVE,
            "WS state message before REST ready (RACE)",
            kind=TransitionKind.RACE,
            enabled=False,
        ),
    ]

    wait_edges: List[WaitEdge] = [
        WaitEdge(S_STATUS_READY, G_READY_GATE, "evaluate_system_ready == ready"),
        WaitEdge(G_READY_GATE, G_L3_DRAIN, "!_cognitive_warmup_blocks_ready"),
        WaitEdge(G_L3_DRAIN, S_BOOT_3, "L3 scheduler ticks"),
        WaitEdge(G_BOOT4_CAUSAL, G_ADAPTER_DONE, "adapter.done"),
        WaitEdge(G_ADAPTER_DONE, G_L3_DRAIN, "queue_length == 0"),
        WaitEdge(S_UI_LIVE, G_RUST_STRICT, 'status == "ready"'),
        WaitEdge(G_RUST_STRICT, S_STATUS_READY, "HTTP /v1/system/ready"),
        WaitEdge(G_V5_CLUSTER, G_READY_GATE, "v5 cluster + CRDT + consensus idle"),
        # Historical deadlock: optimistic BOOT_4 vs ready gate
        WaitEdge(S_BOOT_4, G_L3_DRAIN, "causal completion (was violated)"),
        WaitEdge(S_BOOT_3_STALL, G_L3_DRAIN, "drain never completes if scheduler stuck"),
    ]

    return CausalStateGraph(
        states=states,
        initial=S_INIT,
        transitions=tuple(transitions),
        wait_edges=tuple(wait_edges),
        terminal=frozenset({S_UI_LIVE}),
    )


# ---------------------------------------------------------------------------
# Graph algorithms
# ---------------------------------------------------------------------------


def reachability(graph: CausalStateGraph, start: Optional[str] = None) -> Dict[str, int]:
    """BFS from initial — returns state -> hop distance (-1 if unreachable)."""
    start = start or graph.initial
    dist: Dict[str, int] = {s: -1 for s in graph.states}
    if start not in graph.states:
        return dist
    dist[start] = 0
    frontier = [start]
    while frontier:
        next_frontier: List[str] = []
        for node in frontier:
            for t in graph.outgoing(node):
                if dist[t.target] < 0:
                    dist[t.target] = dist[node] + 1
                    next_frontier.append(t.target)
        frontier = next_frontier
    return dist


def unreachable_states(graph: CausalStateGraph) -> List[str]:
    dist = reachability(graph)
    return sorted(s for s, d in dist.items() if d < 0)


def dead_entry_states(graph: CausalStateGraph) -> List[str]:
    """States with no incoming causal edge from any other state (except INIT)."""
    has_incoming: Set[str] = set()
    for t in graph.transitions:
        if t.enabled and t.kind == TransitionKind.CAUSAL:
            has_incoming.add(t.target)
    return sorted(s for s in graph.states if s not in has_incoming and s != graph.initial)


def illegal_transitions(graph: CausalStateGraph) -> List[Transition]:
    return [t for t in graph.transitions if t.kind != TransitionKind.CAUSAL or not t.enabled]


def build_wait_for_adjacency(graph: CausalStateGraph) -> Dict[str, Set[str]]:
    adj: Dict[str, Set[str]] = {s: set() for s in graph.states}
    for w in graph.wait_edges:
        if w.waiter in adj:
            adj[w.waiter].add(w.waits_for)
    return adj


def find_wait_cycles(graph: CausalStateGraph) -> List[List[str]]:
    """DFS cycle detection on wait-for graph."""
    adj = build_wait_for_adjacency(graph)
    cycles: List[List[str]] = []
    visited: Set[str] = set()
    stack: Set[str] = set()
    path: List[str] = []

    def dfs(node: str) -> None:
        visited.add(node)
        stack.add(node)
        path.append(node)
        for nxt in adj.get(node, ()):
            if nxt not in visited:
                dfs(nxt)
            elif nxt in stack:
                idx = path.index(nxt)
                cycles.append(path[idx:] + [nxt])
        path.pop()
        stack.remove(node)

    for s in graph.states:
        if s not in visited:
            dfs(s)
    return cycles


def transition_matrix(graph: CausalStateGraph) -> Dict[str, Dict[str, List[str]]]:
    """state × state → list of transition ids."""
    matrix: Dict[str, Dict[str, List[str]]] = {s: {} for s in sorted(graph.states)}
    for t in graph.transitions:
        row = matrix.setdefault(t.source, {})
        row.setdefault(t.target, []).append(t.id)
    return matrix


@dataclass
class AnalysisReport:
    unreachable: List[str]
    dead_entries: List[str]
    illegal: List[Transition]
    wait_cycles: List[List[str]]
    distances: Dict[str, int]
    deadlock_gates: List[str]

    def to_dict(self) -> Dict[str, object]:
        return {
            "unreachable_states": self.unreachable,
            "dead_entry_states": self.dead_entries,
            "illegal_transitions": [
                {
                    "id": t.id,
                    "source": t.source,
                    "target": t.target,
                    "kind": t.kind.value,
                    "guard": t.guard,
                }
                for t in self.illegal
            ],
            "wait_cycles": self.wait_cycles,
            "distances_from_init": {k: v for k, v in self.distances.items() if v >= 0},
            "deadlock_gates": self.deadlock_gates,
        }


def analyze_cnexus_runtime() -> AnalysisReport:
    graph = build_cnexus_boot_graph()
    cycles = find_wait_cycles(graph)
    # Gates that participate in any wait cycle
    cycle_nodes: Set[str] = set()
    for c in cycles:
        cycle_nodes.update(c)

    return AnalysisReport(
        unreachable=unreachable_states(graph),
        dead_entries=dead_entry_states(graph),
        illegal=illegal_transitions(graph),
        wait_cycles=cycles,
        distances=reachability(graph),
        deadlock_gates=sorted(
            n
            for n in cycle_nodes
            if n.startswith("GATE_") or n in (S_BOOT_4, G_READY_GATE, S_STATUS_READY)
        ),
    )


def format_report_text(report: AnalysisReport) -> str:
    lines = [
        "=== CNexus Causal State Graph Analysis ===",
        "",
        "## Illegal transitions (not in T or guard-violating)",
    ]
    for t in report.illegal:
        lines.append(f"  [{t.kind.value}] {t.id}: {t.source} -> {t.target}")
        lines.append(f"      guard: {t.guard}")
    lines.extend(["", "## Unreachable from INIT (causal edges only)"])
    if report.unreachable:
        for s in report.unreachable:
            lines.append(f"  - {s}")
    else:
        lines.append("  (none)")
    lines.extend(["", "## Dead-entry states (no incoming causal edge)"])
    for s in report.dead_entries:
        lines.append(f"  - {s}")
    lines.extend(["", "## Wait-for cycles (deadlock)"])
    if report.wait_cycles:
        for i, c in enumerate(report.wait_cycles, 1):
            lines.append(f"  cycle {i}: {' -> '.join(c)}")
    else:
        lines.append("  (none in static wait-for graph)")
    lines.extend(["", "## Deadlock gate nodes"])
    for g in report.deadlock_gates:
        lines.append(f"  - {g}")
    lines.extend(["", "## Reachability distances from INIT"])
    for s, d in sorted(report.distances.items()):
        if d >= 0:
            lines.append(f"  {s}: {d}")
    return "\n".join(lines)


if __name__ == "__main__":
    print(format_report_text(analyze_cnexus_runtime()))
