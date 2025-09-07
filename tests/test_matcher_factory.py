# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 The Vision Authors
from __future__ import annotations

import builtins

import pytest

pytest.importorskip("numpy")

from latency_vision.matcher.factory import build_matcher
from latency_vision.matcher.py_fallback import NumpyMatcher


def test_factory_uses_numpy_when_faiss_missing(monkeypatch) -> None:
    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name.endswith("faiss_backend"):
            raise ImportError("mocked missing faiss")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    matcher = build_matcher(3)
    assert isinstance(matcher, NumpyMatcher)
