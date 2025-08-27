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

For more options, run:

```bash
python -m vision --help
```
