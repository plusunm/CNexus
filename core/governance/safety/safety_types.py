from datetime import datetime
from typing import Dict, List, Literal

from pydantic import BaseModel, Field


class GovernancePolicy(BaseModel):
    policy_id: str
    rule_type: Literal["write", "mutation", "belief", "ethical"]
    condition: str
    action: Literal["allow", "deny", "review", "rollback"]
    severity: Literal["low", "medium", "high"]
    description: str


class MutationProposal(BaseModel):
    proposal_id: str
    target_type: Literal["dna", "belief", "narrative"]
    changes: Dict
    risk_score: float
    proposed_by: str
    timestamp: datetime


class SafetyAuditRecord(BaseModel):
    audit_id: str
    timestamp: datetime
    event_type: str
    target_id: str
    action: str
    result: Literal["approved", "denied", "reviewed"]
    reason: str
    risk_score: float
