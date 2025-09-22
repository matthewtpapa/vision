#!/usr/bin/env python
# SPDX-License-Identifier: Apache-2.0
"""Supply-chain guardrail: SBOM, licenses, and wheel hashes."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ART = Path("artifacts")
ART.mkdir(exist_ok=True)

ALLOW = {"Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "MIT", "PSF-2.0"}


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


def licenses() -> list[dict]:
    """Capture license metadata for all installed packages."""

    out = run([sys.executable, "-m", "piplicenses", "--format=json"]).stdout
    data: list[dict] = json.loads(out)
    write(ART / "licenses.json", json.dumps(data, indent=2, sort_keys=True))
    return data


def enforce_allowlist(rows: list[dict]) -> None:
    bad: list[tuple[str, str]] = []
    for row in rows:
        license_name = (row.get("License") or "").strip()
        name = row.get("Name") or row.get("name") or "UNKNOWN"
        if license_name not in ALLOW:
            bad.append((str(name), license_name))
    if bad:
        msg = "Disallowed licenses:\n" + "\n".join(
            f"  {name}: {license_name or 'Unknown'}" for name, license_name in bad
        )
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
