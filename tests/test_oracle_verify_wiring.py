from __future__ import annotations

import json
import sys
import types
from pathlib import Path

import pytest

from scripts.build_fixture import build_fixture
from scripts.build_labelbank_shard import main as build_shard_main
from scripts.verify_build_manifest import build_manifest
from scripts.verify_calibrate import calibrate


def _install_numpy_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_np = types.ModuleType("numpy")

    class _FakeArray:
        def __init__(self, payload: object | None = None) -> None:
            self.payload = payload

        def __getitem__(self, _key):  # pragma: no cover - defensive
            return self

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


def test_oracle_verify_wiring(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(tmp_path)

    shard_dir = Path("bench/labelbank/shard")
    lb_seed = tmp_path / "lb_seed.jsonl"
    lb_rows = [
        {"label": "alpha", "aliases": ["alpha"], "p31": "product_model", "lang": "en"},
        {"label": "bravo", "aliases": ["bravo"], "p31": "product_model", "lang": "en"},
        {"label": "charlie", "aliases": ["charlie"], "p31": "product_model", "lang": "en"},
    ]
    lb_seed.write_text("\n".join(json.dumps(row) for row in lb_rows), encoding="utf-8")
    build_result = build_shard_main(
        [
            "--seed",
            "1234",
            "--in",
            str(lb_seed),
            "--out",
            str(shard_dir),
            "--dim",
            "16",
            "--max-n",
            "16",
        ]
    )
    assert build_result == 0

    fixture_dir = Path("bench/fixture")
    build_fixture(fixture_dir, n=4, seed=21)

    bench_verify = Path("bench/verify")
    bench_verify.mkdir(parents=True, exist_ok=True)
    seed = repo_root / "data/verify/seed_gallery/seed.jsonl"
    data_dir = repo_root / "data/verify/seed_gallery"
    manifest = bench_verify / "gallery_manifest.jsonl"
    build_manifest(str(seed), str(data_dir), str(manifest))
    calibrate(str(manifest), str(bench_verify / "calibration.json"), 4242)

    monkeypatch.setenv("VISION__LABELBANK__SHARD", str(shard_dir))
    monkeypatch.setenv("VISION__ORACLE__MAXLEN", "64")
    monkeypatch.setenv("VISION__ENABLE_VERIFY_LEDGER", "1")

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
    with metrics_path.open(encoding="utf-8") as fh:
        metrics = json.load(fh)

    oracle_block = metrics["oracle"]
    assert oracle_block["maxlen"] == 64
    assert 0.0 <= oracle_block["shed_rate"] <= 1.0

    verify_block = metrics["verify"]
    assert verify_block["called"] >= verify_block["accepted"] + verify_block["rejected"]

    ledger_path = Path("bench/verify/ledger.jsonl")
    if verify_block["called"] > 0:
        assert ledger_path.exists()
        with ledger_path.open(encoding="utf-8") as fh:
            lines = [line for line in fh.read().splitlines() if line.strip()]
        assert len(lines) >= 1
        sample = json.loads(lines[0])
        assert "embedding" in sample
        assert isinstance(sample["embedding"], list)
    else:
        if ledger_path.exists():
            assert ledger_path.stat().st_size == 0
