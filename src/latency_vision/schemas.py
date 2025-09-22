"""Schema loader utilities for Latency Vision fixtures and reports."""

from __future__ import annotations

import json
from functools import cache
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1.0.0"


def _schemas_dir() -> Path:
    """Return the repository schema directory."""
    return Path(__file__).resolve().parents[2] / "schemas"


@cache
def load_schema(name: str) -> dict[str, Any]:
    """Load a JSON schema by filename.

    Parameters
    ----------
    name:
        Filename located under the top-level ``schemas`` directory.
    """

    schema_path = _schemas_dir() / name
    if not schema_path.is_file():
        raise FileNotFoundError(f"schema not found: {schema_path}")
    with schema_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def available_schemas() -> list[str]:
    """Return the list of bundled schema filenames."""

    directory = _schemas_dir()
    if not directory.exists():
        return []
    return sorted(str(path.name) for path in directory.glob("*.schema.json"))


__all__ = ["SCHEMA_VERSION", "available_schemas", "load_schema"]
