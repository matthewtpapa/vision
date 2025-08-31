# SPDX-License-Identifier: Apache-2.0
from vision.fake_detector import FakeDetector


def test_fake_detector_returns_fixed_box():
    detector = FakeDetector()
    assert detector.detect(object()) == [(50, 50, 200, 200)]
