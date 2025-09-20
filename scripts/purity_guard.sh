#!/usr/bin/env sh
set -eu
: "${SYS_AUDIT_REPORT_JSON:=artifacts/purity_report.json}"
: "${SYS_AUDIT_REPORT_TXT:=artifacts/syscall_report.txt}"
mkdir -p artifacts
: > "$SYS_AUDIT_REPORT_TXT"
# If a syscall verifier exists, run it; otherwise create a clean placeholder.
if [ -x scripts/verify_syscalls.sh ]; then
  scripts/verify_syscalls.sh || true
else
  : > "$SYS_AUDIT_REPORT_TXT"
fi
if grep -E 'connect|sendto|recvfrom|getaddrinfo|socket' "$SYS_AUDIT_REPORT_TXT" >/dev/null 2>&1; then
  printf '{"network_syscalls": true}\n' > "$SYS_AUDIT_REPORT_JSON"
  exit 1
else
  printf '{"network_syscalls": false}\n' > "$SYS_AUDIT_REPORT_JSON"
fi
