import subprocess
import sys
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO

from vision import __version__


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    from vision.cli import main

    out = StringIO()
    err = StringIO()
    code = 0
    try:
        with redirect_stdout(out), redirect_stderr(err):
            main(list(args))
    except SystemExit as exc:  # pragma: no cover
        code = int(exc.code)
    return subprocess.CompletedProcess(
        args=[sys.executable, "-m", "vision", *args],
        returncode=code,
        stdout=out.getvalue(),
        stderr=err.getvalue(),
    )


def test_hello_outputs_version() -> None:
    cp = run_cli("hello")
    assert cp.returncode == 0
    assert f"Latency Vision {__version__}" in cp.stdout
    assert "Python" in cp.stdout
    assert "OS:" in cp.stdout
