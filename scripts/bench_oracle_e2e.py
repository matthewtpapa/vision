#!/usr/bin/env python
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import statistics
import sys
import time
from pathlib import Path
from typing import Any


def _ensure_src_on_path() -> None:
    root = Path(__file__).resolve().parent.parent
    src = root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))


def _cos(u: list[float], v: list[float]) -> float:
    su = math.sqrt(sum(x * x for x in u))
    sv = math.sqrt(sum(x * x for x in v))
    if su == 0.0 or sv == 0.0:
        return 0.0
    return sum(x * y for x, y in zip(u, v)) / (su * sv)


def _parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bank", required=True)
    ap.add_argument("--queries", required=True)
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--out", default="bench")
    return ap.parse_args()


def main() -> None:
    args = _parse_args()

    _ensure_src_on_path()
    from latency_vision.ledger.json_ledger import JsonLedger

    os.makedirs(args.out, exist_ok=True)
    os.makedirs("logs", exist_ok=True)

    with open(args.bank) as bank_file:
        bank = [json.loads(line) for line in bank_file]

    ledger = JsonLedger("logs/evidence_ledger.jsonl")

    lat_ms: list[float] = []
    correct = total = 0

    with open(args.queries) as query_file:
        for line in query_file:
            q = json.loads(line)
            total += 1
            t0 = time.perf_counter()
            scored = [(it["qid"], it.get("alpha", 1.0) * _cos(q["vec"], it["vec"])) for it in bank]
            # deterministic ties
            scored.sort(key=lambda item: (-item[1], item[0]))
            candidates = scored[: args.k]
            picked_qid, picked_s = candidates[0]
            accepted = False
            verify_trace: list[dict[str, Any]] = []
            for cand_qid, cand_s in candidates:
                is_match = cand_qid == q["qid"]
                verify_trace.append({"qid": cand_qid, "score": cand_s, "accepted": is_match})
                if is_match:
                    picked_qid, picked_s = cand_qid, cand_s
                    accepted = True
                    break
            lat_ms.append((time.perf_counter() - t0) * 1000.0)
            correct += int(picked_qid == q["qid"])
            ledger.append(
                {
                    "query": q["qid"],
                    "picked": picked_qid,
                    "score": picked_s,
                    "accepted": accepted,
                    "verify_trace": verify_trace,
                }
            )

    # inclusive p95 for stability
    p95 = statistics.quantiles(lat_ms, n=100, method="inclusive")[94] if lat_ms else 0.0
    out = {"p@1": (correct / max(1, total)), "e2e_p95_ms": p95}

    metrics_path = Path(args.out) / "oracle_e2e.json"
    with metrics_path.open("w") as f:
        json.dump(out, f, indent=2)
        f.write("\n")

    hash_path = Path(args.out) / "oracle_e2e.hash"
    with hash_path.open("w") as f:
        f.write(hashlib.sha256(json.dumps(out, sort_keys=True).encode()).hexdigest())
        f.write("\n")


if __name__ == "__main__":
    main()
