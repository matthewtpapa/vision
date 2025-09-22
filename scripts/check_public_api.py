#!/usr/bin/env python
# SPDX-License-Identifier: Apache-2.0
"""Check the public API surface against a golden snapshot."""

from __future__ import annotations

import difflib
import importlib
from pathlib import Path
from typing import Iterable

MODULES = [
    "latency_vision",
    "latency_vision.calibration",
    "latency_vision.determinism",
    "latency_vision.schemas",
    "latency_vision.slo",
    "latency_vision.telemetry",
    "latency_vision.evaluator",
]


def _public_symbols(module_name: str) -> list[str]:
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as exc:  # pragma: no cover - dependency guard
        missing = exc.name or "unknown"
        raise RuntimeError(
            f"failed to import {module_name}; missing dependency: {missing}"
        ) from exc
    if hasattr(module, "__all__"):
        names = [str(name) for name in getattr(module, "__all__")]
    else:
        names = [name for name in dir(module) if not name.startswith("_")]
    return sorted(set(names))


def _collect_entries(modules: Iterable[str]) -> list[str]:
    entries: list[str] = []
    for module_name in modules:
        for symbol in _public_symbols(module_name):
            entries.append(f"{module_name}:{symbol}")
    return sorted(entries)


def _load_golden(path: Path) -> list[str]:
    return sorted(
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    )


def _write_golden(path: Path, entries: list[str]) -> None:
    path.write_text("\n".join(entries) + "\n", encoding="utf-8")


def main() -> int:
    golden_path = Path(__file__).resolve().parent / "public_api_golden.txt"
    entries = _collect_entries(MODULES)
    if not golden_path.exists():
        _write_golden(golden_path, entries)
        print(f"Wrote new public API golden with {len(entries)} entries → {golden_path}")
        return 0

    golden_entries = _load_golden(golden_path)
    if entries != golden_entries:
        diff = "\n".join(
            difflib.unified_diff(
                golden_entries,
                entries,
                fromfile="golden",
                tofile="current",
                lineterm="",
            )
        )
        print("Public API drift detected:")
        print(diff)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
