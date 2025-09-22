#!/usr/bin/env python
"""Emit a human-readable summary of gate metrics."""
from __future__ import annotations

import json
from pathlib import Path

GATE_SUMMARY = Path("gate_summary.txt")


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    offline = _load(Path("bench/oracle_stats.json"))
    e2e = _load(Path("bench/oracle_e2e.json"))
    purity = _load(Path("artifacts/purity_report.json"))
    metrics_hash = Path("artifacts/metrics_hash.txt").read_text(encoding="utf-8").strip()

    summary = (
        "recall={recall:.4f} lookup_p95_ms={p95:.4f} p@1={p1:.4f} e2e_p95_ms={ep95:.4f} "
        "purity={purity} hash={digest}"
    ).format(
        recall=float(offline.get("candidate_at_k_recall", 0.0)),
        p95=float(offline.get("p95_ms", 0.0)),
        p1=float(e2e.get("p_at_1") or e2e.get("p@1", 0.0)),
        ep95=float(e2e.get("e2e_p95_ms", 0.0)),
        purity="pass" if not purity.get("offending") else "fail",
        digest=metrics_hash,
    )

    print(summary)
    GATE_SUMMARY.write_text(summary + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
