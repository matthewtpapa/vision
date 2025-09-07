# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 The Vision Authors
"""Typed associations between tracks and embeddings."""

from __future__ import annotations

from dataclasses import dataclass

from latency_vision.matcher.types import MatchResult

from .embedding_types import Embedding
from .types import Track


@dataclass(frozen=True)
class TrackEmbedding:
    """Pair a track with its corresponding embedding."""

    track: Track
    embedding: Embedding
    match: MatchResult | None = None


__all__ = ["TrackEmbedding"]
