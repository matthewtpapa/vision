from __future__ import annotations

import json
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, cast

try:  # pragma: no cover - import guard
    import faiss

    _FAISS_AVAILABLE = True
except Exception:  # pragma: no cover - fallback path
    faiss = cast(Any, None)
    _FAISS_AVAILABLE = False

import numpy as np

from .protocol import LabelBankProtocol, TopK


@dataclass
class _TopK:
    _scores: list[float]
    _labels: list[str]

    def scores(self) -> Sequence[float]:
        return self._scores

    def labels(self) -> Sequence[str]:
        return self._labels


class _NPIndex:
    """NumPy brute-force IP index (fallback when FAISS is unavailable)."""

    def __init__(self, dim: int, M: int = 32) -> None:  # noqa: ARG002 - M kept for API parity
        self.dim = dim
        self._vecs: np.ndarray | None = None
        self.metric_type = None

        class _H:
            def __init__(self) -> None:
                self.efConstruction = 0
                self.efSearch = 0
                self.random_seed = 0

        self.hnsw = _H()

    def add(self, vectors: np.ndarray) -> None:
        self._vecs = vectors if self._vecs is None else np.vstack([self._vecs, vectors])

    def search(self, queries: np.ndarray, k: int) -> tuple[np.ndarray, np.ndarray]:
        if self._vecs is None:  # pragma: no cover - defensive
            raise ValueError("index is empty")
        scores = queries @ self._vecs.T
        idx = np.argsort(-scores, axis=1)[:, :k]
        top = np.take_along_axis(scores, idx, axis=1)
        return top.astype("float32"), idx.astype("int64")


class HNSWInt8LabelBank(LabelBankProtocol):
    def __init__(self, dim: int, M: int = 32, efConstruction: int = 200, seed: int = 1234) -> None:
        self.dim = dim
        if _FAISS_AVAILABLE:
            self._index = faiss.IndexHNSWFlat(dim, M)
            self._index.metric_type = faiss.METRIC_INNER_PRODUCT
            self._index.hnsw.efConstruction = efConstruction
            self._index.hnsw.random_seed = seed
            try:  # pragma: no cover - faiss internal global RNG
                faiss.cvar.rand.seed(seed)
            except Exception:  # pragma: no cover - best effort
                pass
        else:  # pragma: no cover - executed when faiss unavailable
            self._index = _NPIndex(dim, M)
        self._labels: list[str] = []
        self._vocab_int8: np.ndarray | None = None

    def add(self, labels: Sequence[str], vectors: np.ndarray) -> None:
        vectors = np.asarray(vectors, dtype="float32")
        if vectors.shape[1] != self.dim:
            raise ValueError("dimension mismatch")
        if len(labels) != vectors.shape[0]:
            raise ValueError("labels and vectors must align")
        # normalize
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        vectors = vectors / np.maximum(norms, 1e-12)
        self._index.add(vectors)
        int8 = np.clip(vectors * 127, -127, 127).astype("int8")
        self._vocab_int8 = int8 if self._vocab_int8 is None else np.vstack([self._vocab_int8, int8])
        self._labels.extend(labels)

    def _lookup_vecs(self, vectors: np.ndarray, k: int = 10) -> TopK:
        vectors = np.asarray(vectors, dtype="float32")
        if vectors.shape[1] != self.dim:
            raise ValueError("dimension mismatch")
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        vectors = vectors / np.maximum(norms, 1e-12)
        self._index.hnsw.efSearch = max(64, 2 * k)
        scores, ids = self._index.search(vectors, k)
        labels = [self._labels[i] for i in ids[0]]
        pairs = sorted(zip(scores[0], labels), key=lambda x: (-x[0], x[1]))
        sorted_scores = [p[0] for p in pairs]
        sorted_labels = [p[1] for p in pairs]
        return _TopK(sorted_scores, sorted_labels)

    def lookup(
        self, items: Sequence[str] | Sequence[int], k: int = 10
    ) -> TopK:  # pragma: no cover - stub
        raise NotImplementedError("string/ID lookup will be implemented in M2-03")

    def save(self, path: str) -> None:
        os.makedirs(path, exist_ok=True)
        if _FAISS_AVAILABLE and isinstance(self._index, faiss.Index):
            faiss.write_index(self._index, os.path.join(path, "index.faiss"))
        else:
            vecs = getattr(self._index, "_vecs", None)
            if vecs is not None:
                np.save(os.path.join(path, "index.npy"), vecs)
        with open(os.path.join(path, "labels.txt"), "w", encoding="utf-8") as fh:
            fh.write("\n".join(self._labels))
        if self._vocab_int8 is not None:
            np.save(os.path.join(path, "vocab.int8.npy"), self._vocab_int8)
        with open(os.path.join(path, "quant.json"), "w", encoding="utf-8") as fh:
            json.dump({"scale": 127}, fh)

    @classmethod
    def load(cls, path: str) -> HNSWInt8LabelBank:
        faiss_path = os.path.join(path, "index.faiss")
        np_path = os.path.join(path, "index.npy")
        if _FAISS_AVAILABLE and os.path.exists(faiss_path):
            index = faiss.read_index(faiss_path)
            obj = cls(index.d)
            obj._index = index
        elif os.path.exists(np_path):
            vecs = np.load(np_path).astype("float32")
            obj = cls(vecs.shape[1])
            obj._index = _NPIndex(vecs.shape[1])
            obj._index.add(vecs)
        else:  # pragma: no cover - missing files
            raise FileNotFoundError("no index found at path")
        with open(os.path.join(path, "labels.txt"), encoding="utf-8") as fh:
            labels = [line.strip() for line in fh if line.strip()]
        vocab_path = os.path.join(path, "vocab.int8.npy")
        vocab = np.load(vocab_path) if os.path.exists(vocab_path) else None
        obj._labels = labels
        obj._vocab_int8 = vocab
        return obj

    def stats(self) -> Mapping[str, int]:
        if _FAISS_AVAILABLE and isinstance(self._index, faiss.Index):
            bytes_index = len(faiss.serialize_index(self._index))
        else:
            vecs = getattr(self._index, "_vecs", None)
            bytes_index = int(vecs.nbytes) if vecs is not None else 0
        bytes_vocab = int(self._vocab_int8.nbytes) if self._vocab_int8 is not None else 0
        return {
            "n_items": len(self._labels),
            "bytes_index": bytes_index,
            "bytes_vocab": bytes_vocab,
        }
