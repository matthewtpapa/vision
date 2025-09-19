from __future__ import annotations

from latency_vision.oracle.in_memory_oracle import InMemoryCandidateOracle


def test_oracle_queue_overflow_and_next() -> None:
    oracle = InMemoryCandidateOracle(maxlen=2)
    for idx in range(3):
        oracle.enqueue_unknown([float(idx)], {"frame_idx": idx})

    assert oracle.qsize() == 2
    assert oracle.shed_total() == 1

    first = oracle.next()
    assert first is not None
    labels, context = first
    assert labels == []
    assert context["frame_idx"] == 1
    assert context["embedding"] == [1.0]

    second = oracle.next()
    assert second is not None
    labels2, context2 = second
    assert labels2 == []
    assert context2["frame_idx"] == 2

    assert oracle.next() is None
    assert oracle.qsize() == 0
