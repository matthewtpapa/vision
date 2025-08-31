# SPDX-License-Identifier: Apache-2.0
"""Utilities for working with matcher indices."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

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
    try:
        import numpy as np
    except Exception as e:  # pragma: no cover
        raise ImportError("numpy not available") from e

    labels: list[str] = []
    embeddings: list[Iterable[float]] = []
    for item in items:
        labels.append(item["label"])
        embeddings.append(item["embedding"])

    if not labels:
        return 0

    vecs = np.asarray(embeddings, dtype=np.float32)
    index.add_many(vecs, labels)
    return len(labels)
