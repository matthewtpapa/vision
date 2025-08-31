# SPDX-License-Identifier: Apache-2.0
import pytest

from vision.config import _reset_config_cache
from vision.detect_adapter import FakeDetector
from vision.embedder_adapter import ClipLikeEmbedder
from vision.matcher.matcher_protocol import MatcherProtocol
from vision.pipeline_detect_track_embed import DetectTrackEmbedPipeline
from vision.track_bytetrack_adapter import ByteTrackLikeTracker


def _make_now():
    t = 0
    step = 1_000_000

    def set_step(ns: int) -> None:
        nonlocal step
        step = ns

    def now() -> int:
        nonlocal t
        t += step
        return t

    return now, set_step


@pytest.fixture(autouse=True)
def reset_config_cache():
    _reset_config_cache()
    yield
    _reset_config_cache()


def _make_pipeline(
    monkeypatch: pytest.MonkeyPatch,
    env: dict[str, str] | None = None,
    *,
    known: bool = False,
):
    now, set_step = _make_now()
    monkeypatch.setattr("vision.telemetry.now_ns", now)
    monkeypatch.setattr("vision.telemetry.Telemetry.now_ns", lambda self: now(), raising=False)
    monkeypatch.setattr("vision.pipeline_detect_track_embed.now_ns", now)

    class DummyMatcher(MatcherProtocol):
        def add(self, vec, lab):
            pass

        def topk(self, vec, k):
            return [("lab", 1.0)] if known else []

    def dummy_builder(dim):
        return DummyMatcher()

    monkeypatch.setattr("vision.matcher.factory.build_matcher", dummy_builder)
    monkeypatch.setattr("vision.pipeline_detect_track_embed.build_matcher", dummy_builder)
    monkeypatch.setattr(
        "vision.pipeline_detect_track_embed.add_exemplars_to_index",
        lambda matcher, items: 0,
    )
    if env:
        for k, v in env.items():
            monkeypatch.setenv(k, v)
    det = FakeDetector(boxes=[(0, 0, 10, 10)])
    trk = ByteTrackLikeTracker()

    def cropper(frame, bboxes):
        return [object() for _ in bboxes]

    def runner(crops, *, dim, batch_size):
        return [[0.0] * dim for _ in crops]

    emb = ClipLikeEmbedder(runner, dim=3, normalize=False, batch_size=2)
    pipe = DetectTrackEmbedPipeline(det, trk, cropper, emb)
    return pipe, set_step


def test_stride_increases(monkeypatch: pytest.MonkeyPatch) -> None:
    env = {
        "VISION__LATENCY__WINDOW": "30",
        "VISION__LATENCY__BUDGET_MS": "50",
        "VISION__PIPELINE__MAX_STRIDE": "3",
    }
    pipe, set_step = _make_pipeline(monkeypatch, env)
    set_step(7_000_000)  # ~7ms per call -> slow frames
    for _ in range(40):
        pipe.process(None)
    assert pipe.current_stride() > 1


def test_stride_decreases(monkeypatch: pytest.MonkeyPatch) -> None:
    env = {
        "VISION__LATENCY__WINDOW": "30",
        "VISION__LATENCY__BUDGET_MS": "50",
        "VISION__PIPELINE__MAX_STRIDE": "3",
    }
    pipe, set_step = _make_pipeline(monkeypatch, env)
    set_step(7_000_000)
    for _ in range(40):
        pipe.process(None)
    assert pipe.current_stride() > 1
    set_step(500_000)  # fast frames
    for _ in range(90):
        pipe.process(None)
    assert pipe.current_stride() == 1


def test_stride_bounds(monkeypatch: pytest.MonkeyPatch) -> None:
    env = {
        "VISION__LATENCY__WINDOW": "30",
        "VISION__LATENCY__BUDGET_MS": "50",
        "VISION__PIPELINE__MAX_STRIDE": "3",
        "VISION__PIPELINE__MIN_STRIDE": "1",
    }
    pipe, set_step = _make_pipeline(monkeypatch, env)
    set_step(7_000_000)
    for _ in range(100):
        pipe.process(None)
    assert pipe.current_stride() == 3
    set_step(500_000)
    for _ in range(120):
        pipe.process(None)
    assert pipe.current_stride() == 1


def test_auto_stride_toggle(monkeypatch: pytest.MonkeyPatch) -> None:
    env = {
        "VISION__LATENCY__WINDOW": "30",
        "VISION__LATENCY__BUDGET_MS": "50",
        "VISION__PIPELINE__AUTO_STRIDE": "0",
    }
    pipe, set_step = _make_pipeline(monkeypatch, env)
    set_step(7_000_000)
    for _ in range(100):
        pipe.process(None)
    assert pipe.current_stride() == 1


def test_telemetry_lengths(monkeypatch: pytest.MonkeyPatch) -> None:
    env = {
        "VISION__PIPELINE__FRAME_STRIDE": "3",
        "VISION__PIPELINE__AUTO_STRIDE": "0",
    }
    pipe, set_step = _make_pipeline(monkeypatch, env, known=True)
    set_step(1_000_000)
    total = 10
    for _ in range(total):
        pipe.process(None)
    per_frame, per_stage, unknown_flags = pipe.get_eval_counters()
    assert len(per_frame) == total
    processed = len([i for i in range(total) if i % 3 == 0])
    assert sum(len(v) for v in per_stage.values()) == processed * 4
    assert len(unknown_flags) == total
    assert not any(unknown_flags)
