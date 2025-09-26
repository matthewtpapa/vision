#!/usr/bin/env python3
import os, json
snap = {k:v for k,v in os.environ.items() if k in [
"PYTHONHASHSEED","VISION_SEED","OMP_NUM_THREADS","OPENBLAS_NUM_THREADS",
"MKL_NUM_THREADS","NUMEXPR_NUM_THREADS","VISION_TIME_SOURCE","VISION_CROP_EXPAND_PCT",
"VISION_CROP_SIZE","VISION_LETTERBOX_VAL","TZ","PYTHONUTF8","LC_ALL",
"CUBLAS_WORKSPACE_CONFIG","CUDA_LAUNCH_BLOCKING","SOURCE_DATE_EPOCH"
]}
os.makedirs("artifacts", exist_ok=True)
with open("artifacts/seeds_applied.json","w") as f: json.dump(snap,f,indent=2,sort_keys=True)
print("ok")
