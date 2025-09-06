# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 The Vision Authors
"""Utilities for working with matcher indices."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any, cast

import numpy as np

from vision.matcher.matcher_protocol import MatcherProtocol


def add_exemplars_to_index(index: MatcherProtocol, items: Iterable[dict[str, Any]]) -> int:
    """Add exemplar items to a matcher index.

    Parameters
    ----------
    index:
        The matcher backend implementing :class:`MatcherProtocol`.
    items:
        Iterable of dictionaries containing ``label`` and ``embedding`` keys.

    Returns
    -------
    int
        The number of items added to the index.
    """
    labels: list[str] = []
    embeddings: list[Iterable[float]] = []
    for item in items:
        labels.append(item["label"])
        embeddings.append(item["embedding"])

    if not labels:
        return 0

    vecs = np.asarray(embeddings, dtype=np.float32)
    # Protocol expects Sequence[Sequence[float]]; keep runtime fast, but satisfy typing
    index.add_many(cast(Sequence[Sequence[float]], vecs.tolist()), labels)
    return len(labels)
