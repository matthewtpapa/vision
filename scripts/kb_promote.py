#!/usr/bin/env python
"""Promote knowledge base entries from the evidence ledger."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CUTOFF = 0.5
ROOT = Path(__file__).resolve().parent.parent
LEDGER_PATH = ROOT / "logs" / "evidence_ledger.jsonl"
ARTIFACTS = ROOT / "artifacts"
REPORT_PATH = ARTIFACTS / "promotion_report.json"


def _coerce_score(value: Any) -> float | None:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return None
    if score != score:  # NaN guard
        return None
    return score


def _load_ledger() -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    with LEDGER_PATH.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError as error:  # pragma: no cover - input contract
                raise SystemExit(
                    f"failed to parse ledger line {line_number}: {error.msg}"
                ) from error
            if not isinstance(entry, dict):  # pragma: no cover - schema guard
                raise SystemExit(f"ledger line {line_number} is not an object")
            entries.append(entry)
    return entries


def main() -> None:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)

    if not LEDGER_PATH.exists():
        report = {
            "promotions": [],
            "reasons": [
                {
                    "query_id": None,
                    "reason": "no-ledger",
                }
            ],
        }
        REPORT_PATH.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print("promotions: 0; refusals: 1")
        return

    ledger_rows = _load_ledger()

    promotions: list[dict[str, Any]] = []
    reasons: list[dict[str, Any]] = []

    for row in ledger_rows:
        query_id = row.get("query_id")
        picked_qid = row.get("picked_qid")
        score_value = _coerce_score(row.get("score"))
        if bool(row.get("is_unknown_truth")):
            reasons.append({"query_id": query_id, "reason": "unknown-truth"})
            continue
        if score_value is None or score_value < CUTOFF:
            reasons.append({"query_id": query_id, "reason": "score<0.5"})
            continue
        promotions.append(
            {
                "query_id": query_id,
                "picked_qid": picked_qid,
                "score": score_value,
            }
        )

    report = {"promotions": promotions, "reasons": reasons}
    REPORT_PATH.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"promotions: {len(promotions)}; refusals: {len(reasons)}")


if __name__ == "__main__":
    main()
