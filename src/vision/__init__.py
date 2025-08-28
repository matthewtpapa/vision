"""Top-level package for vision."""

from .embedder import Embedder
from .fake_detector import FakeDetector
from .labeler import Labeler
from .matcher import Matcher
from .ris import ReverseImageSearchStub
from .telemetry import Telemetry

__version__ = "0.0.1"
__all__ = [
    "__version__",
    "FakeDetector",
    "Embedder",
    "Matcher",
    "Labeler",
    "ReverseImageSearchStub",
    "Telemetry",
]
