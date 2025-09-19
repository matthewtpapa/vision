#!/usr/bin/env sh
set -eu

command -v strace >/dev/null 2>&1 || { echo "strace not found; install it" >&2; exit 127; }

FIXTURE_DIR=${SYS_AUDIT_FIXTURE:-bench/fixture}
OUTPUT_DIR=${SYS_AUDIT_OUTPUT:-bench/out}
REPORT=${SYS_AUDIT_REPORT:-artifacts/syscall_report.txt}
SEED=${SYS_AUDIT_SEED:-7}
COUNT=${SYS_AUDIT_N:-32}
BAND=${SYS_AUDIT_BAND:-0.0,1.0}

mkdir -p artifacts "$FIXTURE_DIR" "$OUTPUT_DIR"

python scripts/build_fixture.py --seed "$SEED" --out "$FIXTURE_DIR" --n "$COUNT"

: >"$REPORT"

CMD="latvision eval --input \"$FIXTURE_DIR\" --output \"$OUTPUT_DIR\" --warmup 0 --unknown-rate-band $BAND"

set +e
strace -f -qq -tt -e trace=network -o "$REPORT" \
  bash -lc "$CMD"
rc=$?
set -e

if [ -s "$REPORT" ]; then
  echo "❌ network syscalls detected" >&2
  head -n 50 "$REPORT" >&2 || true
  exit 1
fi

if [ "$rc" -ne 0 ]; then
  echo "❌ eval failed under strace (rc=$rc)" >&2
  exit "$rc"
fi

echo "✅ no network syscalls detected"

# Optional (disabled): trace file I/O patterns for the hot loop
# strace -f -qq -tt -e trace=file -o artifacts/syscall_file_report.txt \
#   bash -lc "$CMD"
# grep -E "O_WRONLY|O_RDWR" artifacts/syscall_file_report.txt && { echo "warn: write I/O during eval"; true; } || true
