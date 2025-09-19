from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Protocol


class KBPromotion(Protocol):
    def promote(
        self, label: str, gallery_embeddings: Sequence[Sequence[float]]
    ) -> Mapping[str, Any]: ...
