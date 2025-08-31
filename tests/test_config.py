# SPDX-License-Identifier: Apache-2.0
from dataclasses import FrozenInstanceError

import pytest

from vision.config import _reset_config_cache, get_config


@pytest.fixture(autouse=True)
def clear_cache():
    _reset_config_cache()


def test_defaults(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cfg = get_config()
    assert cfg.detector.model_path == "models/yolov8n.onnx"
    assert cfg.detector.input_size == 640
    assert cfg.tracker.type == "bytetrack"
    assert cfg.embedder.model == "ViT-B-32-openai"
    assert cfg.embedder.batch_size == 8
    assert cfg.embedder.device == "cpu"
    assert cfg.matcher.index_type == "faiss-flat"
    assert cfg.matcher.topk == 5
    assert cfg.matcher.threshold == 0.35
    assert cfg.matcher.min_neighbors == 1
    assert cfg.pipeline.frame_stride == 1
    assert cfg.latency.budget_ms == 66
    assert cfg.paths.kb_json == "data/kb.json"
    assert cfg.paths.telemetry_csv == "artifacts/telemetry.csv"


def test_toml_overrides(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "vision.toml").write_text(
        """[embedder]\nbatch_size = 16\n\n[latency]\nbudget_ms = 33\n"""
    )
    cfg = get_config()
    assert cfg.embedder.batch_size == 16
    assert cfg.latency.budget_ms == 33


def test_toml_path_argument_overrides(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "other.toml").write_text(
        """[embedder]\nbatch_size = 12\n\n[latency]\nbudget_ms = 40\n"""
    )
    cfg = get_config("other.toml")
    assert cfg.embedder.batch_size == 12
    assert cfg.latency.budget_ms == 40


def test_env_overrides_precedence(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "vision.toml").write_text(
        """[embedder]\nbatch_size = 12\n\n[matcher]\nthreshold = 0.25\n"""
    )
    monkeypatch.setenv("VISION__EMBEDDER__BATCH_SIZE", "16")
    monkeypatch.setenv("VISION__MATCHER__THRESHOLD", "0.45")
    cfg = get_config()
    assert cfg.embedder.batch_size == 16
    assert cfg.matcher.threshold == 0.45


def test_env_keys_case_insensitive(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("VISION__matcher__THRESHOLD", "0.5")
    cfg = get_config()
    assert cfg.matcher.threshold == 0.5


def test_env_string_passthrough(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("VISION__EMBEDDER__DEVICE", "cuda")
    cfg = get_config()
    assert cfg.embedder.device == "cuda"


def test_env_unknown_keys_ignored(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("VISION__FOO__BAR", "123")
    monkeypatch.setenv("VISION__EMBEDDER__UNKNOWN", "zzz")
    cfg = get_config()
    assert cfg.embedder.batch_size == 8
    assert cfg.embedder.device == "cpu"


def test_config_is_cached():
    first = get_config()
    second = get_config()
    assert first is second


def test_config_is_immutable():
    cfg = get_config()
    with pytest.raises(FrozenInstanceError):
        cfg.detector.model_path = "other"
