from core.governance.safety.constitution import CognitiveConstitution
from core.governance.safety.write_gate import MemoryWriteGate


class GovernancePolicyEngine:
    """治理策略引擎"""

    def __init__(self):
        self.write_gate = MemoryWriteGate()
        self.constitution = CognitiveConstitution()

    def approve_memory_write(self, memory) -> bool:
        return self.write_gate.validate(memory)[0]

    def approve_personality_mutation(self, proposed, current) -> bool:
        return self.constitution.validate_mutation(proposed, current)
