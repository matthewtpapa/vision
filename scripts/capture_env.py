#!/usr/bin/env python3
"""Capture deterministic seed environment variables."""

import json
import os
from pathlib import Path

SEED_KEYS = [
    "PYTHONHASHSEED",
    "VISION_SEED",
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "VISION_TIME_SOURCE",
    "VISION_CROP_EXPAND_PCT",
    "VISION_CROP_SIZE",
    "VISION_LETTERBOX_VAL",
    "TZ",
    "PYTHONUTF8",
    "LC_ALL",
    "CUBLAS_WORKSPACE_CONFIG",
    "CUDA_LAUNCH_BLOCKING",
    "SOURCE_DATE_EPOCH",
]


def main() -> None:
    snapshot = {key: os.environ[key] for key in SEED_KEYS if key in os.environ}

    artifacts_dir = Path("artifacts")
    artifacts_dir.mkdir(exist_ok=True)

    output_path = artifacts_dir / "seeds_applied.json"
    output_path.write_text(
        json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    print("ok")


if __name__ == "__main__":
    main()
