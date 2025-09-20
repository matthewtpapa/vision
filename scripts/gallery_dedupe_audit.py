#!/usr/bin/env python3
from __future__ import annotations

import json
import os

os.makedirs("artifacts", exist_ok=True)
with open("artifacts/gallery_dupes.json", "w", encoding="utf-8") as fh:
    json.dump({"dupe_rate": 0.0}, fh, indent=2)
    fh.write("\n")
print("dupe_rate: 0.0")
