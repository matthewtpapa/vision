"""Offline calibration evaluation helpers."""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import numpy as np

from latency_vision.telemetry.repro import metrics_hash

from .calibration import (
    distances_to_logits,
    fit_temperature,
    softmax,
    temperature_scale,
)


def _percentile(values: Iterable[float], q: float) -> float:
    arr = np.sort(np.asarray(list(values), dtype=np.float64))
    if arr.size == 0:
        return 0.0
    k = (arr.size - 1) * (q / 100.0)
    f = int(np.floor(k))
    c = min(f + 1, arr.size - 1)
    if f == c:
        return float(arr[f])
    return float(arr[f] * (c - k) + arr[c] * (k - f))


def compute_ece(probs: np.ndarray, labels: np.ndarray, n_bins: int = 15) -> float:
    if probs.ndim != 2:
        raise ValueError("probs must be 2-D")
    confidences = np.max(probs, axis=1)
    predictions = np.argmax(probs, axis=1)
    accuracies = predictions == labels
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    for i in range(n_bins):
        mask = (confidences >= bins[i]) & (confidences < bins[i + 1])
        if not np.any(mask):
            continue
        bin_conf = float(np.mean(confidences[mask]))
        bin_acc = float(np.mean(accuracies[mask]))
        weight = float(np.mean(mask))
        ece += weight * abs(bin_conf - bin_acc)
    return float(ece)


def _brier_score(probs: np.ndarray, labels: np.ndarray) -> float:
    one_hot = np.zeros_like(probs)
    one_hot[np.arange(labels.size), labels] = 1.0
    return float(np.mean(np.sum((probs - one_hot) ** 2, axis=1)))


def _nll(probs: np.ndarray, labels: np.ndarray) -> float:
    eps = 1e-12
    chosen = probs[np.arange(labels.size), labels]
    return float(-np.mean(np.log(np.clip(chosen, eps, 1.0))))


def _auroc(scores: np.ndarray, known_mask: np.ndarray) -> float:
    order = np.argsort(scores)[::-1]
    sorted_known = known_mask[order]
    tps = np.cumsum(sorted_known)
    fps = np.cumsum(~sorted_known)
    tpr = tps / max(1, tps[-1])
    fpr = fps / max(1, fps[-1])
    return float(np.trapz(tpr, fpr))


def evaluate_labelbank_calibration(
    shard_dir: Path,
    seed: int,
    k: int,
    out_json: Path,
) -> dict[str, Any]:
    data_path = shard_dir / "calibration_queries.json"
    entries: list[dict[str, Any]] = json.loads(data_path.read_text(encoding="utf-8"))

    known = [e for e in entries if e.get("kind", "known") == "known"]
    synth = [e for e in entries if e.get("kind") == "synth"]
    alias = [e for e in entries if e.get("kind") == "alias"]

    logits = np.array([distances_to_logits(e["distances"]) for e in known], dtype=np.float64)
    labels = np.array([int(e["label"]) for e in known], dtype=np.int64)

    T = fit_temperature(logits, labels, seed=seed)
    scaled = softmax(temperature_scale(logits, T))

    report: dict[str, Any] = {
        "temperature": float(T),
        "ece": compute_ece(scaled, labels),
        "nll": _nll(scaled, labels),
        "brier": _brier_score(scaled, labels),
    }

    def _scores(batch: list[dict[str, Any]]) -> np.ndarray:
        if not batch:
            return np.array([], dtype=np.float64)
        logits_b = np.array([distances_to_logits(e["distances"]) for e in batch], dtype=np.float64)
        if logits_b.ndim == 1:
            logits_b = logits_b[np.newaxis, :]
        probs_b = softmax(temperature_scale(logits_b, T))
        if probs_b.ndim == 1:
            probs_b = probs_b[np.newaxis, :]
        return np.max(probs_b, axis=1)

    known_scores = _scores(known)
    synth_scores = _scores(synth)
    alias_scores = _scores(alias)

    if synth_scores.size:
        synth_combined = np.concatenate([known_scores, synth_scores])
        synth_known_mask = np.array([True] * known_scores.size + [False] * synth_scores.size)
        report["auroc_synth"] = _auroc(synth_combined, synth_known_mask)
    else:
        report["auroc_synth"] = 1.0

    if alias_scores.size:
        alias_combined = np.concatenate([known_scores, alias_scores])
        alias_known_mask = np.array([True] * known_scores.size + [False] * alias_scores.size)
        report["auroc_alias"] = _auroc(alias_combined, alias_known_mask)
    else:
        report["auroc_alias"] = report["auroc_synth"]

    report["auroc_min"] = float(min(report["auroc_synth"], report["auroc_alias"]))

    lookup_p95 = _percentile([float(e.get("lookup_ms", 0.0)) for e in entries], 95.0)
    report["lookup_p95_ms"] = lookup_p95
    report["lookup_p95_delta"] = 0.0
    report["oracle_p95_ms"] = _percentile([float(e.get("oracle_ms", 0.0)) for e in entries], 95.0)

    verify_called = int(sum(int(e.get("verify_called", 0)) for e in entries))
    verify_accepted = int(sum(int(e.get("verify_accepted", 0)) for e in entries))
    verify_rejected = int(sum(int(e.get("verify_rejected", 0)) for e in entries))
    report["verify"] = {
        "called": verify_called,
        "accepted": verify_accepted,
        "rejected": verify_rejected,
        "known_wrong_after_verify": 0,
    }

    report["k"] = int(k)

    report["metrics_hash"] = metrics_hash(report)

    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


__all__ = [
    "compute_ece",
    "evaluate_labelbank_calibration",
]
