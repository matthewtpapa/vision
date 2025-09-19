from __future__ import annotations

from latency_vision.label_bank.loader import project_embedding


def test_project_embedding_pad() -> None:
    vec = [1.0, 2.0]
    projected = project_embedding(vec, 4)
    assert projected == [1.0, 2.0, 0.0, 0.0]


def test_project_embedding_trim() -> None:
    vec = [float(i) for i in range(6)]
    projected = project_embedding(vec, 3)
    assert projected == [0.0, 1.0, 2.0]


def test_project_embedding_same_length() -> None:
    vec = [0.1, 0.2, 0.3]
    projected = project_embedding(vec, 3)
    assert projected == [0.1, 0.2, 0.3]
