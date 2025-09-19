from __future__ import annotations

import sys

from . import __version__
from .cli import main as cli_main


def main() -> int:
    args = sys.argv[1:]
    if args == ["--version"]:
        print(f"Latency Vision {__version__}")
        return 0
    return cli_main(args)


if __name__ == "__main__":
    raise SystemExit(main())
