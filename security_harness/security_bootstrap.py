"""SecurityBootstrap orchestrator for CNexus protection verification."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from security_harness.feature_gate import FeatureGate, RuntimeMode
from security_harness.integrity_checker import run_integrity_checks

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "brain-memory-ui") not in sys.path:
    sys.path.insert(0, str(ROOT / "brain-memory-ui"))

from api.license_guard import issue_license, machine_fingerprint, verify_license_or_exit  # noqa: E402


@dataclass
class BootstrapResult:
    ok: bool
    runtime_mode: RuntimeMode
    user_message: str
    internal_code: str
    granted_features: list[str] = field(default_factory=list)
    issues: list[dict[str, str]] = field(default_factory=list)


def load_harness_config(path: str | Path | None = None) -> dict[str, Any]:
    cfg_path = Path(path or Path(__file__).with_name("config.json"))
    data = json.loads(cfg_path.read_text(encoding="utf-8"))
    gate_rel = data.get("feature_gate_path", "feature_gate.json")
    data["_feature_gate_path"] = str((cfg_path.parent / gate_rel).resolve())
    return data


def _http_json(url: str, payload: dict[str, Any], timeout: float = 3.0) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def security_bootstrap(
    *,
    config: dict[str, Any] | None = None,
    dry_run: bool = False,
    cfg_only: bool = False,
    edition: str = "enterprise",
    skip_integrity: bool = False,
) -> BootstrapResult:
    cfg = config or load_harness_config()
    gate_path = cfg.get("_feature_gate_path", ROOT / cfg["feature_gate_path"])
    gate = FeatureGate.from_config(gate_path)
    gate.load_edition(edition)

    issues: list[dict[str, str]] = []

    # Phase 1: integrity (read-only)
    if not skip_integrity:
        integrity = run_integrity_checks(
            protected_domains=["api.wxb.com", "wetool.wxb.com", "s.weituibao.com"],
            suspicious_ports=cfg.get("integrity_checks", {}).get("check_listening_ports", []),
            suspicious_dll_names=cfg.get("integrity_checks", {}).get("suspicious_dll_names", []),
        )
        issues.extend(integrity.issues)
        if not integrity.ok:
            gate.set_runtime_mode(RuntimeMode.LOCKED)
            return BootstrapResult(
                ok=False,
                runtime_mode=gate.runtime_mode,
                user_message="检测到异常运行环境，已停止启动。",
                internal_code="E2001",
                issues=issues,
            )

    fingerprint = machine_fingerprint()
    secret = os.environ.get(cfg["staging"]["license_secret_env"], "staging-secret-change-me")

    if cfg_only:
        token = issue_license(secret, fingerprint)
        return BootstrapResult(
            ok=True,
            runtime_mode=RuntimeMode.TRUSTED,
            user_message="已生成测试 license token（仅验证用途）。",
            internal_code="CFG_ONLY",
            granted_features=sorted(gate.granted_features),
            issues=[{"code": "license_token", "detail": token}],
        )

    if dry_run:
        gate.set_runtime_mode(RuntimeMode.TRUSTED)
        return BootstrapResult(
            ok=True,
            runtime_mode=gate.runtime_mode,
            user_message="dry-run 通过：完整性检查与 FeatureGate 初始化成功。",
            internal_code="DRY_RUN_OK",
            granted_features=sorted(gate.granted_features),
            issues=issues,
        )

    # Phase 2: staging auth
    host = cfg["staging"]["host"]
    port = cfg["staging"]["port"]
    auth_url = f"http://{host}:{port}/v1/user/auth"
    try:
        auth = _http_json(
            auth_url,
            {
                "auth_type": "card_key",
                "edition": edition,
                "machine": {"machine_id": fingerprint, "platform": "windows"},
                "client": {"app": "CNexus", "app_version": "1.0.0", "build": 1},
                "nonce": "bootstrap",
                "ts": 1,
            },
        )
    except urllib.error.URLError as exc:
        gate.set_runtime_mode(RuntimeMode.DEGRADED)
        return BootstrapResult(
            ok=False,
            runtime_mode=gate.runtime_mode,
            user_message="无法连接 staging 授权服务，进入受限模式。",
            internal_code="E3001",
            granted_features=[f for f in gate.granted_features if gate.allow(f)],
            issues=issues + [{"code": "auth_unreachable", "detail": str(exc)}],
        )

    if not auth.get("ok"):
        gate.set_runtime_mode(RuntimeMode.LOCKED)
        return BootstrapResult(
            ok=False,
            runtime_mode=gate.runtime_mode,
            user_message="授权失败，请重新激活。",
            internal_code="E5001",
            issues=issues,
        )

    # Phase 3: apply policy
    policy = auth["feature_policy"]
    gate.set_granted_features(policy["granted_features"])
    gate.set_runtime_mode(RuntimeMode(policy.get("runtime_mode", "Trusted")))

    # Phase 4: local license verify simulation
    os.environ.setdefault("CNEXUS_LICENSE_SECRET", secret)
    os.environ["CNEXUS_LICENSE"] = auth["license"]["license_token"]
    os.environ["CNEXUS_DEPLOY_LEVEL"] = "enterprise"
    os.environ["CNEXUS_LICENSE_SKIP"] = "0"
    try:
        verify_license_or_exit()
    except SystemExit as exc:
        gate.set_runtime_mode(RuntimeMode.LOCKED)
        return BootstrapResult(
            ok=False,
            runtime_mode=gate.runtime_mode,
            user_message="本地 license 校验失败。",
            internal_code="E4002",
            issues=issues + [{"code": "license_verify_failed", "detail": str(exc)}],
        )

    granted = [f for f in gate.granted_features if gate.allow(f)]
    return BootstrapResult(
        ok=True,
        runtime_mode=gate.runtime_mode,
        user_message="SecurityBootstrap 验证通过。",
        internal_code="OK",
        granted_features=granted,
        issues=issues,
    )


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="CNexus SecurityBootstrap harness")
    parser.add_argument("--config", default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--cfg-only", action="store_true")
    parser.add_argument("--edition", default="enterprise", choices=["personal", "enterprise"])
    args = parser.parse_args()

    result = security_bootstrap(
        config=load_harness_config(args.config) if args.config else None,
        dry_run=args.dry_run,
        cfg_only=args.cfg_only,
        edition=args.edition,
    )
    print(json.dumps(result.__dict__, default=lambda o: o.value if hasattr(o, "value") else o, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result.ok else 1)


if __name__ == "__main__":
    main()
