from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Protocol


class KBPromotion(Protocol):
    """Protocol describing promotion of gallery exemplars."""

    def promote(
        self, label: str, gallery_embeddings: Sequence[Sequence[float]]
    ) -> Mapping[str, Any]:
        """Return promotion metadata for *label* given gallery embeddings."""

        raise NotImplementedError
