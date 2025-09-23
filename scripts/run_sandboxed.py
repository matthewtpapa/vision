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
from collections.abc import Iterable
from pathlib import Path

from latency_vision.schemas import SCHEMA_VERSION

FORBIDDEN_EVENTS = {
    "connect",
    "socket_connect",
    "getaddrinfo",
    "sendto",
    "recvfrom",
    "socket",
}
STRACE_FORBIDDEN_KEYWORDS = (
    "connect(",
    "getaddrinfo",
    "sendto(",
    "recvfrom(",
    "socket(",
)


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

    _orig_socket_class = socket.socket

    class _PatchedSocket(_orig_socket_class):
        def __init__(self, *args, **kwargs):
            family = args[0] if args else kwargs.get("family")
            type_ = args[1] if len(args) > 1 else kwargs.get("type")
            proto = args[2] if len(args) > 2 else kwargs.get("proto")
            detail = f"family={family},type={type_},proto={proto}"
            _record("socket", detail)
            super().__init__(*args, **kwargs)

        def connect(self, address):
            _record("socket_connect", f"address={address}")
            return _orig_socket_class.connect(self, address)

        def sendto(self, data, *args, **kwargs):
            address = None
            if args:
                address = args[0]
            elif "address" in kwargs:
                address = kwargs["address"]
            _record("sendto", f"address={address}")
            return _orig_socket_class.sendto(self, data, *args, **kwargs)

        def recvfrom(self, *args, **kwargs):
            bufsize = args[0] if args else kwargs.get("bufsize")
            _record("recvfrom", f"bufsize={bufsize}")
            return _orig_socket_class.recvfrom(self, *args, **kwargs)

    socket.socket = _PatchedSocket
    socket.SocketType = _PatchedSocket
""",
        encoding="utf-8",
    )


def _run_with_strace(command: list[str], log_path: Path) -> tuple[int, list[dict[str, str]], str]:
    strace_bin = shutil.which("strace")
    unshare_bin = shutil.which("unshare")
    sandbox_mode = "strace-only"
    if strace_bin is None:
        if os.environ.get("PURITY_ALLOW_WEAK_FALLBACK") != "1":
            raise SystemExit("strace is required for the purity sandbox to run")
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            site_dir = (
                temp_path
                / "lib"
                / f"python{sys.version_info.major}.{sys.version_info.minor}"
                / "site-packages"
            )
            site_dir.mkdir(parents=True, exist_ok=True)
            sitecustomize = site_dir / "sitecustomize.py"
            _write_sitecustomize(sitecustomize)
            env = os.environ.copy()
            existing_pythonpath = env.get("PYTHONPATH", "")
            if existing_pythonpath:
                env["PYTHONPATH"] = os.pathsep.join([str(temp_path), existing_pythonpath])
            else:
                env["PYTHONPATH"] = str(temp_path)
            env["PYTHONUSERBASE"] = str(temp_path)
            env["PURITY_LOG_PATH"] = str(log_path)
            result = subprocess.run(command, env=env, check=False)
        events = []
        if log_path.exists():
            events = [
                json.loads(line)
                for line in log_path.read_text(encoding="utf-8").splitlines()
                if line
            ]
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
        result = subprocess.run(
            wrapped,
            check=False,
            capture_output=True,
            text=True,
        )
        if result.stdout:
            sys.stdout.write(result.stdout)
        if result.stderr:
            sys.stderr.write(result.stderr)
        if result.returncode != 0 and (
            "Operation not permitted" in (result.stderr or "")
            or "permission denied" in (result.stderr or "").lower()
        ):
            sandbox_mode = "strace-only"
            if log_path.exists():
                log_path.unlink()
            result = subprocess.run(strace_cmd, check=False)
        elif result.returncode != 0:
            return result.returncode, [], sandbox_mode
    else:
        result = subprocess.run(strace_cmd, check=False)
    events: list[dict[str, str]] = []
    if log_path.exists():
        for line in log_path.read_text(encoding="utf-8").splitlines():
            if any(token in line for token in STRACE_FORBIDDEN_KEYWORDS):
                events.append({"event": "strace", "detail": line.strip()})
    return result.returncode, events, sandbox_mode


def run_sandboxed(command: list[str], report_path: Path) -> int:
    log_path = Path("artifacts/purity_trace.log")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    if log_path.exists():
        log_path.unlink()
    returncode, events, mode = _run_with_strace(command, log_path)

    offenders: list[dict[str, str]] = []
    for event in events:
        if not isinstance(event, dict):
            continue
        event_name = event.get("event")
        if event_name not in FORBIDDEN_EVENTS and event_name != "strace":
            continue
        detail = event.get("detail")
        offenders.append(
            {
                "event": str(event_name),
                "detail": "" if detail is None else str(detail),
            }
        )

    network_syscalls = bool(offenders)

    report = {
        "schema_version": SCHEMA_VERSION,
        "sandbox_mode": mode,
        "command": command,
        "returncode": returncode,
        "network_syscalls": network_syscalls,
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
