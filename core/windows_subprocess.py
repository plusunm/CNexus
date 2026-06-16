"""Windows helpers for spawning console tools without flashing a CMD window."""

from __future__ import annotations

import os
import subprocess
import sys
from typing import Any, Dict, Iterable, List, Sequence

CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0x0800_0000)
SW_HIDE = 0


def hidden_subprocess_kwargs(*, include_encoding: bool = True) -> Dict[str, Any]:
    """Keyword args for subprocess.run / Popen on Windows (no-op elsewhere)."""
    kwargs: Dict[str, Any] = {}
    if include_encoding:
        kwargs["encoding"] = "utf-8"
        kwargs["errors"] = "replace"
    if sys.platform != "win32":
        return kwargs
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = SW_HIDE
    kwargs.update(
        {
            "creationflags": CREATE_NO_WINDOW,
            "startupinfo": startupinfo,
        }
    )
    return kwargs


def utf8_subprocess_env(extra: Dict[str, str] | None = None) -> Dict[str, str]:
    """Merge PYTHONIOENCODING/PYTHONUTF8 into a child-process environment."""
    env = dict(os.environ)
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("PYTHONUTF8", "1")
    if extra:
        env.update(extra)
    return env


def run_hidden(
    args: Sequence[str],
    *,
    check: bool = False,
    capture_output: bool = True,
    text: bool = True,
    timeout: float | None = None,
) -> subprocess.CompletedProcess[str]:
    kwargs: Dict[str, Any] = {
        "check": check,
        "capture_output": capture_output,
        "text": text,
    }
    if timeout is not None:
        kwargs["timeout"] = timeout
    kwargs.update(hidden_subprocess_kwargs())
    return subprocess.run(list(args), **kwargs)


def check_output_hidden(args: Sequence[str], *, timeout: float | None = None) -> str:
    kwargs: Dict[str, Any] = {"stderr": subprocess.DEVNULL}
    if timeout is not None:
        kwargs["timeout"] = timeout
    kwargs.update(hidden_subprocess_kwargs())
    out = subprocess.check_output(list(args), **kwargs)
    return out.decode("utf-8", errors="replace") if isinstance(out, bytes) else str(out)


def pids_listening_on_port(port: int) -> List[int]:
    if sys.platform == "win32":
        return _pids_listening_on_port_windows(port)
    return _pids_listening_on_port_posix(port)


def _pids_listening_on_port_windows(port: int) -> List[int]:
    try:
        out = check_output_hidden(["netstat", "-ano", "-p", "tcp"], timeout=5)
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return []
    token = f":{port}"
    pids: List[int] = []
    seen: set[int] = set()
    for line in out.splitlines():
        upper = line.upper()
        if "LISTENING" not in upper or token not in line:
            continue
        parts = line.split()
        if len(parts) < 5:
            continue
        pid_raw = parts[-1]
        if not pid_raw.isdigit():
            continue
        pid = int(pid_raw)
        if pid > 0 and pid not in seen:
            seen.add(pid)
            pids.append(pid)
    return pids


def _pids_listening_on_port_posix(port: int) -> List[int]:
    try:
        out = subprocess.check_output(["lsof", "-ti", f":{port}"], text=True, timeout=5).strip()
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return []
    pids: List[int] = []
    for pid_raw in out.splitlines():
        pid_raw = pid_raw.strip()
        if pid_raw.isdigit():
            pids.append(int(pid_raw))
    return pids


def kill_pid_tree(pid: int) -> None:
    if pid <= 0:
        return
    if sys.platform == "win32":
        run_hidden(["taskkill", "/F", "/T", "/PID", str(pid)], check=False)
        return
    run_hidden(["kill", "-9", str(pid)], check=False)


def kill_port_listeners(port: int, *, exclude_pids: Iterable[int] | None = None) -> List[int]:
    excluded = {int(p) for p in (exclude_pids or []) if int(p) > 0}
    killed: List[int] = []
    for pid in pids_listening_on_port(port):
        if pid in excluded:
            continue
        kill_pid_tree(pid)
        killed.append(pid)
    return killed
