from __future__ import annotations

import numpy as np

from latency_vision.label_bank import HNSWInt8LabelBank


def _dataset(n: int = 200, dim: int = 8) -> tuple[list[str], np.ndarray]:
    rng = np.random.default_rng(0)
    labels = [f"L{i}" for i in range(n)]
    vecs = rng.standard_normal((n, dim), dtype=np.float32)
    return labels, vecs


def test_roundtrip_and_stats(tmp_path: str) -> None:
    labels, vecs = _dataset()
    bank = HNSWInt8LabelBank(dim=8, seed=1234)
    bank.add(labels, vecs)
    bank.save(tmp_path)

    stats = bank.stats()
    assert stats["n_items"] == 200
    assert stats["bytes_index"] > 0
    assert stats["bytes_vocab"] > 0

    bank2 = HNSWInt8LabelBank.load(tmp_path)
    res1 = bank._lookup_vecs(vecs[0:1])
    res2 = bank2._lookup_vecs(vecs[0:1])
    assert res1.labels() == res2.labels()
    assert res1.scores() == res2.scores()
    assert res1.labels()[0] == labels[0]


def test_deterministic_results() -> None:
    labels, vecs = _dataset()
    bank_a = HNSWInt8LabelBank(dim=8, seed=1234)
    bank_b = HNSWInt8LabelBank(dim=8, seed=1234)
    bank_a.add(labels, vecs)
    bank_b.add(labels, vecs)
    res_a = bank_a._lookup_vecs(vecs[0:1])
    res_b = bank_b._lookup_vecs(vecs[0:1])
    assert res_a.labels() == res_b.labels()
    assert res_a.scores() == res_b.scores()


def test_tie_break() -> None:
    dim = 8
    bank = HNSWInt8LabelBank(dim=dim, seed=1234)
    vec = np.zeros((2, dim), dtype=np.float32)
    vec[:, 0] = 1.0
    bank.add(["B", "A"], vec)
    res = bank._lookup_vecs(vec[0:1], k=2)
    assert res.labels() == ["A", "B"]
