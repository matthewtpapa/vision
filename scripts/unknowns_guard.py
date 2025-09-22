#!/usr/bin/env python
# SPDX-License-Identifier: Apache-2.0
"""Guardrail to catch false accepts on unknown queries."""

from __future__ import annotations

import argparse

from latency_vision.guards import unknowns_false_accept_guard


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--samples",
        default="bench/e2e_samples.jsonl",
        help="Path to bench samples JSONL file.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.025,
        help="Maximum allowed false-accept rate (fraction).",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    unknowns_false_accept_guard(args.samples, threshold=args.threshold)
    print("unknowns guard ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
