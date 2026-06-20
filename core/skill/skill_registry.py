"""SkillRegistry — register and execute persistent CNexus agent skills."""

from __future__ import annotations

import inspect
import json
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, Field


class SkillSpec(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any] = Field(default_factory=dict)

class SkillRegistry:
    """In-process skill registry with OpenAI tools schema export."""

    def __init__(self) -> None:
        self._specs: Dict[str, SkillSpec] = {}
        self._handlers: Dict[str, Callable[..., Any]] = {}

    def register(
        self,
        spec: SkillSpec,
        handler: Callable[..., Any],
    ) -> None:
        self._specs[spec.name] = spec
        self._handlers[spec.name] = handler

    def register_function(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        handler: Callable[..., Any],
    ) -> None:
        self.register(SkillSpec(name=name, description=description, parameters=parameters), handler)

    def get(self, name: str) -> Optional[SkillSpec]:
        return self._specs.get(name)

    def list_specs(self) -> List[SkillSpec]:
        return list(self._specs.values())

    def list_openai_tools(self) -> List[Dict[str, Any]]:
        tools: List[Dict[str, Any]] = []
        for spec in self._specs.values():
            properties = spec.parameters.get("properties")
            if properties is None:
                properties = {
                    key: {"type": "string"}
                    for key in spec.parameters
                    if key not in ("type", "required", "properties")
                }
            required = spec.parameters.get("required")
            if required is None and properties:
                required = list(properties.keys())
            tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": spec.name,
                        "description": spec.description,
                        "parameters": {
                            "type": "object",
                            "properties": properties,
                            "required": required or [],
                        },
                    },
                }
            )
        return tools

    async def execute(self, name: str, arguments: Dict[str, Any]) -> Any:
        if name not in self._handlers:
            raise ValueError(f"Skill {name} not found")
        handler = self._handlers[name]
        result = handler(**arguments)
        if inspect.isawaitable(result):
            return await result
        return result

    async def execute_tool_call(self, name: str, arguments_json: str) -> str:
        try:
            args = json.loads(arguments_json) if arguments_json else {}
        except json.JSONDecodeError as exc:
            return json.dumps({"error": f"invalid arguments JSON: {exc}"}, ensure_ascii=False)
        if not isinstance(args, dict):
            return json.dumps({"error": "arguments must be a JSON object"}, ensure_ascii=False)
        try:
            result = await self.execute(name, args)
            if isinstance(result, str):
                return result
            return json.dumps(result, ensure_ascii=False, default=str)
        except Exception as exc:
            return json.dumps({"error": str(exc)}, ensure_ascii=False)


def build_default_skill_registry(
    runtime: Any,
    *,
    observe_read: Optional[Callable[..., Any]] = None,
) -> SkillRegistry:
    """Register built-in CNexus skills against a runtime instance."""
    registry = SkillRegistry()

    def _governance_snapshot() -> Any:
        if observe_read is None:
            raise RuntimeError("get_cognitive_state requires observe_read('governance_state')")
        return observe_read("governance_state")

    registry.register_function(
        "search_long_term_memory",
        "Search CNexus persistent memory and return assembled recall context.",
        {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Recall query"}},
            "required": ["query"],
        },
        lambda query: runtime.recall(query),
    )
    registry.register_function(
        "get_cognitive_state",
        "Return current CNexus governance / narrative / stability state snapshot.",
        {"type": "object", "properties": {}, "required": []},
        lambda: _governance_snapshot(),
    )
    registry.register_function(
        "run_memory_maintenance",
        "Run metabolic + sleep-time memory maintenance cycle.",
        {
            "type": "object",
            "properties": {
                "force": {"type": "boolean", "description": "Force maintenance even if disabled"}
            },
            "required": [],
        },
        lambda force=False: runtime.maintain_memory(force=force),
    )

    return registry
