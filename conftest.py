# SPDX-License-Identifier: Apache-2.0
import sys
from pathlib import Path

# Ensure tests can import the package without installation by adding the
# ``src`` directory to ``sys.path`` at runtime.
ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
