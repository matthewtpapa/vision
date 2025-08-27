# vision

A minimal Python package with a command-line interface stub.

## Installation

```bash
pip install -e .
```

## Usage

```bash
python -m vision --version
vision --version
```

Both commands output `Vision 0.0.1`.

To test the webcam integration, run the live loop:

```bash
vision webcam
```

For headless environments or continuous integration, use the dry run:

```bash
vision webcam --dry-run
```

To exercise the fake detector instead of the built-in rectangle, use:

```bash
vision webcam --use-fake-detector
```

This overlays stub tracker IDs over the detected box.

The fake detector can also run in a dry run without requiring OpenCV:

```bash
vision webcam --use-fake-detector --dry-run
```

which prints ``Dry run: fake detector produced 1 boxes, tracker assigned IDs``.

For more options, run:

```bash
python -m vision --help
```

## Fake detector stub

The package includes a very small :class:`FakeDetector` that always
returns the same bounding box.  It is a placeholder for future detection
work and can be imported with:

```python
from vision.fake_detector import FakeDetector

detector = FakeDetector()
detector.detect(None)  # -> [(50, 50, 200, 200)]
```

## Tracker stub

The package also ships with a tiny :class:`Tracker` placeholder that assigns
incremental IDs to bounding boxes.

```python
from vision.tracker import Tracker

tracker = Tracker()
tracker.update([(50, 50, 200, 200)])  # -> [(1, (50, 50, 200, 200))]
```
