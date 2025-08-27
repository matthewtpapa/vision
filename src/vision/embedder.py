"""Feature embedder stub."""

from __future__ import annotations

from typing import Any, List


class Embedder:
    """A stub embedder that returns a fixed embedding vector.

    This placeholder mimics a real embedding model by always returning the
    same 128-dimensional feature vector regardless of the input.
    """

    def embed(self, crop: Any) -> List[float]:
        """Return a dummy 128-dimensional embedding.

        Parameters
        ----------
        crop:
            Ignored input representing an image crop or frame.

        Returns
        -------
        list of float
            A list of 128 zeros representing an embedding vector.
        """
        return [0.0] * 128
