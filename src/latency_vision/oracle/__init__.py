"""Oracle interfaces and implementations."""

from .candidate_oracle import CandidateOracle
from .in_memory_oracle import CandidateRecord, InMemoryCandidateOracle

__all__ = ["CandidateOracle", "CandidateRecord", "InMemoryCandidateOracle"]
