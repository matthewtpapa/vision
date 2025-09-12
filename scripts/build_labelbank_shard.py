#!/usr/bin/env python3
"""Build a deterministic LabelBank shard from seed data."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import random
from collections import defaultdict
from collections.abc import Sequence

from latency_vision.label_bank import HNSWInt8LabelBank


def embed_text(text: str, dim: int, seed: int) -> list[float]:
    h = hashlib.blake2b(text.encode("utf-8"), digest_size=16)
    rnd = random.Random(int.from_bytes(h.digest(), "big") ^ seed)
    vec = [rnd.uniform(-1.0, 1.0) for _ in range(dim)]
    norm = sum(x * x for x in vec) ** 0.5 or 1.0
    return [x / norm for x in vec]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build LabelBank shard")
    parser.add_argument("--seed", type=int, default=1234)
    parser.add_argument("--in", dest="in_path", default="data/labelbank/seed.jsonl")
    parser.add_argument("--out", dest="out_path", required=True)
    parser.add_argument("--dim", type=int, default=256)
    parser.add_argument(
        "--max-n",
        type=int,
        default=int(os.environ.get("LB_N", 10000)),
        help="maximum phrases to index",
    )
    parser.add_argument(
        "--p31-allow",
        default="product_model,product_line",
        help="comma-separated p31 tags to allow",
    )
    args = parser.parse_args(argv)

    allow = {p.strip() for p in args.p31_allow.split(",") if p.strip()}
    phrases: list[list[float]] = []
    labels: list[str] = []
    seen: set[str] = set()
    lang_counts: dict[str, int] = defaultdict(int)

    with open(args.in_path, encoding="utf-8") as fh:
        for line in fh:
            rec = json.loads(line)
            if rec.get("p31") not in allow:
                continue
            lang = rec.get("lang", "und")
            lang_counts[lang] += 1
            canonical = rec["label"].strip().casefold()
            alias_list = [a.strip().casefold() for a in rec.get("aliases", [])]
            for phrase in [canonical, *alias_list]:
                if phrase and phrase not in seen:
                    seen.add(phrase)
                    phrases.append(embed_text(phrase, args.dim, args.seed))
                    labels.append(canonical)
                    if len(phrases) >= args.max_n:
                        break
            if len(phrases) >= args.max_n:
                break

    bank = HNSWInt8LabelBank(dim=args.dim, seed=args.seed)
    bank.add(labels, phrases)
    os.makedirs(args.out_path, exist_ok=True)
    bank.save(args.out_path)
    stats = bank.stats()

    manifest = {
        "n_total": len(labels),
        "dim": args.dim,
        "seed": args.seed,
        "p31_allow": sorted(allow),
        "lang_counts": dict(lang_counts),
        "created_utc": dt.datetime.utcnow().isoformat() + "Z",
        "bytes_index": stats["bytes_index"],
        "bytes_vocab": stats["bytes_vocab"],
    }
    with open(os.path.join(args.out_path, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, separators=(",", ":"))

    print(
        f"built shard n_total={manifest['n_total']} dim={args.dim} "
        f"bytes_index={manifest['bytes_index']} bytes_vocab={manifest['bytes_vocab']}"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
