"""Security harness tests for CNexus protection verification."""

from __future__ import annotations

import json
import os
import threading
import time
import urllib.request
from pathlib import Path

import pytest

from security_harness.feature_gate import FeatureGate, RuntimeMode
from security_harness.integrity_checker import check_hosts_poison, scan_app_directory_sideloads
from security_harness.security_bootstrap import load_harness_config, security_bootstrap
from security_harness.staging_auth_server import serve

ROOT = Path(__file__).resolve().parents[2]
GATE_PATH = ROOT / "security_harness" / "feature_gate.json"
HARNESS_DIR = ROOT / "security_harness"


def test_config_json_loads() -> None:
    cfg = load_harness_config(HARNESS_DIR / "config.json")
    assert cfg["product"] == "CNexus"
    assert "heartbeat" in cfg
    assert Path(cfg["_feature_gate_path"]).is_file()


def test_feature_gate_personal_vs_enterprise() -> None:
    gate = FeatureGate.from_config(GATE_PATH)
    gate.load_edition("personal")
    assert gate.allow("CORE_PERSONAL_DEMO")
    assert not gate.allow("CORE_GTBS")

    gate.load_edition("enterprise")
    gate.set_granted_features(gate.edition_defaults["enterprise"])
    assert gate.allow("CORE_GTBS")
    assert gate.allow("CORE_ENTERPRISE_RUNTIME")


def test_feature_gate_heartbeat_degradation() -> None:
    gate = FeatureGate.from_config(GATE_PATH)
    gate.load_edition("enterprise")
    gate.set_granted_features(["CORE_GTBS", "CORE_LOCAL_RUNTIME", "CORE_UI"])

    gate.apply_heartbeat_failure(1, fail_to_degraded=3, fail_to_locked=10)
    assert gate.runtime_mode == RuntimeMode.OFFLINE_GRACE
    assert gate.allow("CORE_LOCAL_RUNTIME")
    assert not gate.allow("CORE_GTBS")

    gate.apply_heartbeat_failure(3, fail_to_degraded=3, fail_to_locked=10)
    assert gate.runtime_mode == RuntimeMode.DEGRADED
    assert gate.allow("CORE_UI")
    assert not gate.allow("CORE_LOCAL_RUNTIME")

    gate.apply_heartbeat_failure(10, fail_to_degraded=3, fail_to_locked=10)
    assert gate.runtime_mode == RuntimeMode.LOCKED
    assert gate.allow("CORE_UI")
    assert not gate.allow("CORE_LOCAL_RUNTIME")


def test_scan_app_directory_flags_api_ms_and_version(tmp_path) -> None:
    app = tmp_path / "app"
    app.mkdir()
    (app / "api-ms-win-core-console-l1-1-0.dll").write_bytes(b"MZ" + b"\x00" * 100)
    (app / "version.dll").write_bytes(b"MZ" + b"\x00" * 100)
    hits = scan_app_directory_sideloads(app)
    codes = {h["code"] for h in hits}
    assert "api_ms_sideload" in codes
    assert "dll_sideload" in codes


def test_hosts_poison_detector() -> None:
    hits = check_hosts_poison(["api.wxb.com"])
    assert isinstance(hits, list)


def test_security_bootstrap_dry_run() -> None:
    result = security_bootstrap(dry_run=True, edition="enterprise", skip_integrity=True)
    assert result.ok
    assert result.internal_code == "DRY_RUN_OK"
    assert "CORE_ENTERPRISE_RUNTIME" in result.granted_features


def test_security_bootstrap_cfg_only() -> None:
    os.environ["CNEXUS_LICENSE_SECRET"] = "unit-test-secret"
    result = security_bootstrap(cfg_only=True, edition="enterprise", skip_integrity=True)
    assert result.ok
    assert result.internal_code == "CFG_ONLY"
    token_issue = next(i for i in result.issues if i["code"] == "license_token")
    assert token_issue["detail"].startswith("CNX1.")


@pytest.fixture(scope="module")
def staging_server():
    secret = "unit-test-secret"
    os.environ["CNEXUS_LICENSE_SECRET"] = secret
    server = serve("127.0.0.1", 0, secret=secret)
    host, port = server.server_address
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.1)
    yield host, port
    server.shutdown()


def test_staging_auth_ping(staging_server) -> None:
    host, port = staging_server
    with urllib.request.urlopen(f"http://{host}:{port}/v1/ping", timeout=2) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    assert data["ok"] is True


def test_security_bootstrap_full_flow(staging_server) -> None:
    host, port = staging_server
    cfg = load_harness_config(HARNESS_DIR / "config.json")
    cfg["staging"]["host"] = host
    cfg["staging"]["port"] = port
    os.environ["CNEXUS_LICENSE_SECRET"] = "unit-test-secret"
    result = security_bootstrap(config=cfg, edition="enterprise", skip_integrity=True)
    assert result.ok
    assert result.internal_code == "OK"
    assert "CORE_ENTERPRISE_RUNTIME" in result.granted_features
