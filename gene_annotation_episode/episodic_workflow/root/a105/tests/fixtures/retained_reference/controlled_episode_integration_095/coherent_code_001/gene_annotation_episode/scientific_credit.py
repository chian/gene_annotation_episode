"""Retired categorical scoring bindings.

These names remain only to reject stale callers explicitly. Historical runs
retain their saved numerical observations; replay needs their original code.
The current annotation channel accepts an explicit numerical scorer separately
from investigation progress. No replacement scientific policy is defined here.
"""
from .credit import _retired


class ScientificEvidenceCredit:
    def __init__(self, *args, **kwargs):
        _retired()


class ScientificInvestigationCredit(ScientificEvidenceCredit):
    pass


class AnnotationSupportScore(ScientificEvidenceCredit):
    pass
