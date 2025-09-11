from __future__ import annotations

import json
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import faiss
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


class HNSWInt8LabelBank(LabelBankProtocol):
    def __init__(self, dim: int, M: int = 32, efConstruction: int = 200, seed: int = 1234) -> None:
        self.dim = dim
        self._index = faiss.IndexHNSWFlat(dim, M)
        self._index.metric_type = faiss.METRIC_INNER_PRODUCT
        self._index.hnsw.efConstruction = efConstruction
        self._index.hnsw.random_seed = seed
        faiss.cvar.rand.seed(seed)
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
        faiss.write_index(self._index, os.path.join(path, "index.faiss"))
        with open(os.path.join(path, "labels.txt"), "w", encoding="utf-8") as fh:
            fh.write("\n".join(self._labels))
        if self._vocab_int8 is not None:
            np.save(os.path.join(path, "vocab.int8.npy"), self._vocab_int8)
        with open(os.path.join(path, "quant.json"), "w", encoding="utf-8") as fh:
            json.dump({"scale": 127}, fh)

    @classmethod
    def load(cls, path: str) -> HNSWInt8LabelBank:
        index = faiss.read_index(os.path.join(path, "index.faiss"))
        with open(os.path.join(path, "labels.txt"), encoding="utf-8") as fh:
            labels = [line.strip() for line in fh if line.strip()]
        vocab_path = os.path.join(path, "vocab.int8.npy")
        vocab = np.load(vocab_path) if os.path.exists(vocab_path) else None
        obj = cls(index.d)
        obj._index = index
        obj._labels = labels
        obj._vocab_int8 = vocab
        return obj

    def stats(self) -> Mapping[str, int]:
        bytes_index = len(faiss.serialize_index(self._index))
        bytes_vocab = int(self._vocab_int8.nbytes) if self._vocab_int8 is not None else 0
        return {
            "n_items": len(self._labels),
            "bytes_index": bytes_index,
            "bytes_vocab": bytes_vocab,
        }
