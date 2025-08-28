"""
Telemetry stub.

Lightweight in-memory counter/gauge store with no external IO. Intended
for drop-in replacement by a real metrics backend in later milestones.
"""

from __future__ import annotations


class Telemetry:
    def __init__(self) -> None:
        self.counters: dict[str, int] = {}
        self.gauges: dict[str, float] = {}

    def inc(self, name: str, value: int = 1) -> None:
        self.counters[name] = self.counters.get(name, 0) + value

    def set_gauge(self, name: str, value: float) -> None:
        self.gauges[name] = float(value)
