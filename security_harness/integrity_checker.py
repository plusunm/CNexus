"""Read-only environment integrity checks for protection verification."""

from __future__ import annotations

import re
import socket
from dataclasses import dataclass, field
from pathlib import Path

# System DLL names commonly abused for sideloading / hooking.
COMMON_SIDELOAD_NAMES = frozenset({
    "version.dll",
    "winhttp.dll",
    "wininet.dll",
    "dbghelp.dll",
    "ws2_32.dll",
})

# api-ms-win-*.dll belong under System32; never in a desktop app folder.
API_MS_PATTERN = re.compile(r"^api-ms-win-.*\.dll$", re.IGNORECASE)

# PE section names associated with Microsoft Detours / hook frameworks.
DETOUR_SECTION_MARKERS = (b".detourc", b".detourd")


@dataclass
class IntegrityReport:
    ok: bool
    issues: list[dict[str, str]] = field(default_factory=list)

    def add(self, code: str, detail: str, *, critical: bool = False) -> None:
        self.issues.append({"code": code, "detail": detail, "critical": str(critical)})
        if critical:
            self.ok = False


def read_hosts_file() -> str:
    hosts = Path(r"C:\Windows\System32\drivers\etc\hosts")
    if not hosts.is_file():
        return ""
    return hosts.read_text(encoding="utf-8", errors="ignore")


def check_hosts_poison(domains: list[str]) -> list[dict[str, str]]:
    content = read_hosts_file().lower()
    hits: list[dict[str, str]] = []
    for domain in domains:
        d = domain.lower()
        for prefix in ("0.0.0.0", "127.0.0.1"):
            needle = f"{prefix} {d}"
            if needle in content:
                hits.append({"code": "hosts_poisoned", "detail": needle})
    return hits


def check_listening_ports(ports: list[int], host: str = "127.0.0.1") -> list[dict[str, str]]:
    hits: list[dict[str, str]] = []
    for port in ports:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.2)
            if sock.connect_ex((host, port)) == 0:
                hits.append({"code": "local_listener", "detail": f"{host}:{port}"})
    return hits


def has_detour_sections(path: Path) -> bool:
    try:
        data = path.read_bytes()[: 1024 * 512]
    except OSError:
        return False
    return any(marker in data for marker in DETOUR_SECTION_MARKERS)


def scan_app_directory_sideloads(app_dir: Path) -> list[dict[str, str]]:
    """Detect non-system DLLs placed beside the app executable."""
    hits: list[dict[str, str]] = []
    if not app_dir.is_dir():
        return hits

    for entry in app_dir.iterdir():
        if not entry.is_file():
            continue
        name = entry.name.lower()
        if not name.endswith(".dll"):
            continue

        if API_MS_PATTERN.match(name):
            hits.append({
                "code": "api_ms_sideload",
                "detail": f"{entry} (api-ms DLL must not live in app directory)",
            })
            continue

        if name in COMMON_SIDELOAD_NAMES:
            hits.append({"code": "dll_sideload", "detail": str(entry)})
            continue

        if has_detour_sections(entry):
            hits.append({"code": "detours_section", "detail": str(entry)})

    return hits


def run_integrity_checks(
    *,
    protected_domains: list[str] | None = None,
    suspicious_ports: list[int] | None = None,
    app_dir: Path | None = None,
    suspicious_dll_names: list[str] | None = None,
) -> IntegrityReport:
    report = IntegrityReport(ok=True)

    for hit in check_hosts_poison(protected_domains or []):
        report.add(hit["code"], hit["detail"], critical=True)

    for hit in check_listening_ports(suspicious_ports or []):
        report.add(hit["code"], hit["detail"], critical=False)

    if app_dir:
        for hit in scan_app_directory_sideloads(app_dir):
            report.add(hit["code"], hit["detail"], critical=True)

        if suspicious_dll_names:
            for name in suspicious_dll_names:
                dll = app_dir / name
                if dll.is_file():
                    report.add("dll_sideload", str(dll), critical=True)

    return report
