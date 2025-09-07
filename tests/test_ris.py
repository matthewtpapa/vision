# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 The Vision Authors
from latency_vision import ReverseImageSearchStub


def test_ris_stub_returns_empty_list_and_records_last_query():
    ris = ReverseImageSearchStub()
    out = ris.search({"foo": "bar"})
    assert out == []
    assert ris.last_query == {"input": {"foo": "bar"}}
