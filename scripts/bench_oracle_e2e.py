#!/usr/bin/env python
from __future__ import annotations
import argparse, json, os, time, hashlib, math, statistics, typing as t
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from latency_vision.ledger.json_ledger import JsonLedger


def _cos(u: t.List[float], v: t.List[float]) -> float:
    su = math.sqrt(sum(x * x for x in u))
    sv = math.sqrt(sum(x * x for x in v))
    if su == 0.0 or sv == 0.0:
        return 0.0
    return sum(x * y for x, y in zip(u, v)) / (su * sv)


ap = argparse.ArgumentParser()
ap.add_argument("--bank", required=True)
ap.add_argument("--queries", required=True)
ap.add_argument("--k", type=int, default=5)
ap.add_argument("--out", default="bench")
a = ap.parse_args()

os.makedirs(a.out, exist_ok=True)
os.makedirs("logs", exist_ok=True)

bank = [json.loads(x) for x in open(a.bank)]
ledger = JsonLedger("logs/evidence_ledger.jsonl")

lat_ms: t.List[float] = []
correct = total = 0

for line in open(a.queries):
    q = json.loads(line)
    total += 1
    t0 = time.perf_counter()
    scored = [
        (it["qid"], it.get("alpha", 1.0) * _cos(q["vec"], it["vec"]))
        for it in bank
    ]
    # deterministic ties
    scored.sort(key=lambda t: (-t[1], t[0]))
    candidates = scored[: a.k]
    picked_qid, picked_s = candidates[0]
    accepted = False
    verify_trace: t.List[dict[str, t.Any]] = []
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

json.dump(out, open(f"{a.out}/oracle_e2e.json", "w"), indent=2)
open(f"{a.out}/oracle_e2e.json", "a").write("\n")
open(f"{a.out}/oracle_e2e.hash", "w").write(
    hashlib.sha256(json.dumps(out, sort_keys=True).encode()).hexdigest() + "\n"
)
