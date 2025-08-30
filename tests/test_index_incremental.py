from __future__ import annotations

import pytest

pytest.importorskip("numpy")

from vision.cluster_store import JsonClusterStore
from vision.matcher.py_fallback import NumpyMatcher


def test_listener_updates_matcher(tmp_path):
    matcher = NumpyMatcher()
    store = JsonClusterStore(tmp_path / "kb.json")

    def _on_exemplar(item: dict[str, object]) -> None:
        matcher.add(item["embedding"], str(item["label"]))  # type: ignore[arg-type]

    store.add_listener(_on_exemplar)

    assert matcher.topk([1, 0, 0], 1) == []

    store.add_exemplar(
        label="Z",
        bbox=(0, 0, 1, 1),
        embedding=[1.0, 0.0, 0.0],
        provenance={},
    )

    assert matcher.topk([1.0, 0.0, 0.0], 1)[0][0] == "Z"
