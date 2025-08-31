#!/usr/bin/env python3
"""Print a concise summary from a metrics.json file."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ORDER = [
    "fps",
    "p95",
    "p99",
    "frames",
    "processed",
    "backend",
    "kb",
    "sdk",
    "stride",
    "window_p95",
]

SYNONYMS = {
    "p95": ["p95", "p95_ms"],
    "p99": ["p99", "p99_ms"],
    "window_p95": ["window_p95", "window_p95_ms"],
}


def load_metrics(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        print(f"Metrics file not found: {path}", file=sys.stderr)
        sys.exit(2)
    except json.JSONDecodeError as err:
        print(f"Invalid JSON: {err}", file=sys.stderr)
        sys.exit(2)
    except OSError as err:
        print(str(err), file=sys.stderr)
        sys.exit(2)


def collect_fields(data: dict[str, Any]) -> dict[str, Any]:
    scopes = [
        data,
        data.get("summary"),
        data.get("latency"),
        data.get("percentiles"),
        data.get("counts"),
        data.get("env"),
        data.get("config"),
    ]
    out: dict[str, Any] = {}
    for key in ORDER:
        names = SYNONYMS.get(key, [key])
        for scope in scopes:
            if not isinstance(scope, dict):
                continue
            for name in names:
                if name in scope:
                    out[key] = scope[name]
                    break
            if key in out:
                break
    return out


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metrics", required=True, type=Path, help="path to metrics.json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data = load_metrics(args.metrics)
    values = collect_fields(data)
    parts = [f"{k}={values[k]}" for k in ORDER if k in values]
    print(" ".join(parts))


if __name__ == "__main__":
    main()
