from vision import Telemetry


def test_telemetry_counters_and_gauges():
    t = Telemetry()
    t.inc("frames")
    t.inc("frames", 2)
    t.set_gauge("latency_ms", 7.5)
    assert t.counters["frames"] == 3
    assert t.gauges["latency_ms"] == 7.5
