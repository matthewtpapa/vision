from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("numpy")

import numpy as np

from latency_vision.calibration import distances_to_logits, softmax, temperature_scale
from latency_vision.eval_calibration import _ensure_2d, evaluate_labelbank_calibration


def _write_fixture(tmp_path: Path) -> Path:
    data = [
        {
            "kind": "known",
            "label": 0,
            "distances": [0.1, 0.9, 1.5],
            "lookup_ms": 3.0,
            "oracle_ms": 1.0,
            "verify_called": 1,
            "verify_accepted": 1,
            "verify_rejected": 0,
        },
        {
            "kind": "known",
            "label": 1,
            "distances": [1.2, 0.2, 0.5],
            "lookup_ms": 4.0,
            "oracle_ms": 1.2,
            "verify_called": 1,
            "verify_accepted": 0,
            "verify_rejected": 1,
        },
        {
            "kind": "synth",
            "label": -1,
            "distances": [2.0, 2.5, 3.0],
            "lookup_ms": 5.0,
            "oracle_ms": 1.5,
            "verify_called": 0,
            "verify_accepted": 0,
            "verify_rejected": 0,
        },
        {
            "kind": "alias",
            "label": -1,
            "distances": [1.8, 2.3, 2.9],
            "lookup_ms": 4.5,
            "oracle_ms": 1.7,
            "verify_called": 0,
            "verify_accepted": 0,
            "verify_rejected": 0,
        },
    ]
    shard_dir = tmp_path / "shard"
    shard_dir.mkdir()
    (shard_dir / "calibration_queries.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return shard_dir


def test_evaluate_labelbank_calibration_reports_metrics(tmp_path: Path) -> None:
    shard = _write_fixture(tmp_path)
    out_json = tmp_path / "stats.json"
    report = evaluate_labelbank_calibration(shard, seed=777, k=10, out_json=out_json)
    assert out_json.exists()
    assert "ece" in report and report["ece"] >= 0.0
    assert "auroc_min" in report and 0.0 <= report["auroc_min"] <= 1.0
    verify = report["verify"]
    assert verify["called"] == verify["accepted"] + verify["rejected"]
    saved = json.loads(out_json.read_text(encoding="utf-8"))
    assert report["metrics_hash"] == saved["metrics_hash"]

    # Determinism: repeated evaluation yields identical hash
    report2 = evaluate_labelbank_calibration(
        shard,
        seed=777,
        k=10,
        out_json=tmp_path / "stats2.json",
    )
    assert report["metrics_hash"] == report2["metrics_hash"]


def test_single_row_scores_from_softmax(tmp_path: Path) -> None:
    shard = _write_fixture(tmp_path)
    report = evaluate_labelbank_calibration(shard, seed=777, k=10, out_json=tmp_path / "stats.json")

    synth_logits = distances_to_logits([2.0, 2.5, 3.0])
    scaled = temperature_scale(synth_logits, report["temperature"])
    probs = softmax(scaled)

    scores = np.max(_ensure_2d(probs), axis=1)
    assert scores.shape == (1,)
    assert scores[0] == pytest.approx(np.max(probs))
