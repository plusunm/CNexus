from core.governance.safety.constitution import CognitiveConstitution
from core.governance.safety.write_gate import MemoryWriteGate


class GovernancePolicyDescriptor:
    """Governance policy descriptor — approval gates for runtime (CDG-adjacent)."""

    def __init__(self, *, write_gate_threshold: float = 0.65):
        self.write_gate = MemoryWriteGate(threshold=write_gate_threshold)
        self.constitution = CognitiveConstitution()

    def approve_memory_write(self, memory) -> bool:
        return self.write_gate.validate(memory)[0]

    def approve_personality_mutation(self, proposed, current) -> bool:
        return self.constitution.validate_mutation(proposed, current)


GovernancePolicyEngine = GovernancePolicyDescriptor  # deprecated v1 alias
