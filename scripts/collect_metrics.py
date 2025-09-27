#!/usr/bin/env python
"""Collect bench metrics for determinism runs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from latency_vision.guards import unknowns_false_accept_rate


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _load_samples(path: Path) -> list[dict]:
    samples: list[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if line:
                samples.append(json.loads(line))
    return samples


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bench-dir", default="bench", help="Directory containing bench outputs")
    parser.add_argument("--run-output", required=True, help="Path to write the run metrics JSON")
    parser.add_argument("--summary-output", help="Optional path to write the summary JSON")
    args = parser.parse_args()

    bench_dir = Path(args.bench_dir)
    offline = _load_json(bench_dir / "oracle_stats.json")
    e2e = _load_json(bench_dir / "oracle_e2e.json")
    samples = _load_samples(bench_dir / "e2e_samples.jsonl")

    unknown_rate = unknowns_false_accept_rate(samples)

    run_payload = {
        "offline_oracle": offline,
        "oracle_e2e": e2e,
        "unknowns": {"unknown_false_accept_rate": unknown_rate},
    }
    _write_json(Path(args.run_output), run_payload)

    if args.summary_output:
        summary_payload = {
            "candidate_at_k_recall": offline["candidate_at_k_recall"],
            "p_at_1": e2e["p_at_1"],
            "e2e_p95_ms": e2e["e2e_p95_ms"],
            "unknown_false_accept_rate": unknown_rate,
        }
        _write_json(Path(args.summary_output), summary_payload)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
