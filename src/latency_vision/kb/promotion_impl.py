"""KB promotion implementation with capped int8 medoids."""

from __future__ import annotations

import ast
import hashlib
import json
import math
import os
import struct
from array import array
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..ledger import EvidenceLedger, JsonLedger
from .promotion import KBPromotion


def _normalize_label(label: str) -> str:
    safe = [c if c.isalnum() or c in {"-", "_"} else "_" for c in label]
    sanitized = "".join(safe).strip("_")
    return sanitized or "label"


def _normalize_embeddings(embeddings: Sequence[Sequence[float]]) -> list[list[float]]:
    rows: list[list[float]] = []
    for vec in embeddings:
        values = [float(x) for x in vec]
        norm_sq = sum(v * v for v in values)
        norm = math.sqrt(norm_sq) if norm_sq > 0.0 else 1.0
        rows.append([v / norm for v in values])
    if not rows:
        raise ValueError("embeddings must contain at least one vector")
    dim = len(rows[0])
    if any(len(row) != dim for row in rows):
        raise ValueError("embedding dimensions must be consistent")
    return rows


def _dot(a: Sequence[float], b: Sequence[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _farthest_point_indices(vecs: Sequence[Sequence[float]], cap: int) -> list[int]:
    n = len(vecs)
    if n == 0:
        return []
    cap = min(cap, n)
    if cap <= 0:
        return []
    best_norm = -1.0
    first_idx = 0
    for i, vec in enumerate(vecs):
        norm_sq = sum(v * v for v in vec)
        if norm_sq > best_norm:
            best_norm = norm_sq
            first_idx = i
    selected = [first_idx]
    if cap == 1:
        return selected
    sims = [_dot(vec, vecs[first_idx]) for vec in vecs]
    sims[first_idx] = float("inf")
    while len(selected) < cap:
        candidate = min(range(n), key=lambda idx: (sims[idx], idx))
        while candidate in selected:
            sims[candidate] = float("inf")
            candidate = min(range(n), key=lambda idx: (sims[idx], idx))
        selected.append(candidate)
        candidate_sims = [_dot(vec, vecs[candidate]) for vec in vecs]
        for idx in range(n):
            sims[idx] = max(sims[idx], candidate_sims[idx])
        for idx in selected:
            sims[idx] = float("inf")
    return selected


def _serialize_int8_matrix(values: Sequence[Sequence[int]]) -> bytes:
    buf = array("b")
    for row in values:
        buf.extend(int(v) for v in row)
    return buf.tobytes()


def _write_int8_npy(path: Path, data: Sequence[Sequence[int]]) -> None:
    rows = len(data)
    cols = len(data[0]) if rows else 0
    header_dict = {"descr": "|i1", "fortran_order": False, "shape": (rows, cols)}
    header_str = str(header_dict)
    header_bytes = header_str.encode("latin1")
    total_header = header_bytes + b"\n"
    header_len = len(total_header)
    prefix_len = len(b"\x93NUMPY") + 2 + 2
    pad = (16 - ((prefix_len + header_len) % 16)) % 16
    total_header = header_bytes + b" " * pad + b"\n"
    with path.open("wb") as fh:
        fh.write(b"\x93NUMPY")
        fh.write(bytes([1, 0]))
        fh.write(struct.pack("<H", len(total_header)))
        fh.write(total_header)
        fh.write(_serialize_int8_matrix(data))


def _read_int8_npy(path: Path) -> list[list[int]]:
    with path.open("rb") as fh:
        magic = fh.read(6)
        if magic != b"\x93NUMPY":
            raise ValueError("invalid npy magic header")
        version = fh.read(2)
        if len(version) != 2:
            raise ValueError("invalid npy version")
        if version[0] == 1:
            header_len = struct.unpack("<H", fh.read(2))[0]
        else:
            header_len = struct.unpack("<I", fh.read(4))[0]
        header = fh.read(header_len)
        header_text = header.decode("latin1").strip()
        header_dict = ast.literal_eval(header_text)
        shape = header_dict.get("shape", ())
        if not shape:
            return []
        if len(shape) == 1:
            rows, cols = shape[0], 1
        else:
            rows, cols = shape
        data_bytes = fh.read()
        buf = array("b")
        buf.frombytes(data_bytes)
        values: list[list[int]] = []
        if rows == 0 or cols == 0:
            return []
        if len(buf) != rows * cols:
            raise ValueError("npy payload size mismatch")
        it = iter(buf)
        for _ in range(rows):
            row = [next(it) for _ in range(cols)]
            values.append(row)
        return values


@dataclass
class KBPromotionImpl(KBPromotion):
    """Promote gallery embeddings into capped int8 medoids."""

    output_dir: str | os.PathLike[str] = "bench/kb"
    ledger: EvidenceLedger | None = None
    medoid_cap: int = 3
    quant_scale: int = 127

    def __post_init__(self) -> None:
        if self.ledger is None:
            ledger_path = Path(self.output_dir) / "promotion_ledger.jsonl"
            self.ledger = JsonLedger(str(ledger_path))
        self._base = Path(self.output_dir)
        self._medoid_dir = self._base / "medoids"
        self._medoid_dir.mkdir(parents=True, exist_ok=True)

    def promote(
        self,
        label: str,
        gallery_embeddings: Sequence[Sequence[float]],
    ) -> Mapping[str, Any]:
        if not gallery_embeddings:
            return {
                "label": label,
                "medoids": 0,
                "bytes": 0,
                "hash": "",
                "updated": False,
            }

        normalized = _normalize_embeddings(gallery_embeddings)

        indices = _farthest_point_indices(normalized, self.medoid_cap)
        medoids = [normalized[idx] for idx in indices]
        quant_rows: list[list[int]] = []
        for row in medoids:
            q_row: list[int] = []
            for value in row:
                scaled = int(round(value * self.quant_scale))
                if scaled > 127:
                    scaled = 127
                elif scaled < -127:
                    scaled = -127
                q_row.append(scaled)
            quant_rows.append(q_row)
        data_bytes = _serialize_int8_matrix(quant_rows)
        digest = hashlib.sha256(data_bytes).hexdigest()

        safe_label = _normalize_label(label)
        npy_path = self._medoid_dir / f"{safe_label}.int8.npy"
        meta_path = self._medoid_dir / f"{safe_label}.json"

        existing_hash = None
        if npy_path.exists():
            try:
                existing_rows = _read_int8_npy(npy_path)
                existing_hash = hashlib.sha256(_serialize_int8_matrix(existing_rows)).hexdigest()
            except Exception:
                existing_hash = None

        updated = digest != existing_hash
        if updated:
            _write_int8_npy(npy_path, quant_rows)
            meta = {
                "label": label,
                "medoids": len(quant_rows),
                "dim": len(quant_rows[0]) if quant_rows else 0,
                "quant": {"scale": self.quant_scale, "dtype": "int8"},
                "hash": digest,
            }
            meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
            if self.ledger is not None:
                self.ledger.append(
                    {
                        "label": label,
                        "medoids": len(quant_rows),
                        "bytes": len(data_bytes),
                        "method": "herding",
                        "quant": "int8",
                        "hash": digest,
                    }
                )

        return {
            "label": label,
            "medoids": len(quant_rows),
            "bytes": len(data_bytes),
            "hash": digest,
            "updated": updated,
        }


__all__ = ["KBPromotionImpl"]
