#!/usr/bin/env python3
from __future__ import annotations
import sys, re, difflib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = (ROOT / "docs" / "schema.md").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")

def _readme_json_block(text: str) -> str | None:
    m = re.search(r"```json\s*(.*?)\s*```", text, flags=re.DOTALL)
    return m.group(1) if m else None

def main() -> int:
    block = _readme_json_block(README)
    if block is None:
        print("README.md is missing a fenced ```json schema example.", file=sys.stderr)
        return 2
    # Expect schema.md to equal the README fenced block verbatim
    if SCHEMA.strip() != block.strip():
        diff = difflib.unified_diff(
            SCHEMA.splitlines(True), block.splitlines(True),
            fromfile="docs/schema.md", tofile="README.md (json block)"
        )
        sys.stderr.writelines(diff)
        return 2
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
