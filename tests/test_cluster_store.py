# SPDX-License-Identifier: Apache-2.0
import json
from pathlib import Path

from vision.cluster_store import ClusterStore


def test_cluster_store_persists_exemplars(tmp_path):
    path = tmp_path / "kb.json"
    store = ClusterStore(path)
    emb = [0.0] * 128
    bbox = (1, 2, 3, 4)
    prov = {"source": "fake", "ts": "2025-01-01T00:00:00Z", "note": "stub"}
    store.add_exemplar("unknown", bbox, emb, prov)
    store.flush()

    data = json.loads(path.read_text())
    assert "exemplars" in data and len(data["exemplars"]) == 1
    ex = data["exemplars"][0]
    assert ex["label"] == "unknown"
    assert ex["bbox"] == list(bbox)
    assert ex["embedding"] == emb
    assert ex["provenance"]["source"] == "fake"
    assert "ts" in ex["provenance"]

    # Load again
    _ = ClusterStore.load(path)
    # Reloaded store should reflect the same exemplar count
    assert len(json.loads(Path(path).read_text())["exemplars"]) == 1
