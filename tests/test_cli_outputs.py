# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 The Vision Authors
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from latency_vision import __version__

ROOT = Path(__file__).resolve().parent.parent
PYTHONPATH = os.pathsep.join([str(ROOT / "src"), os.environ.get("PYTHONPATH", "")])
ENV = {**os.environ, "PYTHONPATH": PYTHONPATH}


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "vision", *args],
        capture_output=True,
        text=True,
        env=ENV,
        check=True,
    )


def test_version_command_reports_version() -> None:
    result = run_cli("--version")
    assert result.stdout.strip() == f"Latency Vision {__version__}"


def test_webcam_dry_run_reports_message() -> None:
    result = run_cli("webcam", "--dry-run")
    assert result.stdout.strip() == "Dry run: webcam loop skipped"


def test_webcam_fake_detector_dry_run_reports_all_steps() -> None:
    result = run_cli("webcam", "--use-fake-detector", "--dry-run")
    assert result.stdout.strip() == (
        "Dry run: fake detector produced 1 boxes, tracker assigned IDs, "
        "embedder produced 1 embeddings, cluster store prepared 1 exemplar, "
        "matcher compared embeddings (stub), labeler assigned 'unknown'"
    )
