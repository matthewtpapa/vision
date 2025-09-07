# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 The Vision Authors
from latency_vision.fake_detector import FakeDetector


def test_fake_detector_returns_fixed_box():
    detector = FakeDetector()
    assert detector.detect(object()) == [(50, 50, 200, 200)]
