#!/usr/bin/env python
# SPDX-License-Identifier: Apache-2.0
"""Promotion sanity gate to prevent junk from landing in KB."""

from __future__ import annotations

import json
from pathlib import Path

LEDGER = Path("logs/evidence_ledger.jsonl")
OUT = Path("artifacts/promotion_report.json")

CUTOFF = 0.5


def main() -> int:
    OUT.parent.mkdir(exist_ok=True)
    promotions: list[dict] = []
    reasons: list[dict] = []

    if not LEDGER.exists():
        OUT.write_text(
            json.dumps({"promotions": [], "reasons": [{"reason": "no-ledger"}]}, indent=2),
            encoding="utf-8",
        )
        print("no ledger; zero promotions")
        return 0

    with LEDGER.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            is_unknown = bool(row.get("is_unknown_truth", False))
            score = float(row.get("score", 0.0))

            if is_unknown:
                reasons.append({"query_id": row.get("query_id"), "reason": "unknown-truth"})
                continue

            if score < CUTOFF:
                reasons.append({"query_id": row.get("query_id"), "reason": f"score<{CUTOFF}"})
                continue

            promotions.append(
                {
                    "query_id": row.get("query_id"),
                    "picked_qid": row.get("picked_qid"),
                    "score": score,
                }
            )

    OUT.write_text(
        json.dumps({"promotions": promotions, "reasons": reasons}, indent=2),
        encoding="utf-8",
    )
    print(f"promotions: {len(promotions)}; refusals: {len(reasons)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
