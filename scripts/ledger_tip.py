#!/usr/bin/env python3
"""Compute the hash tip for the stage ledger."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


LEDGER_PATH = Path("artifacts/stage_ledger.jsonl")
TIP_PATH = Path("artifacts/ledger_tip.txt")


def _hash_payload(previous: str, record: dict[str, object]) -> str:
    payload = (
        previous
        + str(record.get("stage", ""))
        + str(record.get("event", ""))
        + str(record.get("ts", ""))
        + str(record.get("commit", ""))
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def main() -> None:
    tip = "0" * 64
    with LEDGER_PATH.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            tip = _hash_payload(tip, record)

    TIP_PATH.write_text(tip + "\n", encoding="utf-8")
    print(tip)


if __name__ == "__main__":
    main()
