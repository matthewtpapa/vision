#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOW = {
    Path("bench/out/metrics.json"),
    Path("bench/out/stage_times.csv"),
    Path("bench/out/latency.png"),
}

LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
IMAGE_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")


def _check_target(base: Path, target: str, missing: list[str]) -> None:
    if target.startswith("http://") or target.startswith("https://"):
        return
    if target.startswith("#") or target.startswith("mailto:"):
        return
    path_part = target.split("#", 1)[0]
    path_part = Path(path_part)
    resolved = (base.parent / path_part).resolve()
    try:
        rel = resolved.relative_to(ROOT)
    except Exception:
        rel = Path("..") / resolved.name
    if rel in ALLOW:
        return
    if not resolved.exists():
        missing.append(f"{base}: {path_part}")


def main() -> int:
    missing: list[str] = []
    for md in ROOT.rglob("*.md"):
        if "node_modules" in md.parts:
            continue
        text = md.read_text(encoding="utf-8")
        for regex in (LINK_RE, IMAGE_RE):
            for match in regex.finditer(text):
                _check_target(md, match.group(1), missing)
    if missing:
        for item in missing:
            print(f"Missing: {item}")
        return 1
    print("Docs links OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
