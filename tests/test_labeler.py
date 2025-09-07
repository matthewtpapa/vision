# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 The Vision Authors
from latency_vision import Labeler


def test_labeler_returns_unknown_label():
    labeler = Labeler()
    assert labeler.label(object()) == "unknown"
