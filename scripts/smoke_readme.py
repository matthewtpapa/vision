#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README_PATH = ROOT / "README.md"
SCHEMA_PATH = ROOT / "docs" / "schema.md"
MARKER = "__SMOKE_KEYS__"


def _extract_snippet() -> tuple[str, str]:
    text = README_PATH.read_text(encoding="utf-8")
    m_quick = re.search(r"##\s*Quickstart(.*)", text, flags=re.DOTALL)
    if not m_quick:
        raise RuntimeError("Quickstart section missing")
    quick = m_quick.group(1)
    m_code = re.search(r"```python\s*(.*?)\s*```", quick, flags=re.DOTALL)
    if not m_code:
        raise RuntimeError("Quickstart python block missing")
    snippet = m_code.group(1)
    m_var = re.search(r"(\w+)\s*=\s*query_frame", snippet)
    if not m_var:
        raise RuntimeError("Could not determine result variable")
    return snippet, m_var.group(1)


def main() -> int:
    snippet, var = _extract_snippet()
    with tempfile.TemporaryDirectory() as td:
        code = (
            f"{snippet}\n"
            "import json,sys\n"
            f"print('{MARKER}:' + json.dumps(sorted({var}.keys())))\n"
        )
        proc = subprocess.run(
            [sys.executable, "-"],
            input=code,
            text=True,
            capture_output=True,
            cwd=td,
            env={"PYTHONPATH": str(ROOT / "src")},
        )
    if proc.returncode != 0:
        sys.stderr.write(proc.stdout + proc.stderr)
        return 1
    out_key = None
    for line in proc.stdout.splitlines():
        if line.startswith(MARKER + ":"):
            out_key = line.split(":", 1)[1]
            break
    if out_key is None:
        sys.stderr.write("Result marker not found in snippet output\n")
        return 1
    snippet_keys = json.loads(out_key)
    schema_keys = sorted(json.loads(SCHEMA_PATH.read_text(encoding="utf-8")).keys())
    if snippet_keys != schema_keys:
        sys.stderr.write(
            f"Schema keys mismatch: snippet={snippet_keys} schema={schema_keys}\n"
        )
        return 1
    print("README Quickstart OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
