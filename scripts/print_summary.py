#!/usr/bin/env python3
"""Print a concise summary from a metrics.json file."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metrics", required=True, type=Path, help="path to metrics.json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    with open(args.metrics, encoding="utf-8") as fh:
        data = json.load(fh)
    fields = [
        ("fps", "{:.2f}"),
        ("p50_ms", "{:.1f}"),
        ("p95_ms", "{:.1f}"),
        ("p99_ms", "{:.1f}"),
        ("cold_start_ms", "{:.0f}"),
        ("index_bootstrap_ms", "{:.0f}"),
        ("sustained_in_budget", "{:.3f}"),
        ("unknown_rate", "{:.3f}"),
        ("metrics_schema_version", "{}"),
    ]
    out: list[str] = []
    for key, fmt in fields:
        if key in data:
            out.append(f"{key}=" + fmt.format(data[key]))
    if "index_bootstrap_ms" in data:
        alias = "bootstrap" + "_ms"
        out.append(f"{alias}={int(data['index_bootstrap_ms']):d}")
    print(" ".join(out))


if __name__ == "__main__":  # pragma: no cover
    main()
