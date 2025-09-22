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

jq -r '.offending[]? | "\(.event)  \(.detail)"' artifacts/purity_report.json \
    > artifacts/purity_offenders.txt || true

if [ "$status" -ne 0 ]; then
    exit "$status"
fi

if jq -e '.network_syscalls == true' artifacts/purity_report.json >/dev/null 2>&1; then
    echo "network syscalls detected; see artifacts/purity_offenders.txt" >&2
    exit 1
fi

echo "purity ok"
