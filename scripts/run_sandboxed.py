#!/usr/bin/env python
"""Run a command under a lightweight sandbox and emit a purity report."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Iterable, List

from latency_vision.schemas import SCHEMA_VERSION

FORBIDDEN_EVENTS = {"connect", "socket_connect", "getaddrinfo"}
STRACE_FORBIDDEN_KEYWORDS = ("connect(", "getaddrinfo")



def _write_sitecustomize(path: Path) -> None:
    path.write_text(
        """
import json
import os
import socket

_LOG = os.environ.get("PURITY_LOG_PATH")

if _LOG:
    def _record(event: str, detail: str) -> None:
        with open(_LOG, "a", encoding="utf-8") as handle:
            json.dump({"event": event, "detail": detail}, handle)
            handle.write("\\n")

    _orig_getaddrinfo = socket.getaddrinfo
    def _patched_getaddrinfo(*args, **kwargs):
        host = args[0] if args else kwargs.get("host")
        _record("getaddrinfo", f"host={host}")
        return _orig_getaddrinfo(*args, **kwargs)

    socket.getaddrinfo = _patched_getaddrinfo

    _orig_connect = socket.socket.connect

    def _patched_connect(self, address):
        _record("socket_connect", f"address={address}")
        return _orig_connect(self, address)

    socket.socket.connect = _patched_connect
""",
        encoding="utf-8",
    )


def _run_with_strace(command: List[str], log_path: Path) -> tuple[int, list[dict[str, str]], str]:
    strace_bin = shutil.which("strace")
    unshare_bin = shutil.which("unshare")
    sandbox_mode = "strace-only"
    if strace_bin is None:
        # Fall back to Python sitecustomize hooking.
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            sitecustomize = temp_path / "sitecustomize.py"
            _write_sitecustomize(sitecustomize)
            env = os.environ.copy()
            env["PYTHONPATH"] = str(temp_path) + os.pathsep + env.get("PYTHONPATH", "")
            env["PURITY_LOG_PATH"] = str(log_path)
            result = subprocess.run(command, env=env, check=False)
        events = []
        if log_path.exists():
            events = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines() if line]
        return result.returncode, events, sandbox_mode

    log_path.parent.mkdir(parents=True, exist_ok=True)
    strace_cmd = [strace_bin, "-f", "-o", str(log_path)] + command
    if unshare_bin is not None:
        sandbox_mode = "unshare"
        wrapped = [
            unshare_bin,
            "--map-root-user",
            "--user",
            "--mount-proc",
            "--net",
            "--pid",
            "--fork",
            "--",
        ] + strace_cmd
    else:
        wrapped = strace_cmd
    result = subprocess.run(wrapped, check=False)
    events: list[dict[str, str]] = []
    if log_path.exists():
        for line in log_path.read_text(encoding="utf-8").splitlines():
            if any(token in line for token in STRACE_FORBIDDEN_KEYWORDS):
                events.append({"event": "strace", "detail": line.strip()})
    return result.returncode, events, sandbox_mode


def run_sandboxed(command: List[str], report_path: Path) -> int:
    log_path = Path("artifacts/purity_trace.log")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    if log_path.exists():
        log_path.unlink()
    returncode, events, mode = _run_with_strace(command, log_path)

    offenders = [event for event in events if event.get("event") in FORBIDDEN_EVENTS]
    offenders.extend(
        {
            "event": "strace",
            "detail": event["detail"],
        }
        for event in events
        if event.get("event") == "strace"
    )

    report = {
        "schema_version": SCHEMA_VERSION,
        "sandbox_mode": mode,
        "command": command,
        "returncode": returncode,
        "offending": offenders,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if returncode != 0:
        return returncode
    if offenders:
        return 1
    return 0


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", default="artifacts/purity_report.json")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    if not args.command:
        parser.error("a command to execute must be provided after '--'")
    if args.command[0] == "--":
        args.command = args.command[1:]
    return args


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    return run_sandboxed(args.command, Path(args.report))


if __name__ == "__main__":
    sys.exit(main())
