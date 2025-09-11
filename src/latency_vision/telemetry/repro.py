#!/usr/bin/env python3
"""Deterministic metrics canonicalization and hashing utilities."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from hashlib import sha256
from typing import Any


def _normalize(obj: Any) -> Any:
    """Recursively normalize metrics for deterministic serialization."""
    if isinstance(obj, Mapping):
        return {k: _normalize(obj[k]) for k in sorted(obj)}
    if isinstance(obj, Sequence) and not isinstance(obj, (str, bytes, bytearray)):
        return [_normalize(x) for x in obj]
    if isinstance(obj, float):
        return f"{obj:.9f}"
    return obj


def canonicalize_metrics(obj: dict[str, Any]) -> bytes:
    """Return a canonical JSON representation of *obj*.

    Deep-sort all dict keys; normalize sequences to lists; convert floats to
    strings rounded to 9 decimal places; ensure all numbers serialize
    deterministically; dump to UTF-8 bytes via ``json.dumps(..., separators=(",",
    ":"), ensure_ascii=False)``.
    """
    canonical = _normalize(obj)
    return json.dumps(canonical, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def metrics_hash(obj: dict[str, Any]) -> str:
    """Return the SHA256 hash of the canonicalized metrics object."""
    return sha256(canonicalize_metrics(obj)).hexdigest()
