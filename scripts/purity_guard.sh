#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

if ! command -v strace >/dev/null 2>&1; then
    if [ "$(uname -s)" != "Linux" ]; then
        echo "purity guard requires strace or a POSIX socket hook; aborting." >&2
        exit 1
    fi
fi

PYTHONPATH="${REPO_ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}" \
    python scripts/run_sandboxed.py --report artifacts/purity_report.json -- make bench
