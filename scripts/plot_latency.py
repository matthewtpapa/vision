#!/usr/bin/env python3
"""Plot per-frame latency from a stage timings CSV."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path


def _parse_ns(value: str | None) -> float | None:
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def read_latencies(csv_path: Path) -> list[float]:
    try:
        with csv_path.open(newline="") as fh:
            reader = csv.DictReader(fh)
            latencies_ms: list[float] = []
            for row in reader:
                total = _parse_ns(row.get("total_ns"))
                if total is not None:
                    latencies_ms.append(total / 1_000_000)
                    continue
                subtotal = 0.0
                found = False
                for key, value in row.items():
                    if key.endswith("_ns") and key not in {"monotonic_ns", "ts_ns"}:
                        ns = _parse_ns(value)
                        if ns is not None:
                            subtotal += ns
                            found = True
                if found:
                    latencies_ms.append(subtotal / 1_000_000)
            return latencies_ms
    except FileNotFoundError:
        print(f"CSV not found: {csv_path}", file=sys.stderr)
        sys.exit(2)
    except OSError as err:
        print(str(err), file=sys.stderr)
        sys.exit(2)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path, help="path to stage_timings.csv")
    parser.add_argument("--output", type=Path, help="output PNG path")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ModuleNotFoundError:  # pragma: no cover - explicit exit
        print("Missing dependency: matplotlib", file=sys.stderr)
        sys.exit(3)
    latencies = read_latencies(args.input)
    if not latencies:
        print("No latency data found", file=sys.stderr)
        sys.exit(2)
    output = args.output or args.input.with_name("latency.png")
    plt.figure()
    plt.plot(range(len(latencies)), latencies)
    plt.xlabel("frame")
    plt.ylabel("latency (ms)")
    plt.tight_layout()
    plt.savefig(output)
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
