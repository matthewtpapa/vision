# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 The Vision Authors
import pytest

import latency_vision.telemetry as telemetry


def test_stage_timer_records_and_summarizes(monkeypatch):
    tel = telemetry.Telemetry()
    times = iter([0, 2_000_000, 5_000_000, 8_000_000])
    monkeypatch.setattr(telemetry, "now_ns", lambda: next(times))

    with telemetry.StageTimer(tel, "embed"):
        pass
    with telemetry.StageTimer(tel, "embed"):
        pass

    summary = tel.summary()["embed"]
    assert summary["count"] == 2
    assert summary["mean_ms"] == pytest.approx(2.5, abs=1e-6)
    assert summary["max_ms"] == pytest.approx(3.0, abs=1e-6)

    csv = tel.to_csv().splitlines()
    assert csv[0] == "stage,count,total_ms,mean_ms,max_ms"
    assert csv[1] == "embed,2,5.0,2.5,3.0"
