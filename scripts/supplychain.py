#!/usr/bin/env python
# SPDX-License-Identifier: Apache-2.0
"""Supply-chain guardrail: SBOM, licenses, and wheel hashes."""

from __future__ import annotations

import hashlib
import importlib.metadata as importlib_metadata
import json
import re
import subprocess
import sys
import tempfile
from collections.abc import Iterable
from pathlib import Path
from typing import Any, NamedTuple

ART = Path("artifacts")
ART.mkdir(exist_ok=True)

ALLOW = {
    "Apache-2.0",
    "BSD-2-Clause",
    "BSD-3-Clause",
    "ISC",
    "MIT",
    "MPL-2.0",
    "PSF-2.0",
    "HPND",
    "Unlicense",
}

EXACT_ALIASES = {
    "apache license 2.0": "Apache-2.0",
    "apache 2.0": "Apache-2.0",
    "apache license, version 2.0": "Apache-2.0",
    "apache software license": "Apache-2.0",
    "apache license version 2.0": "Apache-2.0",
    "apache software license version 2.0": "Apache-2.0",
    "apache software licence": "Apache-2.0",
    "apache software licence version 2.0": "Apache-2.0",
    "apache-2.0": "Apache-2.0",
    "bsd": "BSD-3-Clause",
    "bsd license": "BSD-3-Clause",
    "bsd-2-clause": "BSD-2-Clause",
    "bsd 2-clause": "BSD-2-Clause",
    "bsd-3-clause": "BSD-3-Clause",
    "bsd 3-clause": "BSD-3-Clause",
    "historical permission notice and disclaimer": "HPND",
    "hpnd": "HPND",
    "isc": "ISC",
    "isc license": "ISC",
    "isc license (iscl)": "ISC",
    "mit": "MIT",
    "mit license": "MIT",
    "mozilla public license 2.0": "MPL-2.0",
    "mpl 2.0": "MPL-2.0",
    "mpl-2.0": "MPL-2.0",
    "python software foundation license": "PSF-2.0",
    "python software foundation license (psf-2.0)": "PSF-2.0",
    "psf": "PSF-2.0",
    "psf license": "PSF-2.0",
    "python software foundation": "PSF-2.0",
    "the unlicense": "Unlicense",
    "unlicense": "Unlicense",
}

SUBSTRING_ALIASES = (
    ("apache", "Apache-2.0"),
    ("bsd-2", "BSD-2-Clause"),
    ("bsd 2", "BSD-2-Clause"),
    ("bsd-3", "BSD-3-Clause"),
    ("bsd 3", "BSD-3-Clause"),
    ("bsd", "BSD-3-Clause"),
    ("historical permission notice and disclaimer", "HPND"),
    ("hpnd", "HPND"),
    ("gnu general public license", "GPL"),
    ("gnu lesser general public license", "LGPL"),
    ("isc", "ISC"),
    ("mit", "MIT"),
    ("mozilla public license", "MPL-2.0"),
    ("mpl", "MPL-2.0"),
    ("python software foundation", "PSF-2.0"),
    ("psf", "PSF-2.0"),
    ("unlicense", "Unlicense"),
)

LICENSE_SPLIT_RE = re.compile(r"[\\/,;]|\s+and\s+|\s+or\s+", re.IGNORECASE)


class PackageReport(NamedTuple):
    """Summary of a package's declared and canonical license information."""

    name: str
    version: str
    declared: tuple[str, ...]
    canonical: tuple[str, ...]


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=True, text=True, capture_output=True)


def write(path: Path, data: str) -> None:
    path.write_text(data if data.endswith("\n") else data + "\n", encoding="utf-8")


def sbom() -> None:
    """Emit an SBOM for the current environment."""

    try:
        out = run([sys.executable, "-m", "cyclonedx_py", "-e"]).stdout
    except Exception:
        out = run([sys.executable, "-m", "pipdeptree", "--json-tree"]).stdout
    write(ART / "sbom.json", out)


