#!/usr/bin/env python
"""Check SLO gates against generated metrics."""

from __future__ import annotations

import json
from pathlib import Path

from latency_vision.slo import SLOGates, assert_slo


def main() -> None:
    offline = json.loads(Path("bench/oracle_stats.json").read_text(encoding="utf-8"))
    e2e = json.loads(Path("bench/oracle_e2e.json").read_text(encoding="utf-8"))
    assert_slo(offline_stats=offline, e2e_stats=e2e, gates=SLOGates())
    print("slo gates ok")


if __name__ == "__main__":
    main()
