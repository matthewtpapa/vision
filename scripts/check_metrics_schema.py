#!/usr/bin/env python
"""Lightweight schema checks for prove artifacts."""
from __future__ import annotations

import json
from pathlib import Path

from latency_vision.schemas import load_schema


def _load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _require_keys(mapping: dict, required: list[str]) -> None:
    missing = [key for key in required if key not in mapping]
    if missing:
        raise SystemExit(f"missing keys: {missing}")


def main() -> None:
    purity = _load_json("artifacts/purity_report.json")
    load_schema("purity_report.schema.json")
    _require_keys(
        purity,
        [
            "sandbox_mode",
            "command",
            "returncode",
            "network_syscalls",
            "offending",
        ],
    )
    print("purity schema ok")


if __name__ == "__main__":
    main()
