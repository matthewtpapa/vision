# vision

<!-- Replace <OWNER>/<REPO> with your repo slug after merge -->
![CI](https://github.com/<OWNER>/<REPO>/actions/workflows/ci.yml/badge.svg)

A minimal Python package with a command-line interface stub.

## Quickstart

```bash
pip install -e .
vision --version
vision webcam --dry-run
```

## Installation

```bash
pip install -e .
```

## Usage

```bash
python -m vision --version
vision --version
```

Both commands output `Vision 0.0.2`.

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

which prints:

```text
Dry run: fake detector produced 1 boxes, tracker assigned IDs, embedder produced 1 embeddings, cluster store prepared 1 exemplar, matcher compared embeddings (stub), labeler assigned 'unknown'
```

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

Dry runs of the webcam now report:

```text
matcher compared embeddings (stub), labeler assigned 'unknown'
```

to indicate the matcher and labeler were invoked.

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

## RIS (Reverse Image Search) Stub

A no-network placeholder that always returns an empty result.

```python
from vision import ReverseImageSearchStub

ris = ReverseImageSearchStub()
ris.search(object())  # -> []
```

## Telemetry Stub

An in-memory metrics sink intended to be replaced later.

```python
from vision import Telemetry

t = Telemetry()
t.inc("frames")
t.set_gauge("latency_ms", 12.3)
```

## Documentation

- [Project Charter](docs/charter.md)
- [Architecture](docs/architecture.md)
- [Changelog](CHANGELOG.md)

## Contributing

We use a lightweight, self-enforced workflow:

- Open PRs from topic branches; do not push directly to `main`.
- Ensure CI is green (`pytest -q` + markdownlint job).
- Use the PR template; link an issue; keep changes small.
- Squash merge and delete the branch after merge.

> Note on docs linting: markdownlint runs in CI via
> `DavidAnson/markdownlint-cli2-action`. You don’t need Node/npm locally.
> Keep Markdown readable; CI will flag formatting issues on PRs.

### Development setup

```bash
python -m venv .venv && source .venv/bin/activate
make setup
```

This installs development tools like `pytest`, `pytest-cov`, `mypy`, and `ruff`.
Coverage runs in CI by default and uploads `.coverage` and `coverage.xml` artifacts.
To run coverage locally (optional):

```bash
make test-cov         # requires pytest-cov
make cov-html         # builds htmlcov/ if .coverage exists
```

If installs are blocked, rely on CI coverage artifacts instead (download from the PR run).

### Run all checks

```bash
ruff check . && ruff format --check . && mypy src/vision && make test
# optionally, add coverage locally if available:
# make test-cov && make cov-html
```

If `make test-cov` reports missing `pytest-cov`, install dev deps (`make setup`) or review coverage in CI.

#### Optional: pre-commit

```bash
pip install pre-commit
pre-commit install
```

Run `make help` to see available targets.

#### One-command local checks

Before pushing, run:

```bash
make verify
```

This runs ruff (lint + format check), mypy, pytest, and markdownlint with the same rules as CI.

#### Markdown lint parity with CI

```bash
# one-time
pre-commit install

# lint all Markdown files (same as CI)
make mdlint
```

Whitespace and line endings are normalized via `.editorconfig` and `.gitattributes`
to avoid OS-specific churn.
