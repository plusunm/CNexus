#!/usr/bin/env python3
"""Issue a host-bound CNexus Runtime license (offline — keep CNEXUS_LICENSE_SECRET private)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "brain-memory-ui"))

from api.license_guard import issue_license, machine_fingerprint  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Issue CNexus Runtime license token")
    parser.add_argument("--secret", required=True, help="CNEXUS_LICENSE_SECRET (never commit)")
    parser.add_argument(
        "--fingerprint",
        default=None,
        help="Target machine fingerprint (default: this host)",
    )
    args = parser.parse_args()
    fp = args.fingerprint or machine_fingerprint()
    print(issue_license(args.secret, fp))
    print(f"# fingerprint={fp}", file=sys.stderr)


if __name__ == "__main__":
    main()
