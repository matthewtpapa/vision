#!/usr/bin/env python3
"""Generate a canonical metrics hash and payload artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from latency_vision.determinism import blas_fingerprint, quantize_float
from latency_vision.schemas import SCHEMA_VERSION, load_schema

ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS = ROOT / "artifacts"


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _quantize_structure(value: Any) -> Any:
    if isinstance(value, float):
        return quantize_float(value)
    if isinstance(value, Mapping):
        return {str(key): _quantize_structure(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_quantize_structure(item) for item in value]
    return value


def _collect_requirements() -> dict[str, list[str]]:
    requirements: dict[str, list[str]] = {}
    for path in sorted(ROOT.glob("requirements*.txt")):
        lines = [
            line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
        ]
        requirements[path.name] = sorted(lines)
    return requirements


def _require_keys(mapping: Mapping[str, Any], keys: list[str]) -> None:
    missing = [key for key in keys if key not in mapping]
    if missing:
        raise ValueError(f"missing keys: {missing}")


def _ensure_number(
    value: Any,
    *,
    min_value: float | None = None,
    max_value: float | None = None,
) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise TypeError(f"expected numeric value, received {type(value)!r}")
    result = float(value)
    if min_value is not None and result < min_value:
        raise ValueError(f"value {result} < minimum {min_value}")
    if max_value is not None and result > max_value:
        raise ValueError(f"value {result} > maximum {max_value}")
    return result


def _validate_schema(
    data: Mapping[str, Any],
    schema_name: str,
    *,
    extra_allowed: set[str] | None = None,
) -> None:
    schema = load_schema(schema_name)
    if not isinstance(data, Mapping):
        raise TypeError(f"{schema_name} payload must be an object")

    properties = schema.get("properties", {})
    allowed = set(properties)
    if extra_allowed:
        allowed.update(extra_allowed)
    required = set(schema.get("required", []))
    _require_keys(data, sorted(required))

    extra = set(data) - allowed
    if extra:
        raise ValueError(f"unexpected keys for {schema_name}: {sorted(extra)}")

    for key, spec in properties.items():
        if key not in data:
            continue
        value = data[key]
        schema_type = spec.get("type")
        if schema_type == "string":
            if not isinstance(value, str):
                raise TypeError(f"{key} must be a string")
        elif schema_type == "integer":
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{key} must be an integer")
            minimum = spec.get("minimum")
            if minimum is not None and value < minimum:
                raise ValueError(f"{key} {value} < minimum {minimum}")
            maximum = spec.get("maximum")
            if maximum is not None and value > maximum:
                raise ValueError(f"{key} {value} > maximum {maximum}")
        elif schema_type == "number":
            _ensure_number(value, min_value=spec.get("minimum"), max_value=spec.get("maximum"))
        else:
            raise TypeError(f"unsupported schema type {schema_type!r} for key {key}")


def _validate_offline(data: Mapping[str, Any]) -> None:
    _validate_schema(data, "oracle_stats.schema.json")
    if data.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"offline schema_version {data.get('schema_version')} != {SCHEMA_VERSION}")
    _ensure_number(data["candidate_at_k_recall"], min_value=0.0, max_value=1.0)
    _ensure_number(data["p95_ms"], min_value=0.0)
    _ensure_number(data["p99_ms"], min_value=0.0)
    if "wall_clock_ms" in data:
        _ensure_number(data["wall_clock_ms"], min_value=0.0)


def _normalize_e2e(data: Mapping[str, Any]) -> Mapping[str, Any]:
    if "p_at_1" not in data and "p@1" in data:
        copied = dict(data)
        copied["p_at_1"] = copied["p@1"]
        return copied
    return data


def _validate_e2e(data: Mapping[str, Any]) -> None:
    normalized = _normalize_e2e(data)
    _validate_schema(normalized, "oracle_e2e.schema.json", extra_allowed={"p@1"})
    if normalized.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(
            f"e2e schema_version {normalized.get('schema_version')} != {SCHEMA_VERSION}"
        )
    _ensure_number(normalized.get("p_at_1", normalized.get("p@1")), min_value=0.0, max_value=1.0)
    _ensure_number(normalized["e2e_p95_ms"], min_value=0.0)
    _ensure_number(normalized["e2e_p99_ms"], min_value=0.0)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Generate deterministic metrics hash")
    parser.add_argument("--out", dest="out", help="Optional additional hash output path")
    args = parser.parse_args(argv)

    offline = _load_json(ROOT / "bench/oracle_stats.json")
    e2e = _load_json(ROOT / "bench/oracle_e2e.json")
    raw_purity = _load_json(ROOT / "artifacts/purity_report.json")
    _validate_offline(offline)
    _validate_e2e(e2e)
    _require_keys(
        raw_purity,
        ["sandbox_mode", "network_syscalls"],
    )
    offenders = raw_purity.get("offenders")
    if offenders is None:
        offenders = raw_purity.get("offending", [])
    purity = {
        "sandbox_mode": raw_purity["sandbox_mode"],
        "network_syscalls": raw_purity["network_syscalls"],
        "offenders": offenders,
    }

    payload = {
        "schema_version": SCHEMA_VERSION,
        "environment": {
            "python": {
                "version": platform.python_version(),
                "implementation": platform.python_implementation(),
            },
            "platform": {
                "system": platform.system(),
                "release": platform.release(),
                "machine": platform.machine(),
            },
            "libc": platform.libc_ver(),
            "blas": blas_fingerprint(),
        },
        "requirements": _collect_requirements(),
        "metrics": {
            "offline_oracle": _quantize_structure(offline),
            "oracle_e2e": _quantize_structure(e2e),
            "purity": purity,
        },
    }

    payload_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    digest = hashlib.sha256(payload_bytes).hexdigest()

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    (ARTIFACTS / "metrics_hash_payload.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (ARTIFACTS / "metrics_hash.txt").write_text(f"metrics_hash: {digest}\n", encoding="utf-8")

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(digest + "\n", encoding="utf-8")

    print(f"metrics_hash={digest}")


if __name__ == "__main__":
    main()
