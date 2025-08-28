"""Cluster store stub with JSON persistence."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import NamedTemporaryFile


class ClusterStore:
    """A stub cluster store that records embeddings by cluster ID.

    In addition to the simple in-memory API used for early experiments, the
    store can persist *exemplar* records to disk in a small JSON file.  Each
    exemplar contains a label, bounding box, embedding vector and provenance
    information.
    """

    def __init__(self, path: str | Path = "data/kb.json") -> None:
        self._store: dict[int, list[list[float]]] = {}

        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._data: dict[str, list[dict[str, object]]] = {"exemplars": []}

    # ------------------------------------------------------------------
    # Backwards compatible in-memory API
    def add(self, cluster_id: int, embedding: list[float]) -> None:
        """Add an embedding to the cluster identified by ``cluster_id``."""
        self._store.setdefault(cluster_id, []).append(embedding)

    def get(self, cluster_id: int) -> list[list[float]]:
        """Return a list of embeddings for ``cluster_id``.

        If the cluster ID has not been seen before, an empty list is returned.
        """
        return list(self._store.get(cluster_id, []))

    # ------------------------------------------------------------------
    # Exemplar persistence API
    def add_exemplar(
        self,
        label: str,
        bbox: tuple[int, int, int, int],
        embedding: list[float],
        provenance: dict,
    ) -> None:
        """Append an exemplar description to the in-memory buffer."""

        self._data["exemplars"].append(
            {
                "label": label,
                "bbox": list(bbox),
                "embedding": list(embedding),
                "provenance": provenance,
            }
        )

    def flush(self) -> None:
        """Atomically persist the current exemplars to disk."""

        with NamedTemporaryFile("w", delete=False, dir=self._path.parent) as tmp:
            json.dump(self._data, tmp, ensure_ascii=False, indent=2)
        Path(tmp.name).replace(self._path)

    @classmethod
    def load(cls, path: str | Path) -> ClusterStore:
        """Load existing exemplars from ``path`` if it exists."""

        p = Path(path)
        store = cls(p)
        if p.exists():
            store._data = json.loads(p.read_text())
        return store
