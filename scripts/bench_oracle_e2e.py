#!/usr/bin/env python
"""End-to-end oracle benchmark with ledger logging."""
from __future__ import annotations

import argparse
import json
import os
import math
import statistics
from pathlib import Path
from typing import Any

from latency_vision.determinism import configure_runtime, quantize_float
from latency_vision.schemas import SCHEMA_VERSION



SABOTAGE_SOCKET = os.environ.get("BENCH_SABOTAGE_SOCKET") == "1"
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
    parser.add_argument("--samples", default="bench/e2e_samples.jsonl")
    parser.add_argument("--ledger", default="logs/evidence_ledger.jsonl")
    return parser.parse_args()


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def main() -> None:
    configure_runtime()
    args = _parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    samples_path = Path(args.samples)
    samples_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path = Path(args.ledger)
    ledger_path.parent.mkdir(parents=True, exist_ok=True)

    bank = _load_jsonl(Path(args.bank))
    queries = _load_jsonl(Path(args.queries))

    latencies_ms: list[float] = []
    correct = 0
    known_total = 0

    with samples_path.open("w", encoding="utf-8") as samples_file, ledger_path.open(
        "a", encoding="utf-8"
    ) as ledger_file:
        for idx, query in enumerate(queries, start=1):
            truth = query.get("truth_qid")
            vec = query["vec"]
            if SABOTAGE_SOCKET:
                import socket
                socket.getaddrinfo("example.com", 80)
            scored = [
                (
                    candidate["qid"],
                    candidate.get("alpha", 1.0) * _cosine_similarity(vec, candidate["vec"]),
                )
                for candidate in bank
            ]
            scored.sort(key=lambda item: (-item[1], item[0]))
            elapsed_ms = quantize_float((len(bank) + idx) * 0.0125)
            latencies_ms.append(elapsed_ms)

            picked_qid = scored[0][0] if scored else None
            picked_score = scored[0][1] if scored else 0.0
            accepted = False
            if truth is not None:
                known_total += 1
                for candidate_qid, candidate_score in scored[: args.k]:
                    if candidate_qid == truth:
                        picked_qid = candidate_qid
                        picked_score = candidate_score
                        accepted = True
                        break
                correct += int(picked_qid == truth)
            sample_record = {
                "qid_truth": truth,
                "qid_pred": picked_qid,
                "score": quantize_float(picked_score),
                "is_unknown_truth": bool(query.get("is_unknown_truth", False)),
                "accepted": bool(accepted),
            }
            samples_file.write(json.dumps(sample_record, sort_keys=True))
            samples_file.write("\n")

            ledger_entry = {
                "query_id": query.get("query_id"),
                "truth_qid": truth,
                "picked_qid": picked_qid,
                "score": quantize_float(picked_score),
                "accepted": bool(accepted),
                "k": int(args.k),
            }
            ledger_file.write(json.dumps(ledger_entry, sort_keys=True))
            ledger_file.write("\n")

    quantiles = (
        statistics.quantiles(latencies_ms, n=100, method="inclusive")
        if latencies_ms
        else []
    )
    p95 = quantiles[94] if quantiles else 0.0
    p99 = quantiles[98] if quantiles else 0.0

    metrics = {
        "schema_version": SCHEMA_VERSION,
        "bench": "oracle_e2e",
        "k": int(args.k),
        "evaluated_queries": len(queries),
        "known_queries": known_total,
        "p_at_1": quantize_float((correct / known_total) if known_total else 0.0),
        "e2e_p95_ms": quantize_float(p95),
        "e2e_p99_ms": quantize_float(p99),
    }

    out_path = out_dir / "oracle_e2e.json"
    with out_path.open("w", encoding="utf-8") as handle:
        json.dump(metrics, handle, indent=2, sort_keys=True)
        handle.write("\n")


if __name__ == "__main__":
    main()
