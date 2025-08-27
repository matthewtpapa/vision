from __future__ import annotations

from vision.cli import main
from vision import __version__


def test_version_prints_package_version(capsys):
    assert main(["--version"]) == 0
    captured = capsys.readouterr()
    assert captured.out.strip() == f"Vision {__version__}"


def test_webcam_command_supports_dry_run(capsys):
    assert main(["webcam", "--dry-run"]) == 0
    captured = capsys.readouterr()
    assert captured.out.strip() == "Dry run: webcam loop skipped"
