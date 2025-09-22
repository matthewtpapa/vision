#!/usr/bin/env python
# SPDX-License-Identifier: Apache-2.0
"""Ensure schema changes bump the shared schema version."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

SCHEMA_DIR = Path("schemas")
SCHEMA_SENTINEL = Path("src/latency_vision/schemas.py")
VERSION_PATTERN = re.compile(r"SCHEMA_VERSION\s*=\s*['\"]([^'\"]+)['\"]")


def _git_diff_names(base_ref: str) -> set[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", f"{base_ref}", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}


def _schema_version_at(ref: str) -> str:
    show = subprocess.run(
        ["git", "show", f"{ref}:{SCHEMA_SENTINEL.as_posix()}"],
        check=True,
        capture_output=True,
        text=True,
    )
    match = VERSION_PATTERN.search(show.stdout)
    if not match:
        raise RuntimeError(f"SCHEMA_VERSION not found at {ref}")
    return match.group(1)


def _current_schema_version() -> str:
    match = VERSION_PATTERN.search(SCHEMA_SENTINEL.read_text(encoding="utf-8"))
    if not match:
        raise RuntimeError("SCHEMA_VERSION not found in working tree")
    return match.group(1)


def main() -> int:
    base_ref = os.environ.get("GIT_DIFF_BASE", "HEAD~1")
    changed = _git_diff_names(base_ref)
    schema_changes = {path for path in changed if path.startswith(f"{SCHEMA_DIR.as_posix()}/")}
    if not schema_changes:
        return 0
    if SCHEMA_SENTINEL.as_posix() not in changed:
        print(
            "Schema files changed without updating src/latency_vision/schemas.py"
        )
        return 1
    base_version = _schema_version_at(base_ref)
    current_version = _current_schema_version()
    if base_version == current_version:
        print(
            "Schema files changed but SCHEMA_VERSION was not updated"
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
