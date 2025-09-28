#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

from canonicalize_pdf import canonicalize_pdf
from reportlab import rl_config
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

rl_config.invariant = 1


def html_to_text(html: str) -> str:
    text = re.sub(r"<!--.*?-->", " ", html, flags=re.S)
    text = re.sub(r"<script\\b.*?</script>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<style\\b.*?</style>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def write_pdf(txt: str, out_path: Path) -> None:
    width, height = letter
    tmp_path = out_path.with_suffix(".tmp.pdf")
    c = canvas.Canvas(str(tmp_path), pagesize=letter, pageCompression=0)

    left = 0.75 * inch
    top = height - 0.75 * inch
    c.setFont("Helvetica", 10)
    max_width = width - 1.5 * inch

    words = txt.split(" ")
    line = []

    def line_width(ws):
        return c.stringWidth(" ".join(ws), "Helvetica", 10)

    y = top
    for w in words:
        candidate = line + [w]
        if line and line_width(candidate) > max_width:
            c.drawString(left, y, " ".join(line))
            y -= 12
            if y < 0.75 * inch:
                c.showPage()
                c.setFont("Helvetica", 10)
                y = top
            line = [w]
        else:
            line = candidate
    if line:
        c.drawString(left, y, " ".join(line))
    c.showPage()
    c.save()

    canonical = canonicalize_pdf(tmp_path if tmp_path.exists() else out_path)
    out_path.write_bytes(canonical)
    try:
        tmp_path.unlink()
    except FileNotFoundError:
        pass


def main() -> None:
    import sys

    if len(sys.argv) != 3:
        print("usage: make_sot_pdf.py <input.html> <output.pdf>", file=sys.stderr)
        sys.exit(2)
    html = Path(sys.argv[1]).read_text(encoding="utf-8")
    text = html_to_text(html)
    write_pdf(text, Path(sys.argv[2]))


if __name__ == "__main__":
    main()
