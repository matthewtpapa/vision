from __future__ import annotations

from typing import TypedDict

from .matcher_protocol import Neighbor


class MatchResult(TypedDict):
    neighbors: list[Neighbor]
    is_unknown: bool


__all__ = ["MatchResult"]
