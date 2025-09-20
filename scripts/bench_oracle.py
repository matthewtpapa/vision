#!/usr/bin/env python
import argparse
import hashlib
import json
import math
import os
import statistics
import time


def cosine_similarity(a: list[float], b: list[float]) -> float:
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return sum(x * y for x, y in zip(a, b)) / (norm_a * norm_b)


ap = argparse.ArgumentParser()
ap.add_argument("--bank", required=True)
ap.add_argument("--queries", required=True)
ap.add_argument("--k", type=int, default=5)
ap.add_argument("--out", default="bench")
a = ap.parse_args()

os.makedirs(a.out, exist_ok=True)

with open(a.bank) as bank_file:
    bank = [json.loads(line) for line in bank_file]

latencies_ms = []
hits = 0
total = 0

with open(a.queries) as queries_file:
    for line in queries_file:
        query = json.loads(line)
        total += 1
        start = time.perf_counter()
        scored = [
            (item["qid"], item.get("alpha", 1.0) * cosine_similarity(query["vec"], item["vec"]))
            for item in bank
        ]
        scored.sort(key=lambda item: (-item[1], item[0]))
        candidates = [qid for qid, _ in scored[: a.k]]
        latency = (time.perf_counter() - start) * 1000.0
        latencies_ms.append(latency)
        hits += int(query["qid"] in candidates)

stats = {
    "candidate_at_k_recall": hits / total if total else 0.0,
    "p95_ms": statistics.quantiles(latencies_ms, n=100)[94] if latencies_ms else 0.0,
}

stats_path = os.path.join(a.out, "oracle_stats.json")
hash_path = os.path.join(a.out, "oracle_stats.hash")

with open(stats_path, "w") as stats_file:
    json.dump(stats, stats_file, indent=2)
    stats_file.write("\n")

with open(hash_path, "w") as hash_file:
    digest = hashlib.sha256(json.dumps(stats, sort_keys=True).encode()).hexdigest()
    hash_file.write(digest + "\n")
