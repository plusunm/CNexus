"""Ensure a single Runtime API listener — avoid killing healthy CNexus instances."""



from __future__ import annotations



import json

import os

import sys

import time

import urllib.error

import urllib.request



from core.windows_subprocess import kill_port_listeners





def _probe_health(url: str) -> bool:

    try:

        with urllib.request.urlopen(url, timeout=1.5) as resp:

            if resp.status != 200:

                return False

            body = json.loads(resp.read().decode("utf-8", errors="replace"))

    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):

        return False

    service = str(body.get("service") or "").lower()

    if "cnexus" in service:

        return True

    status = str(body.get("status") or "").lower()

    return status in ("ok", "ready", "warming")





def port_has_healthy_cnexus(port: int | None = None) -> bool:

    """True if a healthy CNexus API is already listening."""

    port = int(port or os.environ.get("BM_API_PORT", "8000"))

    for path in ("/health", "/v1/health"):

        if _probe_health(f"http://127.0.0.1:{port}{path}"):

            return True

    return False





def ensure_runtime_port_free(port: int | None = None) -> None:

    """Kill stale listeners on the Runtime port (dev recovery only)."""

    if os.environ.get("CNEXUS_SKIP_PORT_GUARD") == "1":

        return

    port = int(port or os.environ.get("BM_API_PORT", "8000"))

    if port_has_healthy_cnexus(port):

        print(f"[port-guard] :{port} already serving healthy CNexus API — skip kill")

        return

    if sys.platform == "win32":

        _ensure_port_free_windows(port)

    else:

        _ensure_port_free_posix(port)





def _ensure_port_free_windows(port: int) -> None:

    killed = kill_port_listeners(port)

    for pid in killed:

        print(f"[port-guard] kill :{port} pid {pid}")

    time.sleep(0.35)





def _ensure_port_free_posix(port: int) -> None:

    killed = kill_port_listeners(port)

    for pid in killed:

        print(f"[port-guard] kill :{port} pid {pid}")

    time.sleep(0.35)


