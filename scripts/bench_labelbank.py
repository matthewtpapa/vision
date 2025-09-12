#!/usr/bin/env python3
"""Micro-benchmark for LabelBank lookup latency and recall."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
import random
import time
from collections.abc import Sequence

from latency_vision.label_bank import HNSWInt8LabelBank
from latency_vision.telemetry.repro import metrics_hash

SEED_FILE = "data/labelbank/seed.jsonl"


def embed_text(text: str, dim: int, seed: int) -> list[float]:
    h = hashlib.blake2b(text.encode("utf-8"), digest_size=16)
    rnd = random.Random(int.from_bytes(h.digest(), "big") ^ seed)
    vec = [rnd.uniform(-1.0, 1.0) for _ in range(dim)]
    norm = sum(x * x for x in vec) ** 0.5 or 1.0
    return [x / norm for x in vec]


def perturb(label: str, aliases: Sequence[str], rng: random.Random) -> str:
    base = rng.choice([label, *aliases]) if aliases else label
    variants = [
        lambda s: s,
        lambda s: s.upper(),
        lambda s: s.lower(),
    ]
    return rng.choice(variants)(base)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bench LabelBank lookup")
    parser.add_argument("--shard", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--seed", type=int, default=999)
    parser.add_argument("--queries", type=int, default=2000)
    parser.add_argument("--k", type=int, default=10)
    args = parser.parse_args(argv)

    bank = HNSWInt8LabelBank.load(args.shard)
    manifest = json.load(open(os.path.join(args.shard, "manifest.json")))
    embed_seed = manifest["seed"]
    dim = manifest["dim"]

    allow = set(manifest["p31_allow"])
    mapping: dict[str, list[str]] = {}
    with open(SEED_FILE, encoding="utf-8") as fh:
        for line in fh:
            rec = json.loads(line)
            if rec.get("p31") not in allow:
                continue
            label = rec["label"].strip().casefold()
            aliases = [a.strip().casefold() for a in rec.get("aliases", [])]
            mapping[label] = aliases

    labels = list(mapping.keys())
    rng = random.Random(args.seed)

    latencies: list[float] = []
    hits = 0
    for _ in range(args.queries):
        label = rng.choice(labels)
        qtext = perturb(label, mapping[label], rng).casefold().strip()
        vec = embed_text(qtext, dim, embed_seed)
        t0 = time.perf_counter()
        res = bank._lookup_vecs([vec], k=args.k)
        t1 = time.perf_counter()
        latencies.append((t1 - t0) * 1000.0)
        if label in res.labels():
            hits += 1

    latencies.sort()
    idx = max(0, math.ceil(0.95 * len(latencies)) - 1)
    p95 = round(latencies[idx], 2)
    recall = round(hits / args.queries, 4)
    stats = bank.stats()
    total_bytes = stats["bytes_index"] + stats["bytes_vocab"]
    bpk = round(total_bytes / stats["n_items"] * 1000)

    out = {
        "n_total": stats["n_items"],
        "queries": args.queries,
        "k": args.k,
        "lookup_p95_ms": p95,
        "recall_at_10": recall,
        "bytes_index": stats["bytes_index"],
        "bytes_vocab": stats["bytes_vocab"],
        "bytes_per_1k_phrases": bpk,
        "seed": args.seed,
        "created_utc": dt.datetime.utcnow().isoformat() + "Z",
    }
    hash_keys = [
        "n_total",
        "queries",
        "k",
        "lookup_p95_ms",
        "recall_at_10",
        "bytes_index",
        "bytes_vocab",
        "bytes_per_1k_phrases",
        "seed",
    ]
    bench_hash = metrics_hash({k: out[k] for k in hash_keys})
    out["bench_hash"] = bench_hash
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, separators=(",", ":"))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
