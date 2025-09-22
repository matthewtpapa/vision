#!/usr/bin/env python
"""Emit supply-chain artifacts and enforce policy."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ARTIFACTS = Path(__file__).resolve().parent.parent / "artifacts"
ALLOWED_LICENSES = {
    "MIT",
    "BSD-2-Clause",
    "BSD-3-Clause",
    "Apache-2.0",
    "ISC",
    "PSF-2.0",
}
LICENSE_ALIASES = {
    "MIT": "MIT",
    "MIT LICENSE": "MIT",
    "APACHE-2.0": "Apache-2.0",
    "APACHE LICENSE 2.0": "Apache-2.0",
    "APACHE LICENSE, VERSION 2.0": "Apache-2.0",
    "APACHE SOFTWARE LICENSE": "Apache-2.0",
    "BSD-2-CLAUSE": "BSD-2-Clause",
    "BSD 2-CLAUSE": "BSD-2-Clause",
    "BSD-3-CLAUSE": "BSD-3-Clause",
    "BSD 3-CLAUSE": "BSD-3-Clause",
    "BSD LICENSE": "BSD-3-Clause",
    "ISC": "ISC",
    "ISC LICENSE": "ISC",
    "PSF": "PSF-2.0",
    "PYTHON SOFTWARE FOUNDATION LICENSE": "PSF-2.0",
    "PSF LICENSE": "PSF-2.0",
}


class SupplyChainError(RuntimeError):
    """Raised when supply-chain policy fails."""


def _run_module(module: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: PLW1510
        [sys.executable, "-m", module, *args],
        check=True,
        capture_output=True,
        text=True,
    )


def _write_text(path: Path, content: str) -> None:
    if not content.endswith("\n"):
        content += "\n"
    path.write_text(content, encoding="utf-8")


def _ensure_sbom() -> None:
    destination = ARTIFACTS / "sbom.json"
    try:
        result = _run_module("cyclonedx_py", "-e")
    except (subprocess.CalledProcessError, FileNotFoundError):
        result = _run_module("pipdeptree", "--json-tree")
    _write_text(destination, result.stdout)


def _normalize_token(token: str) -> str | None:
    cleaned = re.sub(r"[()]+", " ", token).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    if not cleaned:
        return None
    key = cleaned.upper()
    normalized = LICENSE_ALIASES.get(key)
    if normalized:
        return normalized
    for allowed in ALLOWED_LICENSES:
        if allowed.upper() in key:
            return allowed
    return cleaned


def _extract_license_names(raw_value: str) -> set[str]:
    if not raw_value:
        return {"UNKNOWN"}
    parts = re.split(r"\s*(?:,|;|/|\bor\b|\band\b|\+|\|)\s*", raw_value, flags=re.IGNORECASE)
    normalized: set[str] = set()
    for part in parts:
        token = _normalize_token(part)
        if token:
            normalized.add(token)
    if not normalized:
        normalized.add("UNKNOWN")
    return normalized


def _collect_licenses() -> None:
    result = _run_module("piplicenses", "--format=json")
    data = json.loads(result.stdout)
    if not isinstance(data, list):  # pragma: no cover - sanity guard
        raise SupplyChainError("pip-licenses returned unexpected payload")
    destination = ARTIFACTS / "licenses.json"
    destination.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    violations: list[str] = []
    for entry in data:
        if not isinstance(entry, dict):  # pragma: no cover - sanity guard
            continue
        name = str(entry.get("Name", "unknown"))
        raw_license = str(entry.get("License", ""))
        normalized = _extract_license_names(raw_license)
        if not normalized.issubset(ALLOWED_LICENSES):
            violations.append(f"{name}: {raw_license or 'UNKNOWN'}")
    if violations:
        raise SupplyChainError("Disallowed licenses detected: " + ", ".join(sorted(violations)))


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _collect_wheel_hashes() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        temp_path = Path(tmp)
        freeze_output = _run_module("pip", "freeze").stdout
        requirements: list[str] = []
        for line in freeze_output.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("-e "):
                continue
            if stripped.startswith("#"):
                continue
            if "@ file://" in stripped or " @ " in stripped:
                continue
            requirements.append(stripped)
        requirements_file = temp_path / "requirements.txt"
        requirements_content = "\n".join(requirements)
        if requirements:
            requirements_content += "\n"
        requirements_file.write_text(requirements_content, encoding="utf-8")
        if requirements:
            subprocess.run(  # noqa: PLW1510
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "download",
                    "--only-binary",
                    ":all:",
                    "--dest",
                    str(temp_path),
                    "--requirement",
                    str(requirements_file),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
        wheel_lines: list[str] = []
        for wheel in sorted(temp_path.glob("*.whl")):
            wheel_lines.append(f"{wheel.name}  sha256:{_hash_file(wheel)}")
        (ARTIFACTS / "wheels_hashes.txt").write_text(
            "\n".join(wheel_lines) + "\n",
            encoding="utf-8",
        )


def main() -> None:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    _ensure_sbom()
    try:
        _collect_licenses()
    except SupplyChainError as error:
        print(error, file=sys.stderr)
        raise SystemExit(1) from error
    _collect_wheel_hashes()
    print("supply-chain ok")


if __name__ == "__main__":
    main()
