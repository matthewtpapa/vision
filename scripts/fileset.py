#!/usr/bin/env python3
"""Produce a canonical manifest and lock file describing the repository fileset."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]


def _iter_files() -> Iterable[str]:
    out = subprocess.check_output(["git", "ls-files", "-z"], cwd=REPO_ROOT)
    paths = [entry for entry in out.decode().split("\x00") if entry]
    filtered = [
        path
        for path in paths
        if not (
            path.startswith("artifacts/")
            or path.startswith("bench/")
            or path.endswith(".pyc")
            or "/__pycache__/" in path
        )
    ]
    return sorted(filtered)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _record(path: str) -> dict[str, object]:
    full_path = REPO_ROOT / path
    stat_result = full_path.stat()
    return {
        "path": path,
        "mode": stat_result.st_mode & 0o777,
        "bytes": stat_result.st_size,
        "sha256": _sha256_file(full_path),
    }


def main() -> None:
    file_paths = list(_iter_files())
    records = [_record(path) for path in file_paths]

    catalog = hashlib.sha256()
    for record in records:
        catalog.update(record["path"].encode())
        catalog.update(str(record["mode"]).encode())
        catalog.update(str(record["bytes"]).encode())
        catalog.update(record["sha256"].encode())

    bundle = {"files": records, "fileset_sha256": catalog.hexdigest()}
    artifacts_dir = REPO_ROOT / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    (artifacts_dir / "manifest.json").write_text(
        json.dumps(bundle, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    (REPO_ROOT / "roadmap.lock.json").write_text(
        json.dumps({"fileset_sha256": bundle["fileset_sha256"]}, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )

    print(bundle["fileset_sha256"])


if __name__ == "__main__":
    main()
