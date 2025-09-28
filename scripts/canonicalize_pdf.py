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
from pypdf.generic import ByteStringObject, DictionaryObject, NameObject, TextStringObject

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

    # Drop any external metadata stream (typically XMP with volatile timestamps).
    if "/Metadata" in writer._root_object:  # type: ignore[attr-defined]
        del writer._root_object[NameObject("/Metadata")]  # type: ignore[index]

    if writer._info is None:  # type: ignore[attr-defined]
        writer._info = writer._add_object(DictionaryObject())  # type: ignore[attr-defined]

    info = writer._info.get_object()  # type: ignore[attr-defined]
    info[NameObject("/Producer")] = TextStringObject(_CANONICAL_PRODUCER)
    info[NameObject("/Creator")] = TextStringObject(_CANONICAL_CREATOR)
    info[NameObject("/CreationDate")] = TextStringObject(_CANONICAL_DATE)
    info[NameObject("/ModDate")] = TextStringObject(_CANONICAL_DATE)

    writer._ID = [  # type: ignore[attr-defined]
        ByteStringObject(b"\x00" * 16),
        ByteStringObject(b"\x00" * 16),
    ]

    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


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
