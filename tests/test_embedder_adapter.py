from dataclasses import FrozenInstanceError

import pytest

from vision.embedder_adapter import ClipLikeEmbedder
from vision.embedding_types import Embedding


def test_cliplike_embedder_wraps_and_normalizes_vectors() -> None:
    def runner(crops, dim, batch_size):
        return [[3, 4, 0], [0, 0, 0]]

    embedder = ClipLikeEmbedder(runner, dim=3, normalize=True, batch_size=2)
    embeddings = embedder.encode([object(), object()])

    assert embeddings[0].vec == pytest.approx((0.6, 0.8, 0.0))
    assert embeddings[1].vec == pytest.approx((0.0, 0.0, 0.0))
    assert embeddings[0].dim == 3
    assert embeddings[1].dim == 3


def test_cliplike_embedder_respects_dim_and_batch_size() -> None:
    captured: dict[str, int] = {}

    def runner(crops, dim, batch_size):
        captured["dim"] = dim
        captured["batch_size"] = batch_size
        return [[0.0] * dim for _ in crops]

    embedder = ClipLikeEmbedder(runner, dim=5, normalize=False, batch_size=4)
    embedder.encode([object(), object()])

    assert captured["dim"] == 5
    assert captured["batch_size"] == 4


def test_embedding_is_immutable() -> None:
    emb = Embedding(vec=(1.0,), dim=1)
    with pytest.raises(FrozenInstanceError):
        emb.vec = (2.0,)  # type: ignore[misc]
