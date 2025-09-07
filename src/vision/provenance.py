# SPDX-License-Identifier: Apache-2.0
"""Helpers to collect provenance information for metrics."""

from __future__ import annotations

import hashlib
import os
import platform
import subprocess
from collections.abc import Iterable
from pathlib import Path


def _git_commit() -> str:
    """Return the current git commit hash.

    Falls back to the ``GIT_COMMIT`` environment variable if ``git`` is not
    available, otherwise returns ``"unknown"``.
    """

    try:
        out = subprocess.check_output([
            "git",
            "rev-parse",
            "HEAD",
        ])
        return out.decode().strip()
    except Exception:
        return os.getenv("GIT_COMMIT", "unknown")


def _hardware_id() -> str:
    """Return a simple hardware identifier string."""

    return "|".join(
        [platform.system(), platform.machine(), platform.processor()]
    )


def _fixture_hash(frames: Iterable[Path]) -> str:
    """Compute a SHA256 hash of the ordered filenames and bytes in *frames*."""

    h = hashlib.sha256()
    for path in sorted(frames):
        h.update(path.name.encode("utf-8"))
        try:
            h.update(path.read_bytes())
        except OSError:
            continue
    return h.hexdigest()


def collect_provenance(frames: Iterable[Path]) -> dict[str, str]:
    """Collect provenance fields for metrics.json.

    Parameters
    ----------
    frames:
        Iterable of frame ``Path`` objects used in the evaluation fixture.
    """

    paths = list(frames)
    return {
        "git_commit": _git_commit(),
        "hardware_id": _hardware_id(),
        "fixture_hash": _fixture_hash(paths),
    }


__all__ = ["collect_provenance"]
