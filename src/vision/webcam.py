# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 The Vision Authors
"""Webcam support utilities."""

from __future__ import annotations

from datetime import datetime

from ._compat import UTC
from .cluster_store import ClusterStore
from .embedder import Embedder
from .fake_detector import FakeDetector
from .labeler import Labeler
from .matcher import Matcher
from .tracker import Tracker


def loop(*, dry_run: bool = False, use_fake: bool = False) -> int:
    """Run the webcam capture loop.

    Parameters
    ----------
    dry_run:
        If ``True``, the loop is skipped and a message is printed instead.
    use_fake:
        Whether to run the :class:`FakeDetector` rather than draw a
        hard-coded rectangle.

    Returns
    -------
    int
        Exit status code, ``0`` for success.
    """

    if dry_run:
        if use_fake:
            fake_detector = FakeDetector()
            fake_tracker = Tracker()
            fake_embedder = Embedder()
            fake_matcher = Matcher()
            fake_labeler = Labeler()
            boxes = fake_detector.detect(None)
            tracked = fake_tracker.update(boxes)
            embeddings = [fake_embedder.embed(box) for _, box in tracked]
            _ = fake_matcher.match(embeddings[0], embeddings) if embeddings else -1
            _ = fake_labeler.label(embeddings[0]) if embeddings else "unknown"
            print(
                "Dry run: fake detector produced "
                f"{len(boxes)} boxes, tracker assigned IDs, "
                f"embedder produced {len(embeddings)} embeddings, "
                "cluster store prepared 1 exemplar, matcher compared embeddings (stub), "
                "labeler assigned 'unknown'"
            )
            return 0
        print("Dry run: webcam loop skipped")
        return 0

    import cv2  # Import lazily so dry runs do not require OpenCV

    detector: FakeDetector | None = None
    tracker: Tracker | None = None
    embedder: Embedder | None = None
    store: ClusterStore | None = None
    matcher: Matcher | None = None
    labeler: Labeler | None = None
    if use_fake:
        detector = FakeDetector()
        tracker = Tracker()
        embedder = Embedder()
        store = ClusterStore()
        matcher = Matcher()
        labeler = Labeler()

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: could not open webcam")
        return 1

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Error: failed to read frame")
                break

            if (
                use_fake
                and detector is not None
                and tracker is not None
                and embedder is not None
                and store is not None
                and matcher is not None
                and labeler is not None
            ):
                boxes = detector.detect(frame)
                tracked = tracker.update(boxes)
                for tid, (x1, y1, x2, y2) in tracked:
                    embedding = embedder.embed((x1, y1, x2, y2))
                    _ = matcher.match(embedding, [])
                    label = labeler.label(embedding)
                    provenance = {
                        "source": "fake",
                        "ts": datetime.now(UTC).isoformat(),
                        "note": "stub",
                    }
                    store.add_exemplar(label, (x1, y1, x2, y2), embedding, provenance)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(
                        frame,
                        f"ID {tid}",
                        (x1, max(0, y1 - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (0, 255, 0),
                        1,
                        cv2.LINE_AA,
                    )
                    cv2.putText(
                        frame,
                        f"Label {label}",
                        (x1, min(y2 + 16, frame.shape[0] - 5)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (0, 255, 0),
                        1,
                        cv2.LINE_AA,
                    )
                store.flush()
            else:
                cv2.rectangle(frame, (50, 50), (200, 200), (0, 255, 0), 2)

            cv2.imshow("Vision Stub", frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()

    return 0
