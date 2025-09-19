"""JSONL evidence ledger writer."""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Mapping
from typing import Any


class JsonLedger:
    """Append-only JSON ledger that writes one record per line."""

    def __init__(self, path: str) -> None:
        self._path = path
        directory = os.path.dirname(path) or "."
        os.makedirs(directory, exist_ok=True)

    def append(self, record: Mapping[str, Any]) -> None:
        """Append *record* to the ledger using a best-effort atomic write."""

        data = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
        directory = os.path.dirname(self._path) or "."
        tmpf = tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8", dir=directory)
        try:
            tmpf.write(data + "\n")
            tmpf.flush()
            os.fsync(tmpf.fileno())
            tmpf.close()
            with open(self._path, "a", encoding="utf-8") as out:
                out.write(data + "\n")
        finally:
            try:
                os.unlink(tmpf.name)
            except FileNotFoundError:  # pragma: no cover - cleanup best effort
                pass


__all__ = ["JsonLedger"]
