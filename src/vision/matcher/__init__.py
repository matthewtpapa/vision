# SPDX-License-Identifier: Apache-2.0
"""Embedding matcher stub."""

from __future__ import annotations

from collections.abc import Iterable, Sequence


class Matcher:
    """A stub matcher that checks for exact embedding matches.

    The matcher compares a query embedding against a collection of candidate
    embeddings and returns the index of the first candidate that exactly matches
    the query. If no candidate matches, ``-1`` is returned. This behaviour is a
    placeholder for a future, more sophisticated matching algorithm.
    """

    def match(
        self,
        query: Sequence[float],
        candidates: Iterable[Sequence[float]],
    ) -> int:
        """Return the index of the first candidate equal to ``query``.

        Parameters
        ----------
        query:
            The embedding to search for.
        candidates:
            Iterable of candidate embeddings.

        Returns
        -------
        int
            The index of the first candidate that exactly equals ``query``.
            Returns ``-1`` if no such candidate exists.
        """
        for idx, candidate in enumerate(candidates):
            if list(candidate) == list(query):
                return idx
        return -1
