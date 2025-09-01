# SPDX-License-Identifier: Apache-2.0
# Cross-version shims.
from __future__ import annotations

try:  # Py 3.11+
    from datetime import UTC as UTC  # type: ignore[attr-defined, unused-ignore]
except Exception:  # Py 3.10 fallback
    from datetime import timezone as _timezone

    UTC = _timezone.utc  # noqa: N816, UP017 (constant-like alias)
