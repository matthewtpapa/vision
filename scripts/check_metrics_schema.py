#!/usr/bin/env python
"""Validate prove artifacts against the bundled JSON Schemas."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

try:
    from jsonschema import Draft202012Validator
except ImportError:  # pragma: no cover - jsonschema unavailable in sandbox
    import re

    class ValidationError(Exception):
        """Fallback validation error mirroring jsonschema's API."""

        def __init__(self, message: str, path: Sequence[object]):
            super().__init__(message)
            self.message = message
            self.path = list(path)

    class Draft202012Validator:  # type: ignore[override]
        """Minimal Draft 2020-12 validator used when jsonschema is unavailable."""

        def __init__(self, schema: dict[str, Any]):
            self._schema = schema

        def iter_errors(self, instance: Any):  # type: ignore[override]
            yield from _validate_with_schema(instance, self._schema, ())

    def _validate_with_schema(instance: Any, schema: dict[str, Any], path: Sequence[object]):
        path_tuple = tuple(path)
        schema_type = schema.get("type")
        if schema_type == "object":
            if not isinstance(instance, dict):
                yield ValidationError("value is not an object", path_tuple)
                return
            required = schema.get("required", [])
            for key in required:
                if key not in instance:
                    yield ValidationError(f"missing required property '{key}'", path_tuple + (key,))
            properties = schema.get("properties", {})
            if schema.get("additionalProperties", True) is False:
                for key in instance:
                    if key not in properties:
                        yield ValidationError(
                            f"additional property '{key}' is not allowed",
                            path_tuple + (key,),
                        )
            for key, subschema in properties.items():
                if key in instance:
                    yield from _validate_with_schema(instance[key], subschema, path_tuple + (key,))
            return
        if schema_type == "array":
            if not isinstance(instance, list):
                yield ValidationError("value is not an array", path_tuple)
                return
            min_items = schema.get("minItems")
            if isinstance(min_items, int) and len(instance) < min_items:
                yield ValidationError(f"array has fewer than {min_items} items", path_tuple)
            if schema.get("uniqueItems"):
                seen = set()
                for index, item in enumerate(instance):
                    marker = json.dumps(item, sort_keys=True, separators=(",", ":"))
                    if marker in seen:
                        yield ValidationError("array items are not unique", path_tuple + (index,))
                    else:
                        seen.add(marker)
            item_schema = schema.get("items")
            if isinstance(item_schema, dict):
                for index, item in enumerate(instance):
                    yield from _validate_with_schema(item, item_schema, path_tuple + (index,))
            return
        if schema_type == "string":
            if not isinstance(instance, str):
                yield ValidationError("value is not a string", path_tuple)
                return
            pattern = schema.get("pattern")
            if pattern and not re.fullmatch(pattern, instance):
                yield ValidationError("string does not match required pattern", path_tuple)
            enum = schema.get("enum")
            if enum and instance not in enum:
                yield ValidationError("string is not an allowed value", path_tuple)
            return
        if schema_type == "integer":
            if not isinstance(instance, int) or isinstance(instance, bool):
                yield ValidationError("value is not an integer", path_tuple)
                return
            minimum = schema.get("minimum")
            if minimum is not None and instance < minimum:
                yield ValidationError("integer is below the minimum", path_tuple)
            maximum = schema.get("maximum")
            if maximum is not None and instance > maximum:
                yield ValidationError("integer exceeds the maximum", path_tuple)
            return
        if schema_type == "number":
            if not isinstance(instance, int | float) or isinstance(instance, bool):
                yield ValidationError("value is not numeric", path_tuple)
                return
            minimum = schema.get("minimum")
            if minimum is not None and float(instance) < float(minimum):
                yield ValidationError("number is below the minimum", path_tuple)
            maximum = schema.get("maximum")
            if maximum is not None and float(instance) > float(maximum):
                yield ValidationError("number exceeds the maximum", path_tuple)
            return
        if schema_type == "boolean":
            if not isinstance(instance, bool):
                yield ValidationError("value is not a boolean", path_tuple)
            return
        # Fallback: recurse into properties if provided even without explicit type.
        for key, subschema in schema.get("properties", {}).items():
            if isinstance(instance, dict) and key in instance:
                yield from _validate_with_schema(instance[key], subschema, path_tuple + (key,))


from latency_vision.schemas import load_schema

ROOT = Path(__file__).resolve().parent.parent


def _load_json(path: Path) -> Any:
    if not path.is_file():
        raise SystemExit(f"missing artifact for schema validation: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _validate(instance: Any, schema_name: str, *, label: str) -> None:
    schema = load_schema(schema_name)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(instance), key=lambda err: list(err.path))
    if errors:
        messages = []
        for error in errors:
            location = " / ".join(str(part) for part in error.path)
            prefix = f"{label}" if not location else f"{label} -> {location}"
            messages.append(f"{prefix}: {error.message}")
        raise SystemExit("schema validation failed:\n" + "\n".join(messages))


def main() -> None:
    offline = _load_json(ROOT / "bench/oracle_stats.json")
    _validate(offline, "oracle_stats.schema.json", label="bench/oracle_stats.json")

    e2e = _load_json(ROOT / "bench/oracle_e2e.json")
    _validate(e2e, "oracle_e2e.schema.json", label="bench/oracle_e2e.json")

    purity = _load_json(ROOT / "artifacts/purity_report.json")
    _validate(purity, "purity_report.schema.json", label="artifacts/purity_report.json")

    manifest_path = ROOT / "data/bench/manifest.json"
    manifest = _load_json(manifest_path)
    _validate(manifest, "metrics_manifest.schema.json", label="data/bench/manifest.json")

    # Validate each JSONL line in the evidence ledger
    ledger_path = ROOT / "logs/evidence_ledger.jsonl"
    if ledger_path.exists():
        schema = load_schema("evidence_ledger.schema.jsonl")
        validator = Draft202012Validator(schema)
        with ledger_path.open("r", encoding="utf-8") as fh:
            for i, line in enumerate(fh, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError as exc:  # pragma: no cover - trivial failure
                    raise SystemExit(f"ledger parse error at line {i}: {exc}") from exc
                errors = sorted(validator.iter_errors(obj), key=lambda e: list(e.path))
                if errors:
                    first = errors[0]
                    loc = " / ".join(str(p) for p in first.path)
                    where = f" @ {loc}" if loc else ""
                    raise SystemExit(
                        f"ledger schema validation failed at line {i}{where}: {first.message}"
                    )

    print("all schemas validated")


if __name__ == "__main__":
    main()
