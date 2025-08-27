"""Webcam support utilities."""

from __future__ import annotations


def loop(*, dry_run: bool = False) -> int:
    """Run the webcam capture loop.

    Parameters
    ----------
    dry_run:
        If ``True``, the loop is skipped and a message is printed instead.

    Returns
    -------
    int
        Exit status code, ``0`` for success.
    """

    if dry_run:
        print("Dry run: webcam loop skipped")
        return 0

    import cv2  # Import lazily so dry runs do not require OpenCV

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

            cv2.rectangle(frame, (50, 50), (200, 200), (0, 255, 0), 2)
            cv2.imshow("Vision Stub", frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()

    return 0
