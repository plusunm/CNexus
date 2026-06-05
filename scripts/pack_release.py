# -*- coding: utf-8 -*-
"""打包 brain-memory 发布 zip — python scripts/pack_release.py [--skip-memory]"""

from __future__ import annotations

import argparse
import json
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"

INCLUDE = [
    "plugin.json",
    "openclaw.plugin.json",
    "package.json",
    "index.js",
    "rpc_server.py",
    "memory_backend.py",
    "config_loader.py",
    "requirements.txt",
    "README.md",
    "PUBLISH.md",
    "CHANGELOG.md",
    "LICENSE",
    "verify.py",
    "backfill_run.py",
    "config/default.json",
    "brain_skill/SKILL.md",
    "brain_skill/tools.py",
    "scripts/install.bat",
    "scripts/consolidate_task.bat",
    "scripts/run_consolidate.py",
    "scripts/pack_release.py",
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-memory", action="store_true", help="exclude runtime memory/ data")
    args = ap.parse_args()

    manifest = json.loads((ROOT / "plugin.json").read_text(encoding="utf-8"))
    version = manifest.get("version", "0.0.0")
    DIST.mkdir(exist_ok=True)
    out = DIST / f"brain-memory-{version}.zip"

    if out.exists():
        out.unlink()

    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel in INCLUDE:
            p = ROOT / rel
            if p.is_file():
                zf.write(p, f"brain-memory/{rel}")
        if not args.skip_memory:
            mem = ROOT / "memory"
            if mem.exists():
                for fp in mem.rglob("*"):
                    if fp.is_file():
                        zf.write(fp, f"brain-memory/memory/{fp.relative_to(mem).as_posix()}")

    print(f"[OK] {out} ({out.stat().st_size / 1024 / 1024:.2f} MB)")


if __name__ == "__main__":
    main()
