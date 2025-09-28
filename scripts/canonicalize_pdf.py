#!/usr/bin/env python3
"""Canonicalize PDF outputs for deterministic hashing.

This helper rewrites an input PDF using ``pypdf`` so that the document's
metadata, document identifiers, and optional XMP payloads become deterministic.
The rewritten bytes are returned to the caller and can also be written to disk
via the CLI wrapper.

The module is intentionally dependency-light (``pypdf`` only) so the verify
workflow can import it during the SoT PDF determinism gate.
"""

from __future__ import annotations

import argparse
import io
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.generic import (
    ArrayObject,
    ByteStringObject,
    DictionaryObject,
    NameObject,
    TextStringObject,
)

_CANONICAL_PRODUCER = "Vision-Deterministic-PDF"
_CANONICAL_CREATOR = "Vision SoT pipeline"
_CANONICAL_DATE = "D:19700101000000Z"


def canonicalize_pdf(source: Path) -> bytes:
    """Return deterministic PDF bytes for ``source``.

    The original document structure is cloned so that page resources remain
    untouched, while Info dictionary fields, trailer IDs, and optional metadata
    streams are normalised to stable values.
    """

    reader = PdfReader(str(source))
    writer = PdfWriter()
    writer.clone_document_from_reader(reader)

    root = writer._root_object  # type: ignore[attr-defined]

    # Drop external metadata streams, name trees, and structure maps that carry
    # per-render identifiers.
    volatile_root_keys = (
        "/Metadata",
        "/StructTreeRoot",
        "/PieceInfo",
        "/OCProperties",
        "/Outlines",
        "/Names",
        "/OpenAction",
        "/Threads",
        "/PageLabels",
        "/AcroForm",
    )
    for volatile_key in volatile_root_keys:
        if volatile_key in root:  # type: ignore[index]
            del root[NameObject(volatile_key)]  # type: ignore[index]

    # Remove volatile struct-parent indices from page and annotation dictionaries.
    for page in writer.pages:
        if "/StructParents" in page:  # type: ignore[index]
            del page[NameObject("/StructParents")]  # type: ignore[index]
        annots = page.get("/Annots")  # type: ignore[index]
        if isinstance(annots, ArrayObject):
            for annot in annots:
                obj = annot.get_object()
                if isinstance(obj, DictionaryObject):
                    for key in ("/StructParent", "/M", "/NM", "/CreationDate", "/ModDate"):
                        if key in obj:  # type: ignore[index]
                            del obj[NameObject(key)]  # type: ignore[index]

        resources = page.get("/Resources")  # type: ignore[index]
        if isinstance(resources, DictionaryObject):
            fonts = resources.get("/Font")  # type: ignore[index]
            if isinstance(fonts, DictionaryObject):
                for font_ref in list(fonts.values()):  # type: ignore[attr-defined]
                    font = font_ref.get_object()
                    if isinstance(font, DictionaryObject):
                        _canonicalize_font(font)

    info_dict = DictionaryObject()
    info_dict[NameObject("/Producer")] = TextStringObject(_CANONICAL_PRODUCER)
    info_dict[NameObject("/Creator")] = TextStringObject(_CANONICAL_CREATOR)
    info_dict[NameObject("/CreationDate")] = TextStringObject(_CANONICAL_DATE)
    info_dict[NameObject("/ModDate")] = TextStringObject(_CANONICAL_DATE)
    writer._info = writer._add_object(info_dict)  # type: ignore[attr-defined]

    writer._ID = ArrayObject(  # type: ignore[attr-defined]
        [
            ByteStringObject(b"\x00" * 16),
            ByteStringObject(b"\x00" * 16),
        ]
    )

    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def _canonicalize_font(font: DictionaryObject) -> None:
    """Normalise embedded font dictionaries to stable names."""

    def _strip_subset(name: str) -> str:
        raw = name.lstrip("/")
        if len(raw) > 7 and raw[6] == "+" and raw[:6].isupper():
            return raw[7:]
        return raw

    base_font = font.get("/BaseFont")  # type: ignore[index]
    if isinstance(base_font, TextStringObject | NameObject):
        stripped = _strip_subset(str(base_font))
        font[NameObject("/BaseFont")] = NameObject(f"/{stripped}")

    descriptor = font.get("/FontDescriptor")  # type: ignore[index]
    if isinstance(descriptor, DictionaryObject):
        font_name = descriptor.get("/FontName")  # type: ignore[index]
        if isinstance(font_name, TextStringObject | NameObject):
            stripped = _strip_subset(str(font_name))
            descriptor[NameObject("/FontName")] = NameObject(f"/{stripped}")

    descendants = font.get("/DescendantFonts")  # type: ignore[index]
    if isinstance(descendants, ArrayObject):
        for descendant_ref in descendants:
            descendant = descendant_ref.get_object()
            if isinstance(descendant, DictionaryObject):
                _canonicalize_font(descendant)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Canonicalize a PDF file")
    parser.add_argument("source", type=Path, help="Input PDF path")
    parser.add_argument("output", type=Path, help="Destination for canonical PDF")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    data = canonicalize_pdf(args.source)
    args.output.write_bytes(data)


if __name__ == "__main__":
    main()
