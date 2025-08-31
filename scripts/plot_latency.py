# SPDX-License-Identifier: Apache-2.0
import argparse
import json

import matplotlib.pyplot as plt


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--metrics", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    with open(args.metrics, encoding="utf-8") as f:
        m = json.load(f)

    stats = {k: m.get(k) for k in ("p50", "p95", "p99")}
    items = [(k, v) for k, v in stats.items() if isinstance(v, (int | float))]
    plt.figure()
    if items:
        labels, values = zip(*items)
        plt.bar(labels, values)
        plt.title("Latency percentiles (ms)")
        plt.ylabel("ms")
    else:
        txt = "\n".join([f"{k}: {stats.get(k, 'N/A')}" for k in ("p50", "p95", "p99")])
        plt.text(0.1, 0.5, txt, fontsize=12)
        plt.axis("off")
    plt.tight_layout()
    plt.savefig(args.out)


if __name__ == "__main__":
    main()
