"""CSE v1 output contract — structured cognition, not raw logs."""



from __future__ import annotations



from dataclasses import asdict, dataclass, field

from typing import Any, Dict, List





@dataclass

class TextBlock:

    text: str

    confidence: float = 0.7

    source: str = "pattern"



    def to_dict(self) -> Dict[str, Any]:

        return asdict(self)





@dataclass

class InsightBlock:

    title: str

    description: str

    confidence: float = 0.7

    why: str = ""

    source: str = "pattern"

    novelty: float = 0.0

    evidence: List[str] = field(default_factory=list)



    def to_dict(self) -> Dict[str, Any]:

        return asdict(self)





@dataclass

class DiscoveryBlock:

    id: str

    title: str

    description: str

    confidence: float = 0.7

    novelty: float = 0.8

    why: str = ""

    evidence: List[str] = field(default_factory=list)

    source: str = "diff"

    first_seen_at: str = ""



    def to_dict(self) -> Dict[str, Any]:

        return asdict(self)





@dataclass

class ActionBlock:

    action: str

    priority: float

    rationale: str

    category: str = "config"

    impact: float = 0.7

    reversibility: float = 0.8

    why: str = ""



    def to_dict(self) -> Dict[str, Any]:

        return asdict(self)





@dataclass

class CognitiveOutput:

    summary: List[TextBlock] = field(default_factory=list)

    patterns: List[TextBlock] = field(default_factory=list)

    insights: List[InsightBlock] = field(default_factory=list)

    rules: List[TextBlock] = field(default_factory=list)

    experiences: List[TextBlock] = field(default_factory=list)

    discoveries: List[DiscoveryBlock] = field(default_factory=list)

    actions: List[ActionBlock] = field(default_factory=list)

    narrative: str = ""

    generated_at: str = ""

    window_size: int = 0

    mode: str = "live"



    def to_dict(self) -> Dict[str, Any]:

        return {

            "summary": [b.to_dict() for b in self.summary],

            "patterns": [b.to_dict() for b in self.patterns],

            "insights": [b.to_dict() for b in self.insights],

            "rules": [b.to_dict() for b in self.rules],

            "experiences": [b.to_dict() for b in self.experiences],

            "discoveries": [b.to_dict() for b in self.discoveries],

            "actions": [a.to_dict() for a in self.actions],

            "narrative": self.narrative,

            "generated_at": self.generated_at,

            "window_size": self.window_size,

            "mode": self.mode,

        }


