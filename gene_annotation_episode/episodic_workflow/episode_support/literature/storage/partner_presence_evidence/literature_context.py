"""The literature episode identity A107's partner-sheet repositories read.

The A107 literature sheet repositories (``literature_partner_storage``,
``library/literature_sheet_updates``) key their saved sheets and receipts by
the acting episode and check its scope, assignment and received records. A
literature decision source builds one ``LiteratureContext`` from ``bound``
(run id, episode id, path), its admitted Store scope and assignment and the
records it holds. It carries nothing else.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LiteratureContext:
    """One literature episode as the partner-sheet repositories see it."""
    run_id: str
    episode_id: str
    role: str
    path: tuple
    scope: dict
    assignment: dict
    received_record_refs: tuple


__all__ = ['LiteratureContext']
