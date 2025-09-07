# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 The Vision Authors
"""Labeler stub."""

from __future__ import annotations

from typing import Any


class Labeler:
    """A stub labeler that returns a fixed label.

    This placeholder mimics a real labeling model by always returning
    the same label regardless of the input provided.
    """

    def label(self, embedding: Any) -> str:
        """Return a dummy label.

        Parameters
        ----------
        embedding:
            Ignored input representing an embedding or other data.

        Returns
        -------
        str
            The fixed label ``"unknown"``.
        """
        return "unknown"
