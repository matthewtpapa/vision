from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol


class VerifyResult(Protocol):
    @property
    def accepted(self) -> bool: ...

    @property
    def evidence_path(self) -> str: ...


@dataclass(frozen=True)
class VerifyOutcome:
    """Simple container for verify results."""

    accepted: bool
    evidence_path: str
    E: float
    D: float
    r: int
    diversity: int


class VerifyWorker:
    """Verify candidates against a calibrated gallery manifest."""

    def __init__(self, manifest_path: str, calibration_path: str) -> None:
        self.manifest_path = manifest_path
        self.calibration_path = calibration_path
        self._rows: list[dict[str, str]] | None = None
        self._calib: dict | None = None
        self._counts: dict[str, int] | None = None
        self._sources: dict[str, set[str]] | None = None

    def _ensure_loaded(self) -> None:
        if self._rows is None:
            with open(self.manifest_path, encoding="utf-8") as fh:
                self._rows = [json.loads(line) for line in fh if line.strip()]
            counts: dict[str, int] = {}
            sources: dict[str, set[str]] = {}
            for r in self._rows:
                lab = r["label"]
                counts[lab] = counts.get(lab, 0) + 1
                sources.setdefault(lab, set()).add(r["source"])
            self._counts = counts
            self._sources = sources
        if self._calib is None:
            with open(self.calibration_path, encoding="utf-8") as fh:
                self._calib = json.load(fh)

    def load_manifest(self) -> tuple[int, dict[str, str] | None]:
        self._ensure_loaded()
        assert self._rows is not None
        count = len(self._rows)
        sample = self._rows[0] if self._rows else None
        return count, sample

    def verify(self, embedding: Sequence[float], candidate_label: str) -> VerifyResult:
        self._ensure_loaded()
        assert self._counts is not None and self._sources is not None and self._calib is not None

        # NOTE: embeddings are currently unused in this stub; evidence scoring will
        # incorporate them in M2-06.
        r = self._counts.get(candidate_label, 0)
        diversity = len(self._sources.get(candidate_label, set()))
        max_other = max(
            (c for lab, c in self._counts.items() if lab != candidate_label),
            default=0,
        )
        D = float(r - max_other)
        E = float(r)

        thresholds = self._calib.get("sprt", {})
        accept_thr = float(thresholds.get("accept", 1.0))
        reject_thr = float(thresholds.get("reject", 0.0))
        diversity_min = int(self._calib.get("diversity_min", 1))

        accepted = False
        if r <= reject_thr or diversity < diversity_min:
            accepted = False
        elif E >= accept_thr:
            accepted = True

        evidence_path = f"bench/verify/evidence/{candidate_label}.json"
        return VerifyOutcome(accepted, evidence_path, E, D, r, diversity)
