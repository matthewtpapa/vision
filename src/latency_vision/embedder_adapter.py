# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 The Vision Authors
"""Embedder interfaces and CLIP-like adapter."""

from __future__ import annotations

from typing import Protocol

from .embedding_types import Embedding, l2_normalize


class Embedder:
    """Base embedder interface."""

    def encode(self, crops: list[object]) -> list[Embedding]:
        """Encode crops into embeddings."""
        raise NotImplementedError


class Runner(Protocol):
    """Callable responsible for producing raw embedding vectors."""

    def __call__(
        self,
        crops: list[object],
        *,
        dim: int,
        batch_size: int,
    ) -> list[list[float]]:
        """Encode *crops* and return a list of vectors."""

        raise NotImplementedError


class ClipLikeEmbedder(Embedder):
    """Embedder that delegates to a runner callable resembling CLIP."""

    def __init__(
        self,
        runner: Runner,
        dim: int = 512,
        normalize: bool = True,
        batch_size: int = 8,
    ) -> None:
        self._runner = runner
        self._dim = dim
        self._normalize = normalize
        self._batch_size = batch_size

    def encode(self, crops: list[object]) -> list[Embedding]:
        vectors = self._runner(crops, dim=self._dim, batch_size=self._batch_size)
        assert len(vectors) == len(crops)
        embeddings: list[Embedding] = []
        for v in vectors:
            assert len(v) == self._dim
            vec = l2_normalize(v) if self._normalize else tuple(v)
            embeddings.append(Embedding(vec=vec, dim=self._dim))
        return embeddings


__all__ = ["Embedder", "ClipLikeEmbedder"]
