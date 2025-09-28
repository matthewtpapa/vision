#!/usr/bin/env python3
"""Generate roadmap.lock.json using tracked files and stage artifacts."""

from __future__ import annotations

import hashlib
import json
import subprocess
import traceback
from collections.abc import Iterable
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ROADMAP_PATH = REPO_ROOT / "roadmap.yaml"
LOCK_PATH = REPO_ROOT / "roadmap.lock.json"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _iter_tracked_files() -> Iterable[str]:
    out = subprocess.check_output(["git", "ls-files", "-z"], cwd=REPO_ROOT)
    for entry in out.decode().split("\x00"):
        if not entry:
            continue
        if entry == "roadmap.lock.json":
            continue
        if entry.startswith("logs/"):
            continue
        if entry.startswith(".venv"):
            continue
        if entry.startswith("artifacts/") and not entry.endswith(".schema.json"):
            continue
        yield entry


def _parse_roadmap(path: Path) -> dict[str, object]:
    """Parse roadmap.yaml without third-party dependencies.

    The CI environment that consumes this script is intentionally stdlib-only,
    so we implement a small YAML subset reader instead of depending on PyYAML.
    The roadmap checker exercises the same parser to ensure coverage.
    """
    schema_version: str | None = None
    stages: list[dict[str, object]] = []
    current: dict[str, object] | None = None
    active_list: list[str] | None = None
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            if not raw_line.strip():
                continue
            if raw_line.startswith("#"):
                continue
            line = raw_line.rstrip("\n")
            if not line.startswith(" "):
                key, _, value = line.partition(":")
                key = key.strip()
                value = value.strip().strip('"')
                if key == "schema_version":
                    schema_version = value
                continue
            if line.startswith("  - "):
                rest = line[4:]
                key, _, value = rest.partition(":")
                current = {key.strip(): value.strip().strip('"')}
                stages.append(current)
                active_list = None
                continue
            if current is None:
                continue
            if line.startswith("    "):
                stripped = line[4:]
                inner = stripped.lstrip()
                if inner.startswith("-"):
                    if active_list is None:
                        raise ValueError("list entry encountered without active list")
                    item = inner[1:].strip().strip('"')
                    active_list.append(item)
                    continue
                key, _, value = stripped.partition(":")
                key = key.strip()
                value = value.strip()
                if value:
                    current[key] = value.strip('"')
                    active_list = None
                else:
                    target: list[str] = []
                    current[key] = target
                    active_list = target
    if schema_version is None:
        raise ValueError("schema_version missing from roadmap")
    return {"schema_version": schema_version, "stages": stages}


def _compute_fileset_sha() -> str:
    digest = hashlib.sha256()
    for path in sorted(_iter_tracked_files()):
        full = REPO_ROOT / path
        digest.update(path.encode("utf-8"))
        digest.update(_sha256_file(full).encode("utf-8"))
    return digest.hexdigest()


def _compute_stage_hash(stage: dict[str, object]) -> tuple[list[str], str]:
    artifacts = stage.get("artifacts")
    if not isinstance(artifacts, list):
        return [], hashlib.sha256(b"").hexdigest()
    existing: list[str] = []
    payload = bytearray()
    for entry in artifacts:
        artifact = str(entry)
        full = REPO_ROOT / artifact
        if not full.exists():
            continue
        existing.append(artifact)
        if artifact == "roadmap.lock.json":
            continue
        digest = _sha256_file(full)
        payload.extend(artifact.encode("utf-8"))
        payload.extend(b"\n")
        payload.extend(digest.encode("utf-8"))
    return existing, hashlib.sha256(payload).hexdigest()


def main() -> int:
    roadmap = _parse_roadmap(ROADMAP_PATH)
    fileset_sha = _compute_fileset_sha()
    stage_entries: list[dict[str, object]] = []
    for stage in roadmap["stages"]:
        if not isinstance(stage, dict):
            continue
        stage_id = str(stage.get("id"))
        existing_artifacts, artifact_digest = _compute_stage_hash(stage)
        stage_entries.append(
            {
                "id": stage_id,
                "artifacts": existing_artifacts,
                "artifact_sha256": artifact_digest,
            }
        )
    payload = {
        "schema_version": "1.2.0",
        "fileset_sha256": fileset_sha,
        "stages": stage_entries,
    }
    LOCK_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception:
        traceback.print_exc()
        raise SystemExit(1)

