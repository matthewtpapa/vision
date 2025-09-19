from __future__ import annotations

import json
import sys
import types
from pathlib import Path

import pytest

from scripts.build_fixture import build_fixture
from scripts.build_labelbank_shard import main as build_shard_main


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


def test_labelbank_wiring(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(tmp_path)

    shard_dir = Path("bench/labelbank/shard")
    build_result = build_shard_main(
        [
            "--seed",
            "1234",
            "--in",
            str(repo_root / "data/labelbank/seed.jsonl"),
            "--out",
            str(shard_dir),
            "--dim",
            "16",
            "--max-n",
            "32",
        ]
    )
    assert build_result == 0

    fixture_dir = Path("bench/fixture")
    build_fixture(fixture_dir, n=3, seed=11)

    monkeypatch.setenv("VISION__LABELBANK__SHARD", str(shard_dir))
    monkeypatch.setenv("VISION__ORACLE__MAXLEN", "64")

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
    stage_totals = out_dir / "stage_totals.csv"
    ledger_path = Path("bench/verify/ledger.jsonl")

    with metrics_path.open(encoding="utf-8") as fh:
        metrics = json.load(fh)

    oracle_block = metrics["oracle"]
    assert oracle_block["enqueued"] >= 0
    assert oracle_block["shed"] >= 0
    assert "p50_ms" in oracle_block
    assert "p95_ms" in oracle_block

    if metrics.get("unknown_rate", 0.0) > 0:
        assert oracle_block["enqueued"] > 0

    assert stage_csv.exists()

    with stage_totals.open(encoding="utf-8") as fh:
        totals = fh.read().splitlines()
    assert any(line.startswith("oracle,") for line in totals[1:])

    ledger_exists = ledger_path.exists() and ledger_path.stat().st_size > 0
    assert ledger_exists == (metrics["verify"].get("accepted", 0) > 0)
