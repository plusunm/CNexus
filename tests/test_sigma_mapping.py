"""Layer 1 Σ mapping tests — Runbook evolved bridge."""

from datetime import datetime, timezone

from core.evolved.sigma_mapping import (
    derive_timestamps_from_trace,
    execution_record_to_sigma_trace,
    memory_block_to_sigma_m,
    sigma_m_to_memory_block_patch,
)
from memory.block import MemoryBlock


def test_memory_block_round_trip_sigma_m():
    block = MemoryBlock.from_label("persona", "test persona content", importance=0.9)
    sigma = memory_block_to_sigma_m(block, trace_id="run-1700000000000")
    assert sigma["slot"] == "Σ.M"
    assert sigma["label"] == "persona"
    assert sigma["metadata"]["sigma_slot"] == "Σ.M"
    assert sigma["metadata"]["block_importance_snapshot"] == 0.9
    assert sigma["metadata"]["block_created_at"]

    patch = sigma_m_to_memory_block_patch(sigma)
    assert patch["importance"] == 0.9
    assert patch["metadata"]["sigma_slot"] == "Σ.M"


def test_derive_timestamps_from_trace_millis():
    derived = derive_timestamps_from_trace("evt-1700000000000-abc")
    assert derived["block_created_at"].startswith("2023-")


def test_execution_record_to_sigma_trace():
    record = {
        "trace_id": "t-1",
        "intent_type": "STORE",
        "elapsed_ms": 12.5,
        "identity": "self",
        "audit_log": {"source": "kernel"},
        "state_projection": {"stability_metrics": {"importance_snapshot": 0.77}},
        "derivation": {"execution_tier": "T1"},
    }
    sigma_t = execution_record_to_sigma_trace(record)
    assert sigma_t["slot"] == "Σ.T"
    assert sigma_t["trace_id"] == "t-1"
    assert sigma_t["importance_snapshot"] == 0.77
    assert sigma_t["audit_log"]["source"] == "kernel"
