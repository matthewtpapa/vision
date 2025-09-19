"""LabelBank shard loading helpers."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from .hnsw_int8 import HNSWInt8LabelBank
from .protocol import LabelBankProtocol


def load_shard(path: str) -> LabelBankProtocol:
    """Load a LabelBank shard located at *path*.

    Raises ``FileNotFoundError`` when no persisted index is present.
    """

    base = Path(path)
    index_faiss = base / "index.faiss"
    index_jsonl = base / "index.jsonl"
    if not index_faiss.exists() and not index_jsonl.exists():
        raise FileNotFoundError(f"no LabelBank shard at {base}")
    return HNSWInt8LabelBank.load(str(base))


def project_embedding(vec: Sequence[float], target_dim: int) -> list[float]:
    """Project *vec* to ``target_dim`` by trimming or zero-padding."""

    if target_dim <= 0:
        return []
    values = list(vec)
    if len(values) >= target_dim:
        return values[:target_dim]
    return values + [0.0] * (target_dim - len(values))
