"""Webcam support utilities."""

from __future__ import annotations

from .fake_detector import FakeDetector


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
            detector = FakeDetector()
            boxes = detector.detect(None)
            print(f"Dry run: fake detector produced {len(boxes)} boxes")
            return 0
        print("Dry run: webcam loop skipped")
        return 0

    import cv2  # Import lazily so dry runs do not require OpenCV

    detector: FakeDetector | None = None
    if use_fake:
        detector = FakeDetector()

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

            if use_fake and detector is not None:
                for x1, y1, x2, y2 in detector.detect(frame):
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            else:
                cv2.rectangle(frame, (50, 50), (200, 200), (0, 255, 0), 2)

            cv2.imshow("Vision Stub", frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()

    return 0
