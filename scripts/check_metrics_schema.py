#!/usr/bin/env python3
"""Validate oracle benchmark metrics against the JSON schema."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from jsonschema import Draft202012Validator
except Exception:  # pragma: no cover - fallback when dependency unavailable

    class Draft202012Validator:  # type: ignore[override]
        """Minimal validator supporting the keywords used in our schema."""

        def __init__(self, schema: dict[str, Any]) -> None:
            self._schema = schema

        def iter_errors(self, instance: Any):  # type: ignore[override]
            errors: list[_SimpleError] = []
            _validate_schema(self._schema, instance, (), errors)
            return iter(errors)

    class _SimpleError:
        def __init__(self, path: tuple[Any, ...], message: str) -> None:
            self.path = path
            self.message = message

    def _is_number(value: Any) -> bool:
        return isinstance(value, int | float) and not isinstance(value, bool)

    def _validate_schema(
        schema: dict[str, Any],
        instance: Any,
        path: tuple[Any, ...],
        errors: list[_SimpleError],
    ) -> None:
        expected_type = schema.get("type")
        if expected_type == "object":
            if not isinstance(instance, dict):
                errors.append(_SimpleError(path, "is not of type 'object'"))
                return
            required = schema.get("required", [])
            for key in required:
                if key not in instance:
                    errors.append(_SimpleError(path + (key,), "is a required property"))
            properties = schema.get("properties", {})
            additional = schema.get("additionalProperties", True)
            for key, value in instance.items():
                if key in properties:
                    _validate_schema(properties[key], value, path + (key,), errors)
                elif additional is False:
                    errors.append(_SimpleError(path + (key,), "additional property not allowed"))
        elif expected_type == "number":
            if not _is_number(instance):
                errors.append(_SimpleError(path, "is not of type 'number'"))
                return

        if "minimum" in schema and _is_number(instance):
            minimum = schema["minimum"]
            if instance < minimum:
                errors.append(
                    _SimpleError(
                        path,
                        f"{instance} is less than the minimum of {minimum}",
                    )
                )
        if "maximum" in schema and _is_number(instance):
            maximum = schema["maximum"]
            if instance > maximum:
                errors.append(
                    _SimpleError(
                        path,
                        f"{instance} is greater than the maximum of {maximum}",
                    )
                )


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "metrics.schema.json"
ARTIFACTS_DIR = ROOT / "artifacts"
REPORT_PATH = ARTIFACTS_DIR / "metrics_schema_report.txt"


@dataclass(frozen=True)
class Target:
    """A metrics artifact and the schema definition used to validate it."""

    path: Path
    pointer: str


TARGETS: tuple[Target, ...] = (
    Target(ROOT / "bench" / "oracle_stats.json", "#/$defs/oracleStats"),
    Target(ROOT / "bench" / "oracle_e2e.json", "#/$defs/oracleE2E"),
)


def _resolve_pointer(schema: Any, pointer: str) -> Any:
    if not pointer.startswith("#/"):
        raise ValueError(f"Only local JSON pointers are supported (got {pointer!r}).")
    parts = pointer[2:].split("/") if pointer != "#" else []
    node: Any = schema
    for raw_key in parts:
        key = raw_key.replace("~1", "/").replace("~0", "~")
        if not isinstance(node, dict) or key not in node:
            raise KeyError(f"Pointer {pointer!r} not found in schema at {key!r}.")
        node = node[key]
    return node


def _validate_target(schema: dict[str, Any], target: Target) -> tuple[bool, str]:
    if not target.path.exists():
        return False, f"{target.path.relative_to(ROOT)}: missing file"
    data = json.loads(target.path.read_text(encoding="utf-8"))
    try:
        sub_schema = _resolve_pointer(schema, target.pointer)
    except KeyError as exc:  # pragma: no cover - defensive guard
        return False, f"{target.path.relative_to(ROOT)}: schema pointer error: {exc}"
    validator = Draft202012Validator(sub_schema)
    errors = sorted(validator.iter_errors(data), key=lambda e: e.path)
    if errors:
        first = errors[0]
        loc = "/".join(str(x) for x in first.path)
        prefix = f"{target.path.relative_to(ROOT)}: FAIL"
        if loc:
            return False, f"{prefix} ({loc}) {first.message}"
        return False, f"{prefix} {first.message}"
    return True, f"{target.path.relative_to(ROOT)}: OK"


def main() -> int:
    if not SCHEMA_PATH.exists():
        print(f"Schema not found: {SCHEMA_PATH}", file=sys.stderr)
        return 2
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    results: list[str] = []
    success = True
    for target in TARGETS:
        ok, message = _validate_target(schema, target)
        results.append(message)
        if not ok:
            success = False
    REPORT_PATH.write_text("\n".join(results) + "\n", encoding="utf-8")
    if not success:
        print("Schema validation failed. See artifacts/metrics_schema_report.txt", file=sys.stderr)
        return 1
    print("Schema validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
