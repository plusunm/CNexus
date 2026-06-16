"""DAG scheduler — ready-set loop with Π and V."""

from __future__ import annotations

import uuid
from typing import Optional

from ir_kernel.adapters.runtime_facade import RuntimeFacade
from ir_kernel.policy.cost import step_cost_delta
from ir_kernel.policy.greedy_policy import GreedyPolicy
from ir_kernel.runtime.executor import ExecContext, NodeExecutor
from ir_kernel.schema.graph import IRGraph
from ir_kernel.schema.sigma_exec import ExecStep, SigmaExec, hash_text
from ir_kernel.verifier.graph_verifier import GraphVerifier


class DAGScheduler:
    def __init__(
        self,
        *,
        policy: Optional[GreedyPolicy] = None,
        verifier: Optional[GraphVerifier] = None,
        executor: Optional[NodeExecutor] = None,
    ):
        self.policy = policy or GreedyPolicy()
        self.verifier = verifier or GraphVerifier()
        self.executor = executor or NodeExecutor()

    def run(
        self,
        graph: IRGraph,
        sigma: SigmaExec,
        facade: RuntimeFacade,
        ctx: ExecContext,
    ) -> SigmaExec:
        check = self.verifier.verify_graph(graph)
        if not check.ok:
            sigma.status = "failed"
            sigma.error = {"code": "GRAPH_INVALID", "message": ";".join(check.errors)}
            return sigma

        sigma.status = "running"
        sigma.graph_id = graph.graph_id
        sigma.variables["input"] = str(sigma.input.get("user_message", ""))

        deps = graph.dependency_map()
        completed: set[str] = set()

        while len(completed) < len(graph.nodes):
            ready_ids = [
                nid
                for nid, node_deps in deps.items()
                if nid not in completed and node_deps.issubset(completed)
            ]
            if not ready_ids:
                sigma.status = "failed"
                sigma.error = {"code": "DEADLOCK", "message": "no ready nodes"}
                break

            ready_nodes = [graph.nodes[nid] for nid in ready_ids]
            ordered = self.policy.sort_ready(ready_nodes, sigma)

            for node in ordered:
                pre = self.verifier.verify_budget_pre(sigma, node.op)
                if not pre.ok:
                    sigma.status = "aborted"
                    sigma.error = {"code": pre.errors[0], "node_id": node.id}
                    return sigma

                try:
                    result = self.executor.run(node, sigma, facade, ctx)
                except Exception as exc:
                    sigma.status = "failed"
                    sigma.error = {"code": "EXEC_ERROR", "node_id": node.id, "message": str(exc)}
                    return sigma

                post = self.verifier.verify_step_post(sigma, result.value)
                if not post.ok:
                    sigma.status = "failed"
                    sigma.error = {"code": "STEP_INVALID", "node_id": node.id}
                    return sigma

                sigma.variables.update(result.extra_variables)
                step = ExecStep(
                    step_id=f"st_{uuid.uuid4().hex[:12]}",
                    step_index=len(sigma.steps),
                    node_id=node.id,
                    op=node.op,
                    layer=node.layer.value,
                    input_keys=list(node.inputs),
                    output_key=result.output_key,
                    output_preview=(result.value or "")[:500],
                    output_hash=hash_text(result.value or ""),
                    cost_delta=step_cost_delta(node.op, output=result.value, latency_ms=result.latency_ms),
                    verifier={"passed": True, "rules": ["budget_ok", "schema_ok"]},
                    state_variables=dict(result.extra_variables),
                )
                sigma.append_step(step)
                completed.add(node.id)

        if sigma.status == "running":
            sigma.status = "completed"
        return sigma
