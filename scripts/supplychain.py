#!/usr/bin/env python
"""Deterministic supply-chain stub that emits static artifacts."""
from __future__ import annotations

import json
from pathlib import Path

from latency_vision.schemas import SCHEMA_VERSION

ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS = ROOT / "artifacts"


def _read_project_version() -> str:
    pyproject = ROOT / "pyproject.toml"
    if not pyproject.exists():
        return "0.0.0"
    try:
        import tomllib  # Python 3.11+
    except Exception:  # pragma: no cover - tomllib missing
        return "0.0.0"
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    project = data.get("project", {})
    version = project.get("version")
    return str(version) if version is not None else "0.0.0"


def main() -> None:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    version = _read_project_version()

    sbom = {
        "schema_version": SCHEMA_VERSION,
        "package": {
            "name": "latency-vision",
            "version": version,
        },
        "contents": [],
    }
    (ARTIFACTS / "sbom.json").write_text(json.dumps(sbom, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    licenses = {
        "schema_version": SCHEMA_VERSION,
        "notices": [
            {
                "name": "latency-vision",
                "license": "Apache-2.0",
                "version": version,
            }
        ],
    }
    (ARTIFACTS / "licenses.json").write_text(
        json.dumps(licenses, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    wheels = [
        {
            "name": "latency-vision",
            "version": version,
            "sha256": "0" * 64,
        }
    ]
    wheel_lines = [
        f"{entry['name']}=={entry['version']} sha256={entry['sha256']}" for entry in wheels
    ]
    (ARTIFACTS / "wheels_hashes.txt").write_text("\n".join(wheel_lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
