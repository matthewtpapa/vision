#!/usr/bin/env python3
"""Compute a deterministic hash for canonical evaluation artifacts."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

_CANONICAL_PATHS = [
    "bench/oracle_stats.json",
    "bench/oracle_e2e.json",
    "artifacts/config_precedence.json",
    "artifacts/purity_report.json",
]


def _read_existing_bytes(paths: list[str]) -> bytes:
    chunks: list[bytes] = []
    for rel_path in paths:
        path = Path(rel_path)
        if path.exists():
            chunks.append(path.read_bytes())
    return b"".join(chunks)


def main() -> None:
    payload = _read_existing_bytes(_CANONICAL_PATHS)
    digest = hashlib.sha256(payload).hexdigest()
    os.makedirs("artifacts", exist_ok=True)
    out_path = Path("artifacts/metrics_hash.txt")
    out_path.write_text(f"metrics_hash: {digest}\n", encoding="utf-8")
    print(f"metrics_hash: {digest}")


if __name__ == "__main__":
    main()
