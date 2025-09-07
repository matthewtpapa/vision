# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 The Vision Authors
from latency_vision import Embedder


def test_embedder_returns_fixed_vector():
    embedder = Embedder()
    embedding = embedder.embed(object())
    assert embedding == [0.0] * 128
