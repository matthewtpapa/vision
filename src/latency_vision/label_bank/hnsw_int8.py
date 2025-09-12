from __future__ import annotations

import json
import math
import os
import struct
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, cast

try:  # pragma: no cover - import guard
    import faiss

    _FAISS_AVAILABLE = True
except Exception:  # pragma: no cover - fallback
    faiss = cast(Any, None)
    _FAISS_AVAILABLE = False

try:  # pragma: no cover - import guard
    import numpy as np

    _NP_AVAILABLE = True
except Exception:  # pragma: no cover - fallback
    np = cast(Any, None)
    _NP_AVAILABLE = False

from .protocol import LabelBankProtocol, TopK


@dataclass
class _TopK:
    _scores: list[float]
    _labels: list[str]

    def scores(self) -> Sequence[float]:
        return self._scores

    def labels(self) -> Sequence[str]:
        return self._labels


def _normalize_vec(vec: Sequence[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vec))
    if norm == 0:
        return [0.0 for _ in vec]
    return [float(x / norm) for x in vec]


class _PyIndex:
    """Pure-Python brute-force inner-product index."""

    def __init__(self, dim: int) -> None:
        self.dim = dim
        self._vecs: list[list[float]] = []

    def add(self, vectors: Sequence[Sequence[float]]) -> None:
        for v in vectors:
            self._vecs.append(list(v))

    def search(
        self, queries: Sequence[Sequence[float]], k: int
    ) -> tuple[list[list[float]], list[list[int]]]:
        scores_out: list[list[float]] = []
        ids_out: list[list[int]] = []
        for q in queries:
            scores = [sum(q[i] * v[i] for i in range(self.dim)) for v in self._vecs]
            pairs = sorted(enumerate(scores), key=lambda x: (-x[1], x[0]))[:k]
            ids = [idx for idx, _ in pairs]
            top_scores = [sc for _, sc in pairs]
            scores_out.append(top_scores)
            ids_out.append(ids)
        return scores_out, ids_out


