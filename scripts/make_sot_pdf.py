#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfdoc
from reportlab.pdfgen import canvas

CREATOR = "Vision SoT pipeline"
PRODUCER = "Vision-Deterministic-PDF"
FIXED_DATE = "D:19700101000000Z"


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
    c = canvas.Canvas(str(out_path), pagesize=letter, pageCompression=0)
    c.setCreator(CREATOR)
    c.setProducer(PRODUCER)
    docinfo = c._doc.info
    docinfo.producer = PRODUCER
    docinfo.creator = CREATOR
    docinfo.creationDate = FIXED_DATE
    docinfo.modDate = FIXED_DATE
    c._doc._ID = (b"\x00" * 16, b"\x00" * 16)

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
    cat = c._doc.Catalog
    if isinstance(cat, pdfdoc.PDFDictionary):
        cat.dict.pop("Metadata", None)
    c.save()


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
