from __future__ import annotations

import pytest

pytest.importorskip("numpy")

from vision.oracle import CandidateOracle


def test_oracle_abstains_until_confident() -> None:
    oracle = CandidateOracle(T=1.0, abstain_p=0.8, smoothing_alpha=0.5)
    labels = ["cat", "dog"]
    # First observation has moderate confidence
    label, confidence, abstained = oracle.predict(1, labels, [0.1, 0.9])
    assert abstained
    assert label == "__unknown__"
    assert 0.0 <= confidence <= 1.0

    # Stronger evidence should eventually emit once EMA crosses the threshold
    for _ in range(3):
        label, confidence, abstained = oracle.predict(1, labels, [0.01, 2.0])
    assert not abstained
    assert label == "cat"
    assert confidence > 0.8


def test_independent_tracks_do_not_share_state() -> None:
    oracle = CandidateOracle(T=1.0, abstain_p=0.5, smoothing_alpha=0.1)
    labels = ["alpha", "beta"]
    l1, c1, a1 = oracle.predict(1, labels, [0.2, 1.2])
    l2, c2, a2 = oracle.predict(2, labels, [0.2, 1.2])
    assert c1 == c2
    # Track 1 receives additional evidence and should change independently
    oracle.predict(1, labels, [0.01, 3.0])
    l1b, c1b, _ = oracle.predict(1, labels, [0.01, 3.0])
    assert c1b != c2
    assert l1b in labels or l1b == "__unknown__"
