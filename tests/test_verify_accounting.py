from __future__ import annotations

from vision.verify import VerifyWorker


def test_verify_accounting_balances_accepts_and_rejects() -> None:
    worker = VerifyWorker(threshold=1.0)
    res1 = worker.verify([0.6, 0.6], "label-a")
    res2 = worker.verify([-1.0, -0.5], "label-b")
    assert res1.accepted is True
    assert res2.accepted is False

    metrics = worker.metrics_snapshot()
    assert metrics["called"] == metrics["accepted"] + metrics["rejected"]
    assert metrics["known_wrong_after_verify"] == 0
