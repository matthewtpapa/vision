#!/usr/bin/env python3
from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOT = ROOT / "docs" / "Vision_v1_Investor_SoT.html"
STAGES = ROOT / "docs" / "specs" / "stages"


def normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\xa0", " ").replace("**", " ")).strip()


def extract_acceptance(markdown: str) -> str:
    lines = markdown.splitlines()
    collected: list[str] = []
    in_block = False
    for line in lines:
        stripped = line.strip()
        if stripped == "## Acceptance (CI-verified)":
            in_block = True
            continue
        if in_block:
            if line.startswith("## "):
                break
            if stripped.startswith("- "):
                collected.append(stripped[2:])
                continue
            if (line.startswith("  ") or line.startswith("\t")) and collected:
                collected[-1] += " " + stripped
                continue
            if not stripped:
                continue
            break
    return normalize(" ".join(collected))


class TableGrab(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_table = False
        self.in_tr = False
        self.in_cell = False
        self.current_id: str | None = None
        self.current_cell: list[str] = []
        self.current_row: list[str] = []
        self.rows: dict[str, list[str]] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "table":
            self.in_table = True
        elif self.in_table and tag == "tr":
            self.in_tr = True
            self.current_id = None
            self.current_row = []
            for key, value in attrs:
                if key == "id" and value:
                    self.current_id = value
        elif self.in_tr and tag in {"td", "th"}:
            self.in_cell = True
            self.current_cell = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "table":
            self.in_table = False
        elif self.in_table and tag == "tr":
            if self.current_id and self.current_row:
                self.rows[self.current_id] = self.current_row
            self.in_tr = False
            self.current_id = None
        elif self.in_tr and tag in {"td", "th"}:
            if self.in_cell:
                self.current_row.append("".join(self.current_cell).strip())
            self.in_cell = False

    def handle_data(self, data: str) -> None:
        if self.in_cell:
            self.current_cell.append(data)


def main() -> None:
    html = SOT.read_text(encoding="utf-8")
    parser = TableGrab()
    parser.feed(html)
    updated = html
    for md_path in sorted(STAGES.glob("S*.md")):
        stage_id = md_path.stem
        if stage_id not in parser.rows:
            continue
        spec_text = extract_acceptance(md_path.read_text(encoding="utf-8"))
        row = parser.rows[stage_id]
        if len(row) < 3:
            continue
        current = normalize(row[2])
        if current == spec_text:
            continue

        pattern = re.compile(
            rf'(<tr[^>]*id="{stage_id}"[^>]*>.*?<td>.*?</td>.*?<td>.*?</td>.*?<td>)(.*?)(</td>)',
            flags=re.S,
        )

        def repl(match: re.Match[str]) -> str:
            return f"{match.group(1)}{spec_text}{match.group(3)}"

        updated, count = pattern.subn(repl, updated, count=1)
        if count == 0:
            continue
    if updated != html:
        SOT.write_text(updated, encoding="utf-8")
    print("sot_acceptance_sync=1")


if __name__ == "__main__":
    main()