class HNSWInt8LabelBank(LabelBankProtocol):
    def __init__(self, dim: int, M: int = 32, efConstruction: int = 200, seed: int = 1234) -> None:
        self.dim = dim
        self._use_faiss = _FAISS_AVAILABLE and _NP_AVAILABLE
        if self._use_faiss:
            index = faiss.IndexHNSWFlat(dim, M)
            index.metric_type = faiss.METRIC_INNER_PRODUCT
            index.hnsw.efConstruction = efConstruction
            index.hnsw.random_seed = seed
            try:  # pragma: no cover - faiss global RNG
                faiss.cvar.rand.seed(seed)
            except Exception:  # pragma: no cover - best effort
                pass
            self._index: Any = index
        else:
            self._index = _PyIndex(dim)
        self._labels: list[str] = []
        self._vocab: Any = None  # numpy ndarray or bytearray
        self._saved_index_path: str | None = None

    def add(self, labels: Sequence[str], vectors: Sequence[Sequence[float]]) -> None:
        vectors = [_normalize_vec(v) for v in vectors]
        if any(len(v) != self.dim for v in vectors):
            raise ValueError("dimension mismatch")
        if len(labels) != len(vectors):
            raise ValueError("labels and vectors must align")

        if self._use_faiss:
            arr = np.asarray(vectors, dtype="float32")
            self._index.add(arr)
        else:
            self._index.add(vectors)

        if _NP_AVAILABLE:
            arr = np.clip(np.asarray(vectors, dtype="float32") * 127, -127, 127).astype("int8")
            self._vocab = arr if self._vocab is None else np.vstack([self._vocab, arr])
        else:
            if self._vocab is None:
                self._vocab = bytearray()
            for vec in vectors:
                for x in vec:
                    q = int(round(x * 127))
                    q = max(-127, min(127, q))
                    self._vocab.extend(struct.pack("b", q))

        self._labels.extend(labels)

    def _lookup_vecs(self, vectors: Sequence[Sequence[float]], k: int = 10) -> TopK:
        vectors = [_normalize_vec(v) for v in vectors]
        if any(len(v) != self.dim for v in vectors):
            raise ValueError("dimension mismatch")
        if self._use_faiss:
            queries = np.asarray(vectors, dtype="float32")
            self._index.hnsw.efSearch = max(64, 2 * k)
            scores, ids = self._index.search(queries, k)
            scores_list = scores.tolist()
            ids_list = ids.tolist()
        else:
            scores_list, ids_list = self._index.search(vectors, k)
        scores_q = scores_list[0]
        ids_q = ids_list[0]
        labels = [self._labels[i] for i in ids_q]
        pairs = sorted(zip(scores_q, labels), key=lambda x: (-x[0], x[1]))
        sorted_scores = [p[0] for p in pairs]
        sorted_labels = [p[1] for p in pairs]
        return _TopK(sorted_scores, sorted_labels)

    def lookup(
        self, items: Sequence[str] | Sequence[int], k: int = 10
    ) -> TopK:  # pragma: no cover - stub
        raise NotImplementedError("string/ID lookup will be implemented in M2-03")

    def save(self, path: str) -> None:
        os.makedirs(path, exist_ok=True)
        if self._use_faiss:
            index_path = os.path.join(path, "index.faiss")
            faiss.write_index(self._index, index_path)
            with open(os.path.join(path, "labels.txt"), "w", encoding="utf-8") as fh:
                fh.write("\n".join(self._labels))
        else:
            index_path = os.path.join(path, "index.jsonl")
            with open(index_path, "w", encoding="utf-8") as fh:
                for label, vec in zip(self._labels, self._index._vecs):
                    record = {"label": label, "values": vec}
                    fh.write(json.dumps(record, separators=(",", ":"), ensure_ascii=False) + "\n")
        self._saved_index_path = index_path

        if self._vocab is not None:
            if _NP_AVAILABLE and isinstance(self._vocab, np.ndarray):
                np.save(os.path.join(path, "vocab.int8.npy"), self._vocab)
            else:
                with open(os.path.join(path, "vocab.int8.bin"), "wb") as fh:
                    fh.write(self._vocab)

        with open(os.path.join(path, "quant.json"), "w", encoding="utf-8") as fh:
            json.dump({"scale": 127}, fh)

    @classmethod
    def load(cls, path: str) -> HNSWInt8LabelBank:
        faiss_path = os.path.join(path, "index.faiss")
        jsonl_path = os.path.join(path, "index.jsonl")
        if _FAISS_AVAILABLE and _NP_AVAILABLE and os.path.exists(faiss_path):
            index = faiss.read_index(faiss_path)
            obj = cls(index.d)
            obj._index = index
            obj._use_faiss = True
            with open(os.path.join(path, "labels.txt"), encoding="utf-8") as fh:
                obj._labels = [line.strip() for line in fh if line.strip()]
            obj._saved_index_path = faiss_path
        elif os.path.exists(jsonl_path):
            labels: list[str] = []
            vecs: list[list[float]] = []
            with open(jsonl_path, encoding="utf-8") as fh:
                for line in fh:
                    rec = json.loads(line)
                    labels.append(rec["label"])
                    vecs.append(rec["values"])
            if not vecs:
                raise FileNotFoundError("index.jsonl empty")
            obj = cls(len(vecs[0]))
            obj._use_faiss = False
            obj._index = _PyIndex(len(vecs[0]))
            obj._index.add(vecs)
            obj._labels = labels
            obj._saved_index_path = jsonl_path
        else:  # pragma: no cover - missing files
            raise FileNotFoundError("no index found at path")

        if _NP_AVAILABLE:
            vocab_path = os.path.join(path, "vocab.int8.npy")
            if os.path.exists(vocab_path):
                obj._vocab = np.load(vocab_path)
            else:
                bin_path = os.path.join(path, "vocab.int8.bin")
                if os.path.exists(bin_path):
                    obj._vocab = bytearray(open(bin_path, "rb").read())
        else:
            bin_path = os.path.join(path, "vocab.int8.bin")
            if os.path.exists(bin_path):
                obj._vocab = bytearray(open(bin_path, "rb").read())

        return obj

    def stats(self) -> Mapping[str, int]:
        if self._use_faiss:
            bytes_index = len(faiss.serialize_index(self._index))
        else:
            if self._saved_index_path and os.path.exists(self._saved_index_path):
                bytes_index = os.path.getsize(self._saved_index_path)
            else:
                bytes_index = sum(len(v) for v in self._index._vecs) * 8
        if _NP_AVAILABLE and isinstance(self._vocab, np.ndarray):
            bytes_vocab = int(self._vocab.nbytes)
        elif isinstance(self._vocab, bytes | bytearray):
            bytes_vocab = len(self._vocab)
        else:
            bytes_vocab = 0
        return {
            "n_items": len(self._labels),
            "bytes_index": bytes_index,
            "bytes_vocab": bytes_vocab,
        }
