# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 The Vision Authors
from vision.detect_yolo_adapter import YoloLikeDetector
from vision.track_bytetrack_adapter import ByteTrackLikeTracker
from vision.types import Detection


def test_yololike_detector_converts_runner_outputs_with_threshold():
    def fake_runner(frame, input_size):
        return [
            (0.2, 0.2, 10.7, 10.9, 0.10, 1),
            (5.0, 5.0, 25.0, 25.0, 0.90, 3),
        ]

    detector = YoloLikeDetector(fake_runner, input_size=640, score_threshold=0.25)
    detections = detector.detect(None)

    assert len(detections) == 1
    det = detections[0]
    assert det.bbox == (5, 5, 25, 25)
    assert det.score == 0.90
    assert det.cls == 3


def test_bytetracklike_tracker_preserves_ids_across_frames():
    tracker = ByteTrackLikeTracker()

    frame_a = [
        Detection((10, 10, 30, 30), 0.9, 0),
        Detection((100, 100, 140, 140), 0.9, 0),
    ]
    tracks_a = tracker.update(frame_a)
    assert [t.track_id for t in tracks_a] == [1, 2]
    assert tracks_a[0].bbox == frame_a[0].bbox
    assert tracks_a[1].bbox == frame_a[1].bbox

    frame_b = [
        Detection((12, 12, 32, 32), 0.8, 0),
        Detection((102, 102, 142, 142), 0.8, 0),
    ]
    tracks_b = tracker.update(frame_b)
    assert [t.track_id for t in tracks_b] == [1, 2]
    assert tracks_b[0].bbox == frame_b[0].bbox
    assert tracks_b[1].bbox == frame_b[1].bbox


def test_bytetracklike_tracker_assigns_new_id_for_new_object():
    tracker = ByteTrackLikeTracker()

    frame1 = [Detection((10, 10, 30, 30), 0.9, 0)]
    tracks1 = tracker.update(frame1)
    assert tracks1[0].track_id == 1

    frame2 = [
        Detection((12, 12, 32, 32), 0.8, 0),
        Detection((200, 200, 220, 220), 0.8, 0),
    ]
    tracks2 = tracker.update(frame2)
    assert tracks2[0].track_id == 1
    assert tracks2[1].track_id == 2
