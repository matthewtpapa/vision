# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 The Vision Authors
from __future__ import annotations

from latency_vision import __version__
from latency_vision.cli import main


def test_version_prints_package_version(capsys):
    assert main(["--version"]) == 0
    captured = capsys.readouterr()
    assert captured.out.strip() == __version__


def test_webcam_command_supports_dry_run(capsys):
    assert main(["webcam", "--dry-run"]) == 0
    captured = capsys.readouterr()
    assert captured.out.strip() == "Dry run: webcam loop skipped"


def test_webcam_fake_detector_dry_run_includes_labeler(capsys):
    assert main(["webcam", "--use-fake-detector", "--dry-run"]) == 0
    out = capsys.readouterr().out.strip()
    assert out == (
        "Dry run: fake detector produced 1 boxes, tracker assigned IDs, "
        "embedder produced 1 embeddings, cluster store prepared 1 exemplar, "
        "matcher compared embeddings (stub), labeler assigned 'unknown'"
    )
