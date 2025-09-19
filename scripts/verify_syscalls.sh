#!/usr/bin/env sh
set -eu

if ! command -v strace >/dev/null 2>&1; then
  echo "strace not found; install it" >&2
  exit 127
fi

mkdir -p artifacts bench/fixture bench/out

python scripts/build_fixture.py --seed 7 --out bench/fixture --n 32

REPORT="artifacts/syscall_report.txt"
: >"$REPORT"

set +e
strace -f -qq -tt -e trace=network -o "$REPORT" \
  bash -lc 'latvision eval --input bench/fixture --output bench/out --warmup 0 --unknown-rate-band 0.0,1.0'
rc=$?
set -e

if [ -s "$REPORT" ]; then
  echo "❌ network syscalls detected" >&2
  head -n 20 "$REPORT" >&2 || true
  exit 1
fi

if [ "$rc" -ne 0 ]; then
  echo "❌ eval failed under strace (rc=$rc)" >&2
  exit "$rc"
fi

echo "✅ no network syscalls detected"
