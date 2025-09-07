#!/usr/bin/env python3
"""Plot per-frame latency from a stage timings CSV."""

from __future__ import annotations

import argparse
import csv
import json
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


def _percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    if len(s) == 1:
        return float(s[0])
    k = (len(s) - 1) * (q / 100.0)
    f = int(k)
    c = min(f + 1, len(s) - 1)
    if f == c:
        return float(s[f])
    d0 = s[f] * (c - k)
    d1 = s[c] * (k - f)
    return float(d0 + d1)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path, help="path to stage_timings.csv")
    parser.add_argument("--output", type=Path, help="output PNG path")
    parser.add_argument("--metrics", type=Path, help="metrics.json for SLO budget", default=None)
    parser.add_argument("--slo-ms", type=float, default=33.0, help="SLO budget in ms")
    return parser.parse_args()


def render_plot(latencies: list[float], budget_ms: float, output: Path):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    trimmed = latencies[100:] if len(latencies) > 100 else []
    p50 = _percentile(trimmed, 50.0)
    p95 = _percentile(trimmed, 95.0)
    p99 = _percentile(trimmed, 99.0)
    slo_pct = (
        sum(1 for x in trimmed if x <= budget_ms) / len(trimmed) * 100
        if trimmed
        else 0.0
    )

    fig, ax = plt.subplots()
    ax.plot(range(len(latencies)), latencies)
    ax.axhline(budget_ms, color="red", linestyle="--")
    ax.set_xlabel("frame")
    ax.set_ylabel("latency (ms)")
    ax.set_title(f"p50={p50:.1f} p95={p95:.1f} p99={p99:.1f}")
    fig.text(
        0.5,
        0.01,
        f"SLO_in_budget={slo_pct:.1f}% warm-up excluded",
        ha="center",
    )
    fig.tight_layout()
    fig.savefig(output)
    return fig


def main() -> None:
    args = parse_args()
    latencies = read_latencies(args.input)
    if not latencies:
        print("No latency data found", file=sys.stderr)
        sys.exit(2)
    budget = args.slo_ms
    if args.metrics and args.metrics.exists():
        try:
            data = json.loads(args.metrics.read_text())
            budget = float(data.get("slo_budget_ms", budget))
        except Exception:
            pass
    output = args.output or args.input.with_name("latency.png")
    render_plot(latencies, budget, output)
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
