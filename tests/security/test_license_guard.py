"""Tests for license_guard grace period and heartbeat degradation."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
BM_UI = ROOT / "brain-memory-ui"
import sys

sys.path.insert(0, str(BM_UI))

from api import license_guard as lg  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_license_env(tmp_path, monkeypatch):
    monkeypatch.setenv("CNEXUS_EDITION", "enterprise")
    monkeypatch.setenv("CNEXUS_DEPLOY_LEVEL", "enterprise")
    monkeypatch.setenv("CNEXUS_LICENSE_SKIP", "0")
    monkeypatch.setenv("CNEXUS_LICENSE_SECRET", "test-secret")
    monkeypatch.setenv("CNEXUS_LICENSE_STATE_FILE", str(tmp_path / "license_state.json"))
    monkeypatch.setenv("CNEXUS_OFFLINE_GRACE_SEC", "3600")
    monkeypatch.setenv("CNEXUS_HEARTBEAT_FAIL_TO_DEGRADED", "3")
    monkeypatch.setenv("CNEXUS_HEARTBEAT_FAIL_TO_LOCKED", "10")

    fp = lg.machine_fingerprint()
    token = lg.issue_license("test-secret", fp)
    monkeypatch.setenv("CNEXUS_LICENSE", token)

    lg._SESSION = lg.LicenseSessionState()
    yield
    lg._SESSION = lg.LicenseSessionState()


def test_verify_license_initializes_grace_until():
    lg.verify_license_or_exit()
    state = lg.get_session_state()
    assert state.grace_until > state.issued_at
    assert lg.get_runtime_mode() == lg.RuntimeMode.TRUSTED


def test_heartbeat_success_resets_fail_count():
    lg.verify_license_or_exit()
    lg.record_heartbeat_failure(reason="NETWORK")
    assert lg.get_session_state().heartbeat_fail_count == 1
    snap = lg.record_heartbeat_success()
    assert snap["heartbeat_fail_count"] == 0
    assert lg.get_runtime_mode() == lg.RuntimeMode.TRUSTED


def test_heartbeat_failure_degrades():
    lg.verify_license_or_exit()
    lg.record_heartbeat_failure()
    lg.record_heartbeat_failure()
    snap = lg.record_heartbeat_failure()
    assert snap["runtime_mode"] == lg.RuntimeMode.DEGRADED.value
    assert "CORE_GTBS" not in lg.granted_features()


def test_heartbeat_failure_locked():
    lg.verify_license_or_exit()
    for _ in range(10):
        lg.record_heartbeat_failure()
    assert lg.get_runtime_mode() == lg.RuntimeMode.LOCKED
    assert lg.license_valid() is False


def test_license_status_payload_shape():
    lg.verify_license_or_exit()
    payload = lg.license_status_payload()
    assert "grace_until" in payload
    assert "granted_features" in payload
    assert payload["license_valid"] is True


def test_require_feature_blocks_gtbs_when_degraded():
    lg.verify_license_or_exit()
    for _ in range(3):
        lg.record_heartbeat_failure()
    with pytest.raises(Exception) as exc:
        lg.require_feature("CORE_GTBS")
    assert "FEATURE_BLOCKED" in str(exc.value)
