"""Top-level package for vision."""

from .fake_detector import FakeDetector
from .embedder import Embedder

__version__ = "0.0.1"
__all__ = ["__version__", "FakeDetector", "Embedder"]
