#!/usr/bin/env sh
set -eu
: "${SYS_AUDIT_REPORT_JSON:=artifacts/purity_report.json}"
: "${SYS_AUDIT_REPORT_TXT:=artifacts/syscall_report.txt}"
export SYS_AUDIT_REPORT_JSON
export SYS_AUDIT_REPORT_TXT
mkdir -p artifacts

if [ -x scripts/verify_syscalls.sh ]; then
  scripts/verify_syscalls.sh "$@"
else
  python scripts/run_sandboxed.py -- "$@"
fi

if [ ! -f "$SYS_AUDIT_REPORT_JSON" ]; then
  echo "❌ missing purity report at $SYS_AUDIT_REPORT_JSON" >&2
  exit 1
fi

python - <<'PY'
import json
import os
import sys

report_path = os.environ["SYS_AUDIT_REPORT_JSON"]
data = json.loads(open(report_path, encoding="utf-8").read())
if data.get("network_syscalls"):
    sys.exit(1)
PY
