#!/usr/bin/env python3
"""Build a deduplicated gallery manifest with deterministic pHash."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections.abc import Sequence


def phash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:16]


def build_manifest(seed_path: str, data_dir: str, out_path: str) -> tuple[int, int]:
    seen: set[tuple[str, str]] = set()
    rows: list[dict[str, str]] = []
    dupes = 0
    with open(seed_path, encoding="utf-8") as fh:
        for line in fh:
            rec = json.loads(line)
            file_path = os.path.join(data_dir, rec["file"])
            with open(file_path, "rb") as f:
                ph = phash_bytes(f.read())
            key = (rec["label"], ph)
            if key in seen:
                dupes += 1
                continue
            seen.add(key)
            rows.append(
                {
                    "source": rec["source"],
                    "path": rec["file"],
                    "license": rec["license"],
                    "phash": ph,
                    "label": rec["label"],
                    "lang": rec["lang"],
                }
            )
    rows.sort(key=lambda r: (r["label"], r["phash"]))
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as out:
        for r in rows:
            out.write(json.dumps(r, ensure_ascii=False) + "\n")
    return len(rows), dupes


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Build gallery manifest")
    p.add_argument("--seed", required=True)
    p.add_argument("--data", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args(argv)
    rows, dupes = build_manifest(args.seed, args.data, args.out)
    print(f"built gallery_manifest rows={rows} dupes_dropped={dupes}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
