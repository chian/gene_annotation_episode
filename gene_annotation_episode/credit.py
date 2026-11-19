"""The annotation-score record an export carries.

An export reads stored records only; the annotation score is computed by the
root episode (`episodic_workflow/root/credit.py`), not here.
"""
from __future__ import annotations


def unavailable_annotation_score():
    return {"status": "unavailable", "annotation_score": None,
            "reason": "numerical_evidence_component_scorer_not_bound"}
