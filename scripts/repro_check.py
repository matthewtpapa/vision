#!/usr/bin/env python3
"""Compare two metrics JSON files via deterministic hashing."""

from __future__ import annotations

import argparse
import json
from typing import Any

from latency_vision.telemetry.repro import metrics_hash


def load(path: str) -> Any:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare metrics JSON files")
    parser.add_argument("metrics_a")
    parser.add_argument("metrics_b")
    parser.add_argument("--pretty", action="store_true", help="show differing top-level keys")
    args = parser.parse_args()

    obj_a = load(args.metrics_a)
    obj_b = load(args.metrics_b)

    hash_a = metrics_hash(obj_a)
    hash_b = metrics_hash(obj_b)
    equal = hash_a == hash_b

    print(f"hash_a={hash_a}")
    print(f"hash_b={hash_b}")
    print(f"equal={'true' if equal else 'false'}")

    if args.pretty and not equal:
        keys = set(obj_a.keys()) | set(obj_b.keys())
        for key in sorted(keys):
            if obj_a.get(key) != obj_b.get(key):
                print(f"{key}: {obj_a.get(key)!r} != {obj_b.get(key)!r}")

    return 0 if equal else 1


if __name__ == "__main__":
    raise SystemExit(main())
