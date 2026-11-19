"""The literature episode context the A105 sheet repositories and grading logic read."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LiteratureContext:
    """One literature episode's identity, commission and the records it holds."""
    run_id: str
    episode_id: str
    role: str
    path: tuple
    scope: dict
    assignment: dict
    request: dict
    received_record_refs: tuple


__all__ = ['LiteratureContext']
