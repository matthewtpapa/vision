"""Configuration management for the vision package.

This module exposes a single public function :func:`get_config` which returns
application configuration as a frozen dataclass hierarchy. Configuration values
may come from in-code defaults, an optional ``vision.toml`` file, and
environment variables prefixed with ``VISION__``. The resulting object is
memoized so subsequent calls return the same instance. A helper
``_reset_config_cache`` is provided for test suites to clear the memoized
instance.
"""

from __future__ import annotations

import os
import tomllib
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class DetectorConfig:
    model_path: str = "models/yolov8n.onnx"
    input_size: int = 640


@dataclass(frozen=True)
class TrackerConfig:
    type: str = "bytetrack"


@dataclass(frozen=True)
class EmbedderConfig:
    model: str = "ViT-B-32-openai"
    batch_size: int = 8
    device: str = "cpu"


@dataclass(frozen=True)
class MatcherConfig:
    index_type: str = "faiss-flat"
    topk: int = 5
    threshold: float = 0.35
    min_neighbors: int = 1


@dataclass(frozen=True)
class PathsConfig:
    kb_json: str = "data/kb.json"
    telemetry_csv: str = "artifacts/telemetry.csv"


@dataclass(frozen=True)
class PipelineConfig:
    frame_stride: int = 1


@dataclass(frozen=True)
class LatencyConfig:
    budget_ms: int = 66


@dataclass(frozen=True)
class Config:
    detector: DetectorConfig = field(default_factory=DetectorConfig)
    tracker: TrackerConfig = field(default_factory=TrackerConfig)
    embedder: EmbedderConfig = field(default_factory=EmbedderConfig)
    matcher: MatcherConfig = field(default_factory=MatcherConfig)
    pipeline: PipelineConfig = field(default_factory=PipelineConfig)
    paths: PathsConfig = field(default_factory=PathsConfig)
    latency: LatencyConfig = field(default_factory=LatencyConfig)


_CONFIG_CACHE: Config | None = None


def _deep_merge(base: dict[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
    """Recursively merge ``override`` into ``base`` and return the result."""

    result: dict[str, Any] = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, Mapping):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _dict_to_config(data: dict[str, Any]) -> Config:
    """Convert a nested mapping to a :class:`Config` instance."""

    return Config(
        detector=DetectorConfig(**data["detector"]),
        tracker=TrackerConfig(**data["tracker"]),
        embedder=EmbedderConfig(**data["embedder"]),
        matcher=MatcherConfig(**data["matcher"]),
        pipeline=PipelineConfig(**data["pipeline"]),
        paths=PathsConfig(**data["paths"]),
        latency=LatencyConfig(**data["latency"]),
    )


def _cast_env_value(value: str) -> Any:
    """Cast environment variable string to int or float when possible."""

    try:
        return int(value)
    except ValueError:
        try:
            return float(value)
        except ValueError:
            return value


def _env_overrides(schema: Mapping[str, Any]) -> dict[str, Any]:
    """Collect environment variable overrides following ``VISION__`` prefix."""

    prefix = "VISION__"
    result: dict[str, Any] = {}
    for raw_key, raw_value in os.environ.items():
        if not raw_key.startswith(prefix):
            continue
        parts = [part.lower() for part in raw_key[len(prefix) :].split("__")]
        if len(parts) != 2:
            continue
        section, field = parts
        if section not in schema or field not in schema[section]:
            continue
        result.setdefault(section, {})[field] = _cast_env_value(raw_value)
    return result


def get_config(toml_path: str | None = None) -> Config:
    """Return application configuration.

    The configuration is created on first use and cached for the lifetime of the
    process. Configuration values may be overridden by a ``vision.toml`` file
    located in the current working directory or supplied via ``toml_path``, and
    by environment variables prefixed with ``VISION__``. Precedence: defaults <
    TOML < environment variables (VISION__…). Sections/keys are case-insensitive.
    The configuration is cached globally; subsequent calls ignore a different
    ``toml_path`` or env changes unless the cache is reset.
    """

    global _CONFIG_CACHE
    if _CONFIG_CACHE is None:
        cfg_dict = asdict(Config())
        path = Path(toml_path) if toml_path is not None else Path.cwd() / "vision.toml"
        if path.is_file():
            with path.open("rb") as fh:
                overrides = tomllib.load(fh)
            cfg_dict = _deep_merge(cfg_dict, overrides)
        env_cfg = _env_overrides(cfg_dict)
        if env_cfg:
            cfg_dict = _deep_merge(cfg_dict, env_cfg)
        _CONFIG_CACHE = _dict_to_config(cfg_dict)
    return _CONFIG_CACHE


def _reset_config_cache() -> None:
    """Clear the cached configuration.

    This function is intended for use in test suites to ensure isolation between
    tests.
    """

    global _CONFIG_CACHE
    _CONFIG_CACHE = None


__all__ = ["get_config"]
