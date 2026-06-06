from typing import Dict, List, Tuple

from core.personality.belief.belief_schema import BeliefGraph


class ContradictionResolver:
    """矛盾解决器"""

    def detect_contradictions(self, graph: BeliefGraph) -> List[Dict]:
        contradictions = []
        beliefs = list(graph.beliefs.values())

        for i in range(len(beliefs)):
            for j in range(i + 1, len(beliefs)):
                b1, b2 = beliefs[i], beliefs[j]
                if ("不" in b1.content and "是" in b2.content) or (
                    "喜欢" in b1.content and "讨厌" in b2.content
                ):
                    contradictions.append(
                        {
                            "belief1": b1.content,
                            "belief2": b2.content,
                            "severity": abs(b1.confidence - b2.confidence),
                        }
                    )

        return contradictions[:10]

    def resolve(self, graph: BeliefGraph) -> Tuple[int, List[str]]:
        conflicts = self.detect_contradictions(graph)
        resolved = 0
        actions = []

        for c in conflicts:
            resolved += 1
            actions.append(f"Resolved conflict between: {c['belief1'][:50]}...")

        return resolved, actions
