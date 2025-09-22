#!/usr/bin/env python
"""Emit deterministic supply-chain artifacts for the prove pipeline."""

from __future__ import annotations

import hashlib
import json
from importlib import metadata
from pathlib import Path

from latency_vision.schemas import SCHEMA_VERSION

ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS = ROOT / "artifacts"


def _normalize_name(name: str) -> str:
    return name.replace("_", "-").lower()


def _iter_distributions() -> list[metadata.Distribution]:
    unique: dict[str, metadata.Distribution] = {}
    for dist in metadata.distributions():
        name = dist.metadata.get("Name")
        if not name:
            continue
        key = _normalize_name(str(name))
        unique.setdefault(key, dist)
    return [unique[key] for key in sorted(unique)]


def _extract_license(dist: metadata.Distribution) -> str:
    meta = dist.metadata
    license_field = (meta.get("License") or "").strip()
    if license_field and license_field.upper() != "UNKNOWN":
        return license_field
    classifiers = meta.get_all("Classifier", []) or []
    for classifier in classifiers:
        if classifier.startswith("License ::"):
            candidate = classifier.split("::")[-1].strip()
            if candidate:
                return candidate
    return "UNKNOWN"


def _extract_homepage(dist: metadata.Distribution) -> str:
    return (dist.metadata.get("Home-page") or "").strip()


def _hash_file(path: Path) -> bytes:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.digest()


def _hash_distribution(dist: metadata.Distribution) -> str:
    digest = hashlib.sha256()
    files = dist.files or []
    for file in sorted(files, key=lambda item: str(item)):
        resolved = Path(dist.locate_file(file))
        digest.update(str(file).encode("utf-8"))
        digest.update(b"\0")
        if resolved.is_file():
            digest.update(_hash_file(resolved))
    return digest.hexdigest()


def _collect_requirements(dist: metadata.Distribution) -> list[str]:
    requires = dist.requires or []
    return sorted(str(req) for req in requires)


def main() -> None:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    distributions = _iter_distributions()

    packages: list[dict[str, object]] = []
    notices: list[dict[str, object]] = []
    wheel_lines: list[str] = []

    for dist in distributions:
        raw_name = (
            dist.metadata.get("Name")
            or dist.metadata.get("Summary")
            or dist.metadata.get("Metadata-Version")
            or "package"
        )
        name = str(raw_name)
        version = str(dist.version)
        license_name = _extract_license(dist)
        homepage = _extract_homepage(dist)
        requires = _collect_requirements(dist)
        packages.append(
            {
                "name": name,
                "version": version,
                "license": license_name,
                "homepage": homepage,
                "requires": requires,
            }
        )
        notices.append(
            {
                "name": name,
                "version": version,
                "license": license_name,
                "homepage": homepage,
            }
        )
        wheel_lines.append(f"{name}=={version} sha256={_hash_distribution(dist)}")

    sbom = {
        "schema_version": SCHEMA_VERSION,
        "packages": packages,
    }
    (ARTIFACTS / "sbom.json").write_text(
        json.dumps(sbom, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    licenses = {
        "schema_version": SCHEMA_VERSION,
        "notices": notices,
    }
    (ARTIFACTS / "licenses.json").write_text(
        json.dumps(licenses, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    (ARTIFACTS / "wheels_hashes.txt").write_text("\n".join(wheel_lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
