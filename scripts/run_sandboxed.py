#!/usr/bin/env python3
"""Run a command with network sandboxing and syscall tracing."""

from __future__ import annotations

import json
import shlex
import subprocess
import sys
from pathlib import Path

NETWORK_SYSCALLS = (
    "connect",
    "sendto",
    "recvfrom",
    "socket",
    "getsockname",
    "getpeername",
)


def _reset_log(path: Path) -> None:
    """Ensure the syscall log exists and is owned by the current user."""
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.unlink(missing_ok=True)
    except TypeError:
        # Python <3.8 fallback – shouldn't occur but keep defensive.
        if path.exists():
            path.unlink()
    except PermissionError:
        # If we somehow can't unlink, leave the existing file in place.
        pass
    try:
        path.touch(exist_ok=True)
    except PermissionError:
        # As a last resort attempt to open for writing which will truncate/create.
        with open(path, "w", encoding="utf-8"):
            pass


def _detect_network_syscalls(path: Path) -> bool:
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                for name in NETWORK_SYSCALLS:
                    if f"{name}(" in line:
                        return True
    except FileNotFoundError:
        return False
    return False


def main(argv: list[str]) -> int:
    if "--" not in argv:
        print("usage: run_sandboxed.py -- <COMMAND ...>", file=sys.stderr)
        return 0

    sep_index = argv.index("--")
    command_parts = argv[sep_index + 1 :]
    if not command_parts:
        print("no command provided", file=sys.stderr)
        return 0

    artifacts_dir = Path("artifacts")
    artifacts_dir.mkdir(exist_ok=True)
    syscall_log = (artifacts_dir / "syscall_report.txt").resolve()
    report_path = artifacts_dir / "purity_report.json"

    command_str = shlex.join(command_parts)

    sandbox_mode = "unshare"
    need_fallback = False

    unshare_cmd = [
        "sudo",
        "unshare",
        "-n",
        "--",
        "strace",
        "-f",
        "-o",
        str(syscall_log),
        "-e",
        "trace=network",
        "bash",
        "-lc",
        command_str,
    ]

    try:
        _reset_log(syscall_log)
        result = subprocess.run(unshare_cmd, check=False)
        if result.returncode != 0:
            need_fallback = True
    except Exception as exc:  # pragma: no cover - defensive
        print(f"[run_sandboxed] unshare attempt failed: {exc}", file=sys.stderr)
        need_fallback = True

    if need_fallback:
        sandbox_mode = "strace-only"
        fallback_cmd = [
            "strace",
            "-f",
            "-o",
            str(syscall_log),
            "-e",
            "trace=network",
            "bash",
            "-lc",
            command_str,
        ]
        try:
            _reset_log(syscall_log)
            subprocess.run(fallback_cmd, check=False)
        except Exception as exc:  # pragma: no cover - defensive
            print(f"[run_sandboxed] strace-only execution failed: {exc}", file=sys.stderr)

    network_detected = _detect_network_syscalls(syscall_log)

    report = {
        "network_syscalls": bool(network_detected),
        "sandbox_mode": sandbox_mode,
    }
    try:
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    except Exception as exc:  # pragma: no cover - defensive
        print(f"[run_sandboxed] failed to write report: {exc}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
