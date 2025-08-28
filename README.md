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

This overlays stub tracker IDs over the detected box and runs the stub
embedder for each detection.

The fake detector can also run in a dry run without requiring OpenCV:

```bash
vision webcam --use-fake-detector --dry-run
```

which prints ``Dry run: fake detector produced 1 boxes, tracker assigned IDs, embedder produced 1 embeddings, cluster store prepared 1 exemplar, matcher compared embeddings (stub), labeler assigned 'unknown'``.

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

## Embedder stub

The package also contains an :class:`Embedder` placeholder that always
returns the same 128-dimensional feature vector.

```python
from vision.embedder import Embedder

embedder = Embedder()
embedder.embed(None)  # -> [0.0] * 128
```

## Matcher stub

The package provides a simple :class:`Matcher` placeholder that searches for
an embedding within a list of candidates and reports the index of the first
exact match. When no match is found, ``-1`` is returned.

```python
from vision.matcher import Matcher

matcher = Matcher()
matcher.match([1.0, 2.0], [[1.0, 2.0], [3.0, 4.0]])  # -> 0
matcher.match([5.0], [])  # -> -1
```

Dry runs of the webcam now report ``matcher compared embeddings (stub), labeler assigned 'unknown'`` to
indicate the matcher and labeler were invoked.

## Labeler stub

The package includes a small :class:`Labeler` placeholder that always
returns the label ``"unknown"``.

```python
from vision import Labeler

labeler = Labeler()
labeler.label(None)  # -> "unknown"
```

## Cluster store stub

The package provides a :class:`ClusterStore` placeholder that persists
*exemplar* records to ``data/kb.json`` by default. An exemplar has the
following fields:

```json
{
  "label": "unknown",
  "bbox": [x1, y1, x2, y2],
  "embedding": [0.0, ... 128 floats ...],
  "provenance": {"source": "fake", "ts": "<ISO8601>", "note": "stub"}
}
```

Dry runs of the webcam (``vision webcam --use-fake-detector --dry-run``)
do not write to disk, while live runs with ``--use-fake-detector`` append an
exemplar per frame and flush the store.

```python
from vision.cluster_store import ClusterStore

store = ClusterStore()  # persists to data/kb.json
store.add_exemplar(
    "unknown",
    (1, 2, 3, 4),
    [0.0] * 128,
    {"source": "fake", "ts": "2025-01-01T00:00:00Z", "note": "stub"},
)
store.flush()
# Later
reloaded = ClusterStore.load("data/kb.json")
```
