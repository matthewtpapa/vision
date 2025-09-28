#!/usr/bin/env python
"""Validate the eval fixture manifest for determinism."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from latency_vision.schemas import SCHEMA_VERSION

_PATH_PATTERN = re.compile(r"^(?!/)(?!.*//)(?!.*\\)(?!.*\\.\\.)([A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+$")


def _validate_entry(entry: dict[str, str]) -> Path:
    if set(entry) != {"path", "sha256"}:
        raise SystemExit(f"manifest entry keys must be {{'path','sha256'}}, got {sorted(entry)}")

    raw_path = entry["path"]
    if not isinstance(raw_path, str):
        raise SystemExit("manifest path must be a string")
    if raw_path != raw_path.strip():
        raise SystemExit(f"whitespace forbidden in manifest path: {raw_path!r}")
    if not _PATH_PATTERN.match(raw_path):
        raise SystemExit(f"path must be POSIX-normalized without traversal: {raw_path}")

    rel = Path(raw_path)
    if rel.is_absolute():
        raise SystemExit(f"absolute path forbidden: {rel}")
    if ".." in rel.parts:
        raise SystemExit(f"parent directory traversal forbidden: {rel}")

    full = Path(rel)
    if not full.exists():
        raise SystemExit(f"manifest path missing: {rel}")
    if full.is_symlink():
        raise SystemExit(f"symlink forbidden: {rel}")

    sha_value = entry["sha256"]
    if not isinstance(sha_value, str):
        raise SystemExit("sha256 must be a string")
    if sha_value != sha_value.lower():
        raise SystemExit(f"sha256 must be lowercase: {sha_value}")
    if len(sha_value) != 64 or any(ch not in "0123456789abcdef" for ch in sha_value):
        raise SystemExit(f"sha256 must be 64 hex chars: {sha_value}")

    digest = hashlib.sha256(full.read_bytes()).hexdigest()
    if digest != sha_value:
        raise SystemExit(f"sha256 mismatch for {rel}: {digest} != {sha_value}")

    return full


def validate(path: Path) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit("manifest payload must be an object")
    if data.get("schema_version") != SCHEMA_VERSION:
        raise SystemExit(
            f"manifest schema_version {data.get('schema_version')} != {SCHEMA_VERSION}"
        )

    entries = data.get("entries")
    if not isinstance(entries, list) or not entries:
        raise SystemExit("manifest entries must be a non-empty list")
    if entries != sorted(entries, key=lambda item: item["path"]):
        raise SystemExit("manifest entries must be sorted by path")

    seen: set[Path] = set()
    for raw_entry in entries:
        if not isinstance(raw_entry, dict):
            raise SystemExit("manifest entries must be objects")
        full = _validate_entry(raw_entry)
        if full in seen:
            raise SystemExit(f"duplicate manifest path: {full}")
        seen.add(full)

    actual = {
        candidate
        for candidate in path.parent.glob("*")
        if candidate.name != path.name and candidate.is_file()
    }
    if seen != actual:
        raise SystemExit("manifest entries do not match fixture files")


if __name__ == "__main__":
    validate(Path("data/bench/manifest.json"))
    print("manifest ok")
