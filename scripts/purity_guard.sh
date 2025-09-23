#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

mkdir -p artifacts

if ! command -v strace >/dev/null 2>&1; then
    if [ "$(uname -s)" != "Linux" ]; then
        echo "purity guard requires strace or a POSIX socket hook; aborting." >&2
        exit 1
    fi
fi

set +e
PYTHONPATH="${REPO_ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}" \
    python scripts/run_sandboxed.py --report artifacts/purity_report.json -- make bench
status=$?
set -e

offenders_path="artifacts/purity_offenders.txt"
: >"${offenders_path}"
if [ -f artifacts/purity_report.json ]; then
    jq -e '
      .offending | (type=="array") and
      all(.[]; (type=="object") and has("event") and has("detail"))
    ' artifacts/purity_report.json > /dev/null || {
      echo "Invalid offenders format"; exit 1; }

    jq -e '.offending | length == 0' artifacts/purity_report.json > /dev/null || {
      jq -r '.offending[] | "\(.event): \(.detail)"' artifacts/purity_report.json \
        > "${offenders_path}"
      echo "Network offenders detected"; exit 1; }
fi

if [ "$status" -ne 0 ]; then
    exit "$status"
fi

if jq -e '.network_syscalls == true' artifacts/purity_report.json >/dev/null 2>&1; then
    echo "network syscalls detected; see ${offenders_path}" >&2
    exit 1
fi

echo "purity ok"