def _split_licenses(value: str) -> list[str]:
    value = value.replace("(", " ").replace(")", " ")
    parts = [p.strip() for p in LICENSE_SPLIT_RE.split(value) if p.strip()]
    return parts or ([value.strip()] if value.strip() else [])


def _canonicalize(entry: str) -> str | None:
    normalized = re.sub(r"\s+", " ", entry.strip().lower()).replace("licence", "license")
    if not normalized:
        return None
    if normalized in EXACT_ALIASES:
        return EXACT_ALIASES[normalized]
    for needle, alias in SUBSTRING_ALIASES:
        if needle in normalized:
            return alias
    return None


def _distribution_report(dist: importlib_metadata.Distribution) -> PackageReport:
    name = dist.metadata.get("Name") or dist.metadata["Name"]
    declared: set[str] = set()
    license_field = dist.metadata.get("License")
    if license_field:
        declared.update(_split_licenses(license_field))
    for classifier in dist.metadata.get_all("Classifier") or []:
        if not classifier.lower().startswith("license ::"):
            continue
        declared.add(classifier.split("::")[-1].strip())
    canonical: set[str] = {
        alias for item in declared if (alias := _canonicalize(item))
    }
    if not canonical and license_field:
        fallback = _canonicalize(license_field)
        if fallback:
            canonical.add(fallback)
    return PackageReport(
        name=name,
        version=dist.version,
        declared=tuple(sorted(declared)),
        canonical=tuple(sorted(alias for alias in canonical if alias)),
    )


def licenses() -> list[dict[str, Any]]:
    """Capture license metadata for installed packages and normalize it."""

    reports: list[PackageReport] = []
    for dist in importlib_metadata.distributions():
        reports.append(_distribution_report(dist))
    reports.sort(key=lambda item: item.name.lower())
    data = [
        {
            "name": report.name,
            "version": report.version,
            "declared_licenses": list(report.declared),
            "canonical_licenses": list(report.canonical),
        }
        for report in reports
    ]
    write(ART / "licenses.json", json.dumps(data, indent=2, sort_keys=True))
    return data


def enforce_allowlist(rows: Iterable[dict[str, Any]]) -> None:
    bad: list[tuple[str, list[str]]] = []
    for row in rows:
        name = row.get("name") or row.get("Name") or "UNKNOWN"
        canonical = [str(item) for item in row.get("canonical_licenses") or []]
        declared = row.get("declared_licenses") or []
        declared_list = [str(item) for item in declared] if declared else ["Unknown"]
        if not canonical:
            bad.append((str(name), declared_list))
            continue
        disallowed = [lic for lic in canonical if lic not in ALLOW]
        if disallowed:
            bad.append((str(name), disallowed))
    if bad:
        lines = []
        for name, issues in bad:
            issues_text = ", ".join(issues)
            lines.append(f"  {name}: {issues_text or 'Unknown'}")
        msg = "Disallowed licenses:\n" + "\n".join(lines)
        print(msg, file=sys.stderr)
        raise SystemExit(2)


def wheels_hashes() -> None:
    """Download wheels for the environment and produce deterministic hashes."""

    with tempfile.TemporaryDirectory() as tmp:
        req_file = Path(tmp) / "requirements.txt"
        freeze = run([sys.executable, "-m", "pip", "freeze", "--all"]).stdout
        write(req_file, freeze)
        run(
            [
                sys.executable,
                "-m",
                "pip",
                "download",
                "--only-binary",
                ":all:",
                "-r",
                str(req_file),
                "-d",
                tmp,
            ]
        )
        lines: list[str] = []
        directory = Path(tmp)
        for wheel in sorted(directory.iterdir()):
            if wheel.suffix != ".whl":
                continue
            digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
            lines.append(f"{wheel.name}  sha256:{digest}")
        write(ART / "wheels_hashes.txt", "\n".join(lines))


def main() -> int:
    sbom()
    rows = licenses()
    enforce_allowlist(rows)
    wheels_hashes()
    print("supply-chain ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
