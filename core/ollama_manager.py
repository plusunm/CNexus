"""Ollama install detection, reachability probe, and local start/stop helpers."""



from __future__ import annotations



import logging

import os

import shutil

import subprocess

import sys

import time

import urllib.error

import urllib.request

from pathlib import Path

from typing import Any, Dict, Optional



logger = logging.getLogger(__name__)



OLLAMA_DOWNLOAD_URL = "https://ollama.com/download"

DEFAULT_HOST = "http://127.0.0.1:11434"

_NO_PROXY_VALUE = "localhost,127.0.0.1,::1"


def _ensure_local_no_proxy() -> None:
    """Keep urllib/requests from routing loopback through HTTP_PROXY."""
    for key in ("NO_PROXY", "no_proxy"):
        current = os.environ.get(key, "")
        parts = [p.strip() for p in current.split(",") if p.strip()]
        for required in _NO_PROXY_VALUE.split(","):
            if required not in parts:
                parts.append(required)
        os.environ[key] = ",".join(parts)


_ensure_local_no_proxy()


def resolve_ollama_host() -> str:
    return _normalize_host(os.environ.get("OLLAMA_HOST", DEFAULT_HOST))

_spawned_process: Optional[subprocess.Popen[Any]] = None

_started_externally: bool = False





def _normalize_host(host: str) -> str:

    return host.rstrip("/")





def find_ollama_binary() -> Optional[str]:

    found = shutil.which("ollama")

    if found:

        return found

    if sys.platform == "win32":

        local = os.environ.get("LOCALAPPDATA", "")

        candidates = [

            Path(local) / "Programs" / "Ollama" / "ollama.exe",

            Path(os.environ.get("ProgramFiles", "")) / "Ollama" / "ollama.exe",

        ]

        for candidate in candidates:

            if candidate.is_file():

                return str(candidate)

    return None





def is_ollama_running(host: str | None = None) -> bool:

    resolved = _normalize_host(host or resolve_ollama_host())

    url = f"{resolved}/api/tags"

    try:

        req = urllib.request.Request(url, method="GET")

        with urllib.request.urlopen(req, timeout=2) as resp:

            return resp.status == 200

    except (urllib.error.URLError, TimeoutError, OSError) as exc:

        logger.warning("Ollama probe failed url=%s err=%s", url, exc)

        return False





def get_ollama_status(host: str | None = None) -> Dict[str, Any]:

    resolved = _normalize_host(host or resolve_ollama_host())

    binary = find_ollama_binary()

    running = is_ollama_running(resolved)

    installed = binary is not None or running

    logger.info(
        "ollama status host=%s running=%s OLLAMA_HOST=%s NO_PROXY=%s",
        resolved,
        running,
        os.environ.get("OLLAMA_HOST", ""),
        os.environ.get("NO_PROXY", os.environ.get("no_proxy", "")),
    )

    return {

        "installed": installed,

        "binary_found": binary is not None,

        "running": running,

        "host": resolved,

        "download_url": OLLAMA_DOWNLOAD_URL,

        "binary_path": binary,

    }





def start_ollama(host: str | None = None) -> Dict[str, Any]:

    global _started_externally

    resolved = _normalize_host(host or resolve_ollama_host())



    if is_ollama_running(resolved):

        return {"ok": True, "detail": "already_running", "running": True}



    binary = find_ollama_binary()

    if not binary:

        return {

            "ok": False,

            "detail": "not_installed",

            "download_url": OLLAMA_DOWNLOAD_URL,

            "running": False,

        }



    global _spawned_process

    try:

        from core.windows_subprocess import hidden_subprocess_kwargs, utf8_subprocess_env

        popen_kwargs: Dict[str, Any] = {
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
            "env": utf8_subprocess_env(),
            **hidden_subprocess_kwargs(),
        }
        if sys.platform == "win32":
            # Ollama >=0.30 opens an interactive TUI when launched without args — use serve headlessly.
            detached_process = getattr(subprocess, "DETACHED_PROCESS", 0x0000_0008)
            popen_kwargs["creationflags"] = (
                popen_kwargs.get("creationflags", 0) | detached_process
            )

        _spawned_process = subprocess.Popen([binary, "serve"], **popen_kwargs)
        _started_externally = False



        for _ in range(30):

            time.sleep(0.5)

            if is_ollama_running(resolved):

                return {"ok": True, "detail": "started", "running": True}

        return {"ok": False, "detail": "start_timeout", "running": is_ollama_running(resolved)}

    except Exception as exc:

        logger.exception("Failed to start Ollama")

        return {"ok": False, "detail": str(exc), "running": is_ollama_running(resolved)}





def stop_ollama(host: str | None = None) -> Dict[str, Any]:

    global _spawned_process, _started_externally

    resolved = _normalize_host(host or resolve_ollama_host())



    if not is_ollama_running(resolved):

        return {"ok": True, "detail": "already_stopped", "running": False}



    if _started_externally:

        return {

            "ok": False,

            "detail": "externally_managed",

            "running": True,

        }



    try:

        if _spawned_process and _spawned_process.poll() is None:

            _spawned_process.terminate()

            try:

                _spawned_process.wait(timeout=5)

            except subprocess.TimeoutExpired:

                _spawned_process.kill()

            _spawned_process = None

            time.sleep(0.5)

            running = is_ollama_running(resolved)

            return {

                "ok": not running,

                "detail": "stopped" if not running else "stop_timeout",

                "running": running,

            }



        return {

            "ok": False,

            "detail": "not_managed_by_cnexus",

            "running": True,

        }

    except Exception as exc:

        logger.exception("Failed to stop Ollama")

        return {"ok": False, "detail": str(exc), "running": is_ollama_running(resolved)}

