"""Tiny picklable sklearn helpers.

Lives in its own module (never run as __main__) so that functions referenced by
a saved sklearn Pipeline pickle by a stable import path (`pipeline._sk.to_dense`)
and reload correctly regardless of how the training script was launched.
"""

from __future__ import annotations


def to_dense(x):
    """Densify a sparse matrix for estimators that need dense input (HGB)."""
    return x.toarray() if hasattr(x, "toarray") else x
