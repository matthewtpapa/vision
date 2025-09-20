#!/usr/bin/env python
import argparse
import json
import os
import random

ap = argparse.ArgumentParser()
ap.add_argument("--out", default="bench/oracle_fixture")
ap.add_argument("--n", type=int, default=500)
ap.add_argument("--dim", type=int, default=32)
ap.add_argument("--seed", type=int, default=7)
a = ap.parse_args()

os.makedirs(a.out, exist_ok=True)
random.seed(a.seed)

with (
    open(f"{a.out}/bank.jsonl", "w") as bank_file,
    open(f"{a.out}/queries.jsonl", "w") as queries_file,
):
    for i in range(100):
        vec = [0.0] * a.dim
        vec[i % a.dim] = 1.0
        bank_file.write(json.dumps({"qid": f"Q{i + 1}", "vec": vec, "alpha": 1.0}) + "\n")
    for _ in range(a.n):
        i = random.randrange(100)
        vec = [0.0] * a.dim
        vec[i % a.dim] = 1.0
        queries_file.write(json.dumps({"qid": f"Q{i + 1}", "vec": vec}) + "\n")
