from __future__ import annotations

import pytest

try:
    import numpy as np
except ModuleNotFoundError:  # pragma: no cover - environment guard
    pytest.skip("requires numpy", allow_module_level=True)

from vision.calibration import (
    distances_to_logits,
    fit_temperature,
    softmax,
    temperature_scale,
    unknown_rate_guard,
)


def test_softmax_normalises() -> None:
    logits = np.array([[1.0, 2.0, 0.5], [0.1, -0.2, 0.3]], dtype=np.float64)
    probs = softmax(logits)
    assert probs.shape == logits.shape
    np.testing.assert_allclose(probs.sum(axis=1), np.ones(2), atol=1e-8)


def test_temperature_monotonicity() -> None:
    logits = np.array([[2.0, 1.0, 0.5]], dtype=np.float64)
    base = softmax(logits)[0]
    hotter = softmax(temperature_scale(logits, 2.0))[0]
    colder = softmax(temperature_scale(logits, 0.5))[0]
    assert hotter.max() < base.max()
    assert colder.max() > base.max()


def test_fit_temperature_recovers_ground_truth() -> None:
    rng = np.random.default_rng(123)
    logits = rng.normal(size=(64, 3))
    logits = distances_to_logits(-logits)
    true_T = 2.5
    scaled = softmax(temperature_scale(logits, true_T))
    labels = np.argmax(scaled, axis=1)
    fitted = fit_temperature(logits, labels, seed=999)
    assert abs(fitted - true_T) < 0.3


def test_unknown_rate_guard() -> None:
    assert unknown_rate_guard([True, False, True, True]) == pytest.approx(0.75)
    assert unknown_rate_guard([]) == 0.0
