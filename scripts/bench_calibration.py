#!/usr/bin/env python3
"""Run the calibration bench over an offline shard."""

from __future__ import annotations

import argparse
from pathlib import Path

from latency_vision.eval_calibration import evaluate_labelbank_calibration


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bench calibration metrics")
    parser.add_argument("--shard", required=True, help="Path to shard directory")
    parser.add_argument("--seed", type=int, default=999)
    parser.add_argument("--k", type=int, default=10)
    parser.add_argument(
        "--out",
        default="bench/calib_stats.json",
        help="Output JSON path",
    )
    parser.add_argument(
        "--hash-out",
        default="bench/calib_hash.txt",
        help="Where to write the metrics hash",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out_path = Path(args.out)
    report = evaluate_labelbank_calibration(Path(args.shard), args.seed, args.k, out_path)
    hash_path = Path(args.hash_out)
    hash_path.parent.mkdir(parents=True, exist_ok=True)
    hash_path.write_text(str(report["metrics_hash"]) + "\n", encoding="utf-8")
    print(
        f"wrote calibration metrics to {out_path} (hash={report['metrics_hash']})",
        flush=True,
    )
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    raise SystemExit(main())
