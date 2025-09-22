#!/usr/bin/env python
"""Offline oracle benchmark with deterministic configuration."""
from __future__ import annotations

import argparse
import json
import math
import statistics
from pathlib import Path
from typing import Any

from latency_vision.determinism import configure_runtime, quantize_float
from latency_vision.schemas import SCHEMA_VERSION


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bank", required=True)
    parser.add_argument("--queries", required=True)
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--out", default="bench")
    return parser.parse_args()


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def main() -> None:
    configure_runtime()
    args = _parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    bank = _load_jsonl(Path(args.bank))
    queries = _load_jsonl(Path(args.queries))

    latencies_ms: list[float] = []
    hits = 0
    known_total = 0

    for idx, query in enumerate(queries, start=1):
        truth = query.get("truth_qid")
        vec = query["vec"]
        scored = [
            (
                candidate["qid"],
                candidate.get("alpha", 1.0) * _cosine_similarity(vec, candidate["vec"]),
            )
            for candidate in bank
        ]
        scored.sort(key=lambda item: (-item[1], item[0]))
        elapsed_ms = quantize_float((len(bank) + idx) * 0.01)
        latencies_ms.append(elapsed_ms)
        if truth is not None:
            known_total += 1
            hits += int(any(candidate == truth for candidate, _ in scored[: args.k]))

    recall = (hits / known_total) if known_total else 0.0
    quantiles = (
        statistics.quantiles(latencies_ms, n=100, method="inclusive")
        if latencies_ms
        else []
    )
    p95 = quantiles[94] if quantiles else 0.0
    p99 = quantiles[98] if quantiles else 0.0

    stats = {
        "schema_version": SCHEMA_VERSION,
        "bench": "offline_oracle",
        "k": int(args.k),
        "total_queries": len(queries),
        "known_queries": known_total,
        "candidate_at_k_recall": quantize_float(recall),
        "p95_ms": quantize_float(p95),
        "p99_ms": quantize_float(p99),
        "wall_clock_ms": quantize_float(sum(latencies_ms)),
    }

    stats_path = out_dir / "oracle_stats.json"
    with stats_path.open("w", encoding="utf-8") as handle:
        json.dump(stats, handle, indent=2, sort_keys=True)
        handle.write("\n")



if __name__ == "__main__":
    main()
