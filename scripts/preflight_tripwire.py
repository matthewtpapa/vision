#!/usr/bin/env python3
import json, re, subprocess
from pathlib import Path

def sh(cmd):
    return subprocess.check_output(cmd, shell=True, text=True).strip()

# 1) No tracked artifacts/logs/gate_summary
tracked = sh("git ls-files 'artifacts/*' 'logs/*' 'bench/*.json' 'bench/*.jsonl' || true").splitlines()
root_gs = "gate_summary.txt" in sh("git ls-files || true").splitlines()
errs = []
if tracked:
    errs.append(f"Tracked generated files: {tracked}")
if root_gs:
    errs.append("Tracked gate_summary.txt at repo root")

# 2) No ellipses/theater in code/Make/scripts
bad = []
for p in Path('.').rglob('*'):
    if not p.is_file():
        continue
    if not any(str(p).startswith(d) for d in ("src/", "scripts/", "Makefile", ".github/workflows/verify.yml")):
        continue
    try:
        txt = p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        continue
    if re.search(r'(^|\s)\.\.\.(\s|$)', txt):
        bad.append(str(p))
if bad:
    errs.append(f"Files contain '...': {bad}")

# 3) Verify required CI targets exist in Makefile
mk = Path("Makefile").read_text()
for target in ["bench", "purity", "schema-check", "metrics-hash", "metrics-hash-twice", "prove"]:
    if not re.search(rf'^{target}:(?:\s|$)', mk, re.M):
        errs.append(f"Missing Make target: {target}")

if errs:
    raise SystemExit("TRIPWIRE FAIL:\n- " + "\n- ".join(errs))
print("TRIPWIRE OK")
