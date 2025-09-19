from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from latency_vision.verify.verify_worker import VerifyWorker


def test_verify_accept_reject(tmp_path: Path) -> None:
    manifest = tmp_path / "gallery_manifest.jsonl"
    calib = tmp_path / "calibration.json"
    subprocess.run(
        [
            sys.executable,
            "scripts/verify_build_manifest.py",
            "--seed",
            "data/verify/seed_gallery/seed.jsonl",
            "--data",
            "data/verify/seed_gallery",
            "--out",
            str(manifest),
        ],
        check=True,
        env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")},
    )
    subprocess.run(
        [
            sys.executable,
            "scripts/verify_calibrate.py",
            "--manifest",
            str(manifest),
            "--out",
            str(calib),
            "--seed",
            "4242",
        ],
        check=True,
        env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")},
    )
    worker = VerifyWorker(str(manifest), str(calib))
    pos = worker.verify([0.0], "alpha")
    neg = worker.verify([0.0], "zulu")
    assert pos.accepted
    assert not neg.accepted
    pos2 = worker.verify([0.0], "alpha")
    assert pos.E == pos2.E
