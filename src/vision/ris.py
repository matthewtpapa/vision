# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 The Vision Authors
"""
Reverse Image Search (RIS) stub.

This placeholder mimics a RIS connector. It returns an empty list for any
query and records the last query payload for debugging/tests.
"""

from __future__ import annotations

from typing import Any


class ReverseImageSearchStub:
    """Stub RIS connector."""

    def __init__(self) -> None:
        self.last_query: dict[str, Any] | None = None

    def search(self, image_or_embedding: Any) -> list[dict[str, Any]]:
        """Return an empty list of candidates (no network calls)."""
        self.last_query = {"input": image_or_embedding}
        return []
