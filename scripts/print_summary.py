# SPDX-License-Identifier: Apache-2.0
import argparse
import json


def _get(d, keys, default="N/A"):
    cur = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("metrics", help="Path to metrics.json")
    args = ap.parse_args()

    with open(args.metrics, encoding="utf-8") as f:
        m = json.load(f)
    c = m.get("controller", {})

    rows = [
        ("fps", m.get("fps", "N/A")),
        ("p50 (ms)", m.get("p50", "N/A")),
        ("p95 (ms)", m.get("p95", "N/A")),
        ("p99 (ms)", m.get("p99", "N/A")),
        (
            "frames processed",
            f"{_get(c, ['frames_processed'])}/{_get(c, ['frames_total'])}",
        ),
        (
            "stride start→end",
            f"{_get(c, ['start_stride'])}→{_get(c, ['end_stride'])}",
        ),
        ("backend", m.get("backend_selected", "N/A")),
        ("kb_size", m.get("kb_size", "N/A")),
    ]
    w = max(len(k) for k, _ in rows) + 2
    for k, v in rows:
        print(f"{k:<{w}}{v}")

    fps = m.get("fps")
    p95 = m.get("p95")
    verdict = "N/A"
    if isinstance(fps, (int | float)) and isinstance(p95, (int | float)):
        verdict = "PASS" if (p95 <= 33 and fps >= 25) else "FAIL"
    print(f"\nVERDICT: {verdict}")


if __name__ == "__main__":
    main()
