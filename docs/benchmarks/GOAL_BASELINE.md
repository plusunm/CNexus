# Goal Layer Baseline

Generated: 2026-06-12T10:52:38.730224+00:00

## Scope

- Goal capture → intent block JSON integrity
- GoalManager mount on capture hot path
- Governance cycle `goal_layer` observation
- BeliefMeta boundary (Belief/Reflection only)
- Goal vs stale episodic recall influence

## Pytest

```
....................                                                     [100%]
20 passed in 254.43s (0:04:14)
```

Exit code: 0

## v1 Boundary

| In scope | Out of scope (full Mind) |
|----------|--------------------------|
| IntentEngine + GoalManager on capture | Automatic BeliefMeta on every capture |
| Recall intent context + goal ranking boost | Full narrative/working_self sync |
| Governance cycle read-only goal snapshot | Background goal mutation in governance |
