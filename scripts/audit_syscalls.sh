#!/usr/bin/env sh
set -eu

command -v strace >/dev/null 2>&1 || { echo "strace not found; install it" >&2; exit 127; }

mkdir -p artifacts bench/fixture bench/out

# Build a small offline fixture to exercise the hot loop.
python scripts/build_fixture.py --seed 42 --out bench/fixture --n 200

# Run eval under strace, tracing ONLY network syscalls from all threads/processes.
# Store a concise report for upload.
STRACE_OUT="artifacts/syscall_report.txt"
: > "$STRACE_OUT"

# Use bash -lc so shell aliases/env match CI shell; allow non-zero exit to be caught below.
set +e
strace -f -qq -tt -e trace=network -o "$STRACE_OUT" \
  bash -lc 'latvision eval --input bench/fixture --output bench/out --warmup 0 --unknown-rate-band 0.0,1.0'
RC=$?
set -e

# Count network syscalls; strace writes one line per syscall when any occur.
if [ -s "$STRACE_OUT" ]; then
  echo "❌ network syscalls detected in hot loop:" >&2
  head -n 50 "$STRACE_OUT" >&2 || true
  exit 1
fi

# Also fail if eval itself failed.
if [ "$RC" -ne 0 ]; then
  echo "❌ eval failed under strace (rc=$RC)" >&2
  exit $RC
fi

echo "✅ no network syscalls detected"

# Optional (disabled): sanity check file I/O patterns for the hot loop
# strace -f -qq -tt -e trace=file -o artifacts/syscall_file_report.txt \
#   bash -lc 'latvision eval --input bench/fixture --output bench/out --warmup 0 --unknown-rate-band 0.0,1.0'
# grep -E "O_WRONLY|O_RDWR" artifacts/syscall_file_report.txt && { echo "warn: write I/O during eval"; true; } || true
