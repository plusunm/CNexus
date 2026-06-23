"""Minimal STUN binding client for server-reflexive (srflx) candidate discovery."""

from __future__ import annotations

import os
import random
import socket
import struct
import time
from typing import Dict, List, Optional, Tuple


# RFC 5389 binding request / success response (no auth, no attrs beyond XOR-MAPPED-ADDRESS)
_STUN_MAGIC = 0x2112A442
_STUN_BINDING_REQUEST = 0x0001
_STUN_BINDING_SUCCESS = 0x0101
_ATTR_XOR_MAPPED_ADDRESS = 0x0020


def _default_stun_servers() -> List[Tuple[str, int]]:
    raw = os.environ.get("CNEXUS_STUN_SERVERS", "stun.l.google.com:19302")
    servers: List[Tuple[str, int]] = []
    for part in str(raw or "").split(","):
        part = part.strip()
        if not part:
            continue
        if ":" in part:
            host, port_s = part.rsplit(":", 1)
            try:
                servers.append((host.strip(), int(port_s)))
            except ValueError:
                continue
        else:
            servers.append((part, 19302))
    return servers or [("stun.l.google.com", 19302)]


def _xor_mapped_address(data: bytes, transaction_id: bytes) -> Optional[Tuple[str, int]]:
    offset = 0
    while offset + 4 <= len(data):
        attr_type, attr_len = struct.unpack("!HH", data[offset : offset + 4])
        offset += 4
        value = data[offset : offset + attr_len]
        offset += attr_len + (attr_len % 4 and (4 - attr_len % 4) or 0)
        if attr_type != _ATTR_XOR_MAPPED_ADDRESS or len(value) < 8:
            continue
        _family = value[1]
        xport = struct.unpack("!H", value[2:4])[0] ^ (struct.unpack("!H", _STUN_MAGIC.to_bytes(4, "big")[:2])[0])
        xaddr = struct.unpack("!I", value[4:8])[0] ^ struct.unpack("!I", _STUN_MAGIC.to_bytes(4, "big"))[0]
        ip = socket.inet_ntoa(struct.pack("!I", xaddr))
        return ip, xport
    return None


def stun_binding_request(
    server: Tuple[str, int],
    *,
    timeout: float = 2.5,
) -> Dict[str, object]:
    """Send STUN Binding Request; return mapped public endpoint if successful."""
    transaction_id = random.randbytes(12)
    header = struct.pack("!HHI", _STUN_BINDING_REQUEST, 0, _STUN_MAGIC) + transaction_id
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    try:
        sock.sendto(header, server)
        data, _addr = sock.recvfrom(2048)
    except OSError as exc:
        return {"ok": False, "error": str(exc), "server": server}
    finally:
        sock.close()

    if len(data) < 20:
        return {"ok": False, "error": "short_response", "server": server}
    msg_type, msg_len, magic = struct.unpack("!HHI", data[:8])
    if magic != _STUN_MAGIC or msg_type != _STUN_BINDING_SUCCESS:
        return {"ok": False, "error": "unexpected_stun_response", "server": server}
    body = data[20 : 20 + msg_len]
    mapped = _xor_mapped_address(body, transaction_id)
    if not mapped:
        return {"ok": False, "error": "no_mapped_address", "server": server}
    ip, port = mapped
    return {
        "ok": True,
        "ip": ip,
        "port": port,
        "server": server,
        "nat_hint": "srflx",
        "at": time.time(),
    }


def gather_srflx_candidate(*, timeout: float = 2.5) -> Optional[Dict[str, object]]:
    servers = _default_stun_servers()
    random.shuffle(servers)
    for server in servers[:4]:
        result = stun_binding_request(server, timeout=timeout)
        if result.get("ok"):
            return result
    return None
