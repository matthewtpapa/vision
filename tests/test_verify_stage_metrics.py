from __future__ import annotations

import json
import sys
import types
from pathlib import Path

import pytest

from scripts.build_fixture import build_fixture
from scripts.verify_build_manifest import build_manifest
from scripts.verify_calibrate import calibrate


class _FakeArray:
    def __init__(self, payload: object | None = None) -> None:
        self.payload = payload

    def __getitem__(self, _key):  # pragma: no cover - defensive
        return self


def _install_numpy_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_np = types.ModuleType("numpy")

    def asarray(obj):
        return _FakeArray(obj)

    fake_np.asarray = asarray  # type: ignore[attr-defined]
    fake_np.ndarray = _FakeArray  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "numpy", fake_np)


def _install_pil_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_pil = types.ModuleType("PIL")
    fake_image = types.ModuleType("PIL.Image")

    class _FakeImage:
        def __init__(self, path: Path) -> None:
            self.path = Path(path)

        def __enter__(self) -> _FakeImage:
            return self

        def __exit__(self, *_exc_info) -> bool:
            return False

        def convert(self, _mode: str) -> _FakeImage:
            return self

    def open_image(path: str | Path) -> _FakeImage:
        return _FakeImage(Path(path))

    fake_image.open = open_image  # type: ignore[attr-defined]
    fake_pil.Image = fake_image  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "PIL", fake_pil)
    monkeypatch.setitem(sys.modules, "PIL.Image", fake_image)


def test_verify_stage_metrics(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(tmp_path)

    bench_verify = Path("bench/verify")
    bench_verify.mkdir(parents=True, exist_ok=True)

    seed = repo_root / "data/verify/seed_gallery/seed.jsonl"
    data_dir = repo_root / "data/verify/seed_gallery"
    manifest = bench_verify / "gallery_manifest.jsonl"
    build_manifest(str(seed), str(data_dir), str(manifest))
    calibrate(str(manifest), str(bench_verify / "calibration.json"), 4242)

    fixture_dir = Path("bench/fixture")
    build_fixture(fixture_dir, n=3, seed=7)

    _install_numpy_stub(monkeypatch)
    _install_pil_stub(monkeypatch)

    from latency_vision import evaluator

    out_dir = Path("bench/out")
    code = evaluator.run_eval(
        str(fixture_dir),
        str(out_dir),
        warmup=0,
        unknown_rate_band=(0.0, 1.0),
    )
    assert code == 0

    metrics_path = out_dir / "metrics.json"
    stage_csv = out_dir / "stage_times.csv"

    with metrics_path.open(encoding="utf-8") as fh:
        metrics = json.load(fh)

    verify_block = metrics["verify"]
    assert "p50_ms" in verify_block
    assert "p95_ms" in verify_block
    assert "p99_ms" in verify_block

    with stage_csv.open(encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    assert any(line.startswith("verify,") for line in lines)
