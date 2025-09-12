from __future__ import annotations

import random

from latency_vision.label_bank import HNSWInt8LabelBank


def _dataset(n: int = 200, dim: int = 8) -> tuple[list[str], list[list[float]]]:
    rng = random.Random(0)
    labels = [f"L{i}" for i in range(n)]
    vecs = [[rng.gauss(0.0, 1.0) for _ in range(dim)] for _ in range(n)]
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
    res1 = bank._lookup_vecs([vecs[0]])
    res2 = bank2._lookup_vecs([vecs[0]])
    assert res1.labels() == res2.labels()
    assert res1.scores() == res2.scores()
    assert res1.labels()[0] in labels


def test_deterministic_results() -> None:
    labels, vecs = _dataset()
    bank_a = HNSWInt8LabelBank(dim=8, seed=1234)
    bank_b = HNSWInt8LabelBank(dim=8, seed=1234)
    bank_a.add(labels, vecs)
    bank_b.add(labels, vecs)
    res_a = bank_a._lookup_vecs([vecs[0]])
    res_b = bank_b._lookup_vecs([vecs[0]])
    assert res_a.labels() == res_b.labels()
    assert res_a.scores() == res_b.scores()


def test_tie_break() -> None:
    dim = 8
    bank = HNSWInt8LabelBank(dim=dim, seed=1234)
    vec = [[1.0] + [0.0] * (dim - 1) for _ in range(2)]
    bank.add(["B", "A"], vec)
    res = bank._lookup_vecs([vec[0]], k=2)
    assert res.labels() == ["A", "B"]
