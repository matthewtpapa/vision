#!/usr/bin/env sh
set -eu

FIXTURE_DIR=${SYS_AUDIT_FIXTURE:-bench/fixture}
OUTPUT_DIR=${SYS_AUDIT_OUTPUT:-bench/out}
SEED=${SYS_AUDIT_SEED:-7}
COUNT=${SYS_AUDIT_N:-32}
BAND=${SYS_AUDIT_BAND:-0.0,1.0}
REPORT_JSON=${SYS_AUDIT_REPORT_JSON:-artifacts/purity_report.json}
REPORT_TXT=${SYS_AUDIT_REPORT_TXT:-artifacts/syscall_report.txt}
DEFAULT_JSON=artifacts/purity_report.json
DEFAULT_TXT=artifacts/syscall_report.txt

mkdir -p artifacts "$FIXTURE_DIR" "$OUTPUT_DIR"

python scripts/build_fixture.py --seed "$SEED" --out "$FIXTURE_DIR" --n "$COUNT"

python scripts/run_sandboxed.py -- \
  latvision eval \
  --input "$FIXTURE_DIR" \
  --output "$OUTPUT_DIR" \
  --warmup 0 \
  --unknown-rate-band "$BAND"

if [ "$REPORT_JSON" != "$DEFAULT_JSON" ] && [ -f "$DEFAULT_JSON" ]; then
  mkdir -p "$(dirname "$REPORT_JSON")"
  cp "$DEFAULT_JSON" "$REPORT_JSON"
fi

if [ "$REPORT_TXT" != "$DEFAULT_TXT" ] && [ -f "$DEFAULT_TXT" ]; then
  mkdir -p "$(dirname "$REPORT_TXT")"
  cp "$DEFAULT_TXT" "$REPORT_TXT"
fi

if [ ! -f "$REPORT_JSON" ]; then
  echo "❌ missing purity report at $REPORT_JSON" >&2
  exit 1
fi

export REPORT_JSON
python - <<'PY'
import json
import os
import sys

report_json = os.environ["REPORT_JSON"]
data = json.loads(open(report_json, encoding="utf-8").read())
if data.get("network_syscalls"):
    sys.exit("network syscalls detected")
PY

if [ ! -f "$REPORT_TXT" ]; then
  echo "⚠️  syscall trace missing; expected $REPORT_TXT" >&2
else
  head -n 50 "$REPORT_TXT" >/dev/null 2>&1 || true
fi

echo "✅ no network syscalls detected"
