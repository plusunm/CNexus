"""Bridge Σ_exec executors to BrainMemoryRuntime (Σ_cognitive)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from ir_kernel.schema.sigma_exec import CommitEvent, MemoryRef, hash_text

if TYPE_CHECKING:
    from brain_memory.runtime import BrainMemoryRuntime


@dataclass
class RecallResult:
    context: str
    memory_refs: List[MemoryRef] = field(default_factory=list)
    governance_notes: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class OutboundBundle:
    system_prompt: str
    messages: List[Dict[str, str]]
    governance_injection: str
    context: str
    outbound_preview: str


@dataclass
class GovernResult:
    approved: bool
    reply: str
    reason: str = ""
    notes: List[Dict[str, Any]] = field(default_factory=list)


class RuntimeFacade:
    """
    IR Kernel may only interact with Σ_cognitive through this facade.
    READ paths use read_only recall where possible; WRITE paths enqueue commits.
    """

    def __init__(self, runtime: "BrainMemoryRuntime"):
        self._runtime = runtime

    @property
    def runtime(self) -> "BrainMemoryRuntime":
        return self._runtime

    def recall_for_ir(
        self,
        query: str,
        *,
        top_k: Optional[int] = None,
        read_only: bool = True,
    ) -> RecallResult:
        rt = self._runtime
        k = top_k
        if k is None:
            k = int(rt.config.get("chat_recall_top_k", 6))

        context = rt.recall_pipeline.recall(
            query,
            top_k=k,
            use_attention=not read_only,
            mutate_state=not read_only,
        )

        refs: List[MemoryRef] = []
        explain = rt.recall_pipeline.last_explain or {}
        for idx, label in enumerate(explain.get("top_labels") or []):
            if not label:
                continue
            refs.append(
                MemoryRef(
                    ref_type="recall_excerpt",
                    ref_id=str(label),
                    score=float(idx),
                    excerpt_hash=hash_text(context[:512]) if context else "",
                )
            )

        return RecallResult(context=context, memory_refs=refs)

    def filter_context(self, context: str, *, max_chars: Optional[int] = None) -> str:
        limit = max_chars or int(self._runtime.config.get("chat_max_context_chars", 4000))
        if len(context) <= limit:
            return context
        return context[:limit] + "\n…"

    def build_outbound(
        self,
        user_message: str,
        context: str,
        *,
        chat_governance_notes: Optional[List[Dict[str, Any]]] = None,
    ) -> OutboundBundle:
        notes = list(chat_governance_notes or [])
        governance = self._runtime._build_chat_governance_injection(user_message, notes)
        system_prompt, messages = self._runtime._compose_chat_llm_messages(
            user_message,
            context,
            extra_system=governance or None,
        )
        preview = self._runtime._format_chat_outbound_preview(
            user_message,
            context,
            governance,
            system_prompt,
        )
        return OutboundBundle(
            system_prompt=system_prompt,
            messages=messages,
            governance_injection=governance,
            context=context,
            outbound_preview=preview,
        )

    def call_llm(
        self,
        user_message: str,
        context: str,
        *,
        governance_injection: str = "",
        llm_client: Any = None,
        llm_profile: Any = None,
        temperature: float = 0.7,
    ) -> str:
        return self._runtime._generate_llm_response(
            user_message,
            context,
            temperature=temperature,
            llm_client=llm_client,
            llm_profile=llm_profile,
            extra_system=governance_injection or None,
        )

    def govern_output(self, text: str) -> GovernResult:
        rt = self._runtime
        decision = rt.governance_pipeline.check_output(
            text,
            rt.working_self,
            rt.dna_engine.dna,
        )
        if decision.approved:
            return GovernResult(approved=True, reply=text, reason=decision.reason)
        safe = decision.safe_text or text
        return GovernResult(
            approved=False,
            reply=safe,
            reason=decision.reason,
            notes=[decision.to_dict()],
        )

    def enqueue_capture(
        self,
        pending: List[CommitEvent],
        *,
        role: str,
        content: str,
        meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        pending.append(
            CommitEvent(
                kind="capture",
                role=role,
                content=content,
                meta=dict(meta or {}),
            )
        )

    def apply_commits(self, events: List[CommitEvent]) -> List[Dict[str, Any]]:
        """CommitRunner — sole writer to Σ_cognitive from IR path."""
        from core.governance.gtbs.adapters.ir_adapter import maybe_emit_ir_commit_shadow

        maybe_emit_ir_commit_shadow(self._runtime, events=events, commit=True)
        results: List[Dict[str, Any]] = []
        for event in events:
            if event.kind != "capture":
                results.append({"kind": event.kind, "skipped": True})
                continue
            capture_id = self._runtime.capture(
                event.role,
                event.content,
                importance=0.65 if event.role == "user" else 0.5,
                **(event.meta or {}),
            )
            results.append({"kind": "capture", "role": event.role, "id": str(capture_id)})
        from core.spine.hooks.mutation import emit_ir_mutation

        capture_n = sum(1 for e in events if getattr(e, "kind", None) == "capture")
        emit_ir_mutation(event_count=len(events), capture_count=capture_n)
        return results
