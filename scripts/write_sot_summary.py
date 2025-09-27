#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts"
DOCS = ROOT / "docs"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def maybe_txt(path: Path) -> str | None:
    return path.read_text(encoding="utf-8").strip() if path.exists() else None


def main() -> None:
    ART.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "1.0",
        "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "repo": os.getenv("GITHUB_REPOSITORY"),
        "commit": os.getenv("GITHUB_SHA"),
        "run_id": os.getenv("GITHUB_RUN_ID"),
        "files": {
            "docs/Vision_v1_Investor_SoT.html": {
                "sha256": sha256(DOCS / "Vision_v1_Investor_SoT.html")
            },
            "artifacts/vision_v1_SoT.pdf": {"sha256": sha256(ART / "vision_v1_SoT.pdf")},
            "roadmap.lock.json": {"sha256": sha256(ROOT / "roadmap.lock.json")},
        },
        "metrics_hash": maybe_txt(ART / "metrics_hash.txt"),
        "purity": json.loads((ART / "purity_report.json").read_text(encoding="utf-8")),
        "gate_summary": maybe_txt(ROOT / "gate_summary.txt"),
    }
    (ART / "sot_summary.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print("sot_summary_ok=1")


if __name__ == "__main__":
    main()
