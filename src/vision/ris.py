"""
Reverse Image Search (RIS) stub.

This placeholder mimics a RIS connector. It returns an empty list for any
query and records the last query payload for debugging/tests.
"""

from __future__ import annotations
from typing import Any, Dict, List

class ReverseImageSearchStub:
    """Stub RIS connector."""

    def __init__(self) -> None:
        self.last_query: Dict[str, Any] | None = None

    def search(self, image_or_embedding: Any) -> List[Dict[str, Any]]:
        """Return an empty list of candidates (no network calls)."""
        self.last_query = {"input": image_or_embedding}
        return []
