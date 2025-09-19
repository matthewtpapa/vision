from __future__ import annotations

import json
from pathlib import Path

from scripts.verify_build_manifest import build_manifest
from scripts.verify_calibrate import calibrate


def test_calibration_hash_stable(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    seed = repo_root / "data/verify/seed_gallery/seed.jsonl"
    data_dir = repo_root / "data/verify/seed_gallery"

    manifest = tmp_path / "gallery_manifest.jsonl"
    rows, _ = build_manifest(str(seed), str(data_dir), str(manifest))
    assert rows > 0

    calib_a = tmp_path / "calibration.json"
    calib_b = tmp_path / "calibration_2.json"
    calibrate(str(manifest), str(calib_a), 4242)
    calibrate(str(manifest), str(calib_b), 4242)

    with calib_a.open(encoding="utf-8") as fh:
        data_a = json.load(fh)
    with calib_b.open(encoding="utf-8") as fh:
        data_b = json.load(fh)

    assert data_a["calibration_hash"] == data_b["calibration_hash"]
