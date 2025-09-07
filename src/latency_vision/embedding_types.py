# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 The Vision Authors
"""Embedding data contracts and helpers."""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt


@dataclass(frozen=True)
class Embedding:
    """Immutable embedding vector."""

    vec: tuple[float, ...]
    dim: int


def l2_normalize(vec: list[float] | tuple[float, ...]) -> tuple[float, ...]:
    """Return an L2-normalized copy of ``vec``.

    If ``vec`` has zero L2 norm, the original values are returned as a tuple.
    """

    norm = sqrt(sum(x * x for x in vec))
    if norm == 0:
        return tuple(vec)
    return tuple(x / norm for x in vec)


__all__ = ["Embedding", "l2_normalize"]
