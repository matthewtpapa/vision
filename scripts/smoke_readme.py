#!/usr/bin/env python3
"""Verify README schema snippet matches docs/schema.md."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
SCHEMA = ROOT / "docs" / "schema.md"


def main() -> int:
    readme = README.read_text(encoding="utf-8")
    m = re.search(r"```json\s*(\{.*?\})\s*```", readme, flags=re.DOTALL)
    if not m:
        sys.stderr.write("README JSON block missing\n")
        return 1
    snippet = m.group(1).strip()
    schema = SCHEMA.read_text(encoding="utf-8").strip()
    if snippet != schema:
        sys.stderr.write("README schema mismatch\n")
        return 1
    print("README schema OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
