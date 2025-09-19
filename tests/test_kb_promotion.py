from __future__ import annotations

import json
import random
from pathlib import Path

from latency_vision.kb import KBPromotionImpl
from latency_vision.kb.promotion_impl import _read_int8_npy


def _sample_embeddings(n: int, dim: int) -> list[list[float]]:
    rng = random.Random(123)
    result: list[list[float]] = []
    for _ in range(n):
        row = [rng.uniform(-1.0, 1.0) for _ in range(dim)]
        result.append(row)
    return result


def test_kb_promotion_cap_and_ledger(tmp_path: Path) -> None:
    kb_dir = tmp_path / "bench" / "kb"
    promo = KBPromotionImpl(output_dir=kb_dir)

    embeddings = _sample_embeddings(6, 8)
    result = promo.promote("test/label", embeddings)
    assert result["medoids"] <= 3
    assert result["updated"] is True

    medoid_dir = kb_dir / "medoids"
    medoid_path = medoid_dir / "test_label.int8.npy"
    meta_path = medoid_dir / "test_label.json"
    ledger_path = kb_dir / "promotion_ledger.jsonl"

    assert medoid_path.exists()
    medoids = _read_int8_npy(medoid_path)
    assert len(medoids) <= 3
    assert all(all(-127 <= val <= 127 for val in row) for row in medoids)

    assert meta_path.exists()
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    assert meta["label"] == "test/label"
    assert meta["medoids"] == len(medoids)
    assert meta["hash"] == result["hash"]

    assert ledger_path.exists()
    initial_lines = ledger_path.read_text(encoding="utf-8").splitlines()
    lines = [json.loads(line) for line in initial_lines if line.strip()]
    assert len(lines) == 1
    entry = lines[0]
    expected_bytes = sum(len(row) for row in medoids)
    assert entry == {
        "label": "test/label",
        "medoids": len(medoids),
        "bytes": expected_bytes,
        "method": "herding",
        "quant": "int8",
        "hash": result["hash"],
    }

    second = promo.promote("test/label", embeddings)
    assert second["updated"] is False
    lines_after = ledger_path.read_text(encoding="utf-8").splitlines()
    assert lines_after == initial_lines


def test_kb_promotion_empty(tmp_path: Path) -> None:
    promo = KBPromotionImpl(output_dir=tmp_path / "bench" / "kb")
    out = promo.promote("empty", [])
    assert out["medoids"] == 0
    ledger_path = tmp_path / "bench" / "kb" / "promotion_ledger.jsonl"
    assert not ledger_path.exists() or ledger_path.read_text(encoding="utf-8").strip() == ""
