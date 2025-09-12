#!/usr/bin/env python3
"""Calibrate verification thresholds from a gallery manifest."""

from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict
from collections.abc import Sequence
from datetime import UTC, datetime


def _quantile(values: Sequence[float], q: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    if len(s) == 1:
        return float(s[0])
    k = (len(s) - 1) * q
    f = int(k)
    c = min(f + 1, len(s) - 1)
    if f == c:
        return float(s[f])
    return float(s[f] * (c - k) + s[c] * (k - f))


def calibrate(manifest_path: str, out_path: str, seed: int) -> None:
    with open(manifest_path, encoding="utf-8") as fh:
        rows = [json.loads(line) for line in fh if line.strip()]

    counts: dict[str, int] = defaultdict(int)
    sources: dict[str, set[str]] = defaultdict(set)
    for r in rows:
        lab = r["label"]
        counts[lab] += 1
        sources[lab].add(r["source"])

    r_vals = list(counts.values())
    diversity_vals = [len(s) for s in sources.values()]
    deltas: list[float] = []
    for lab, r in counts.items():
        others = [c for lab_other, c in counts.items() if lab_other != lab]
        deltas.append(float(r - (max(others) if others else 0)))
    E_vals = [float(r) for r in r_vals]

    out = {
        "E_q": {
            "p5": _quantile(E_vals, 0.05),
            "p50": _quantile(E_vals, 0.5),
            "p95": _quantile(E_vals, 0.95),
        },
        "Δ_q": {
            "p5": _quantile(deltas, 0.05),
            "p50": _quantile(deltas, 0.5),
            "p95": _quantile(deltas, 0.95),
        },
        "r_q": {
            "p5": _quantile(r_vals, 0.05),
            "p50": _quantile(r_vals, 0.5),
            "p95": _quantile(r_vals, 0.95),
        },
        "diversity_min": min(diversity_vals) if diversity_vals else 0,
        "sprt": {"accept": _quantile(r_vals, 0.5), "reject": 0.0},
        "seed": seed,
        "created_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2)


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Calibrate VerifyWorker thresholds")
    p.add_argument("--manifest", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--seed", required=True, type=int)
    args = p.parse_args(argv)
    calibrate(args.manifest, args.out, args.seed)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
