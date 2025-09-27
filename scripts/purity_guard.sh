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

if [ -f artifacts/purity_report.json ]; then
    # Validate offender shape (array of strings or objects with event/detail)
    jq -e '
      (has("offenders") or has("offending")) and
      ((.offenders // .offending) | type=="array") and (
        ((.offenders // .offending) | length) == 0 or
        ((.offenders // .offending) | map(((type=="object") and has("event") and has("detail")) or (type=="string")) | min)
      )
    ' artifacts/purity_report.json > /dev/null || {
      echo "Invalid offenders format in purity_report.json" >&2
      exit 1
    }

    offenders_path="artifacts/purity_offenders.txt"

    # Fail if any offenders present; write a human-readable list
    if ! jq -e '(.offenders // .offending // []) | length == 0' artifacts/purity_report.json > /dev/null; then
      jq -r '(.offenders // .offending // [])[]? | (if type=="object" and (.event? and .detail?) then "\(.event)  \(.detail)" else tostring end)' \
        artifacts/purity_report.json > "${offenders_path}"
      echo "Network offenders detected" >&2
      exit 1
    else
      : > "${offenders_path}"
    fi
fi

if [ "$status" -ne 0 ]; then
    exit "$status"
fi

[[ -f artifacts/purity_report.json ]] || { echo "missing purity report" >&2; exit 1; }

if jq -e '.network_syscalls == true' artifacts/purity_report.json >/dev/null 2>&1; then
    echo "network syscalls detected; see ${offenders_path}" >&2
    exit 1
fi

echo "purity ok"
