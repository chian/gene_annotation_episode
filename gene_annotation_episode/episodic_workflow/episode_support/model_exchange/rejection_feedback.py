"""The invalid-selection feedback an episode's ``action`` passes in ``Rejected(feedback)``.

``rejection_feedback(error, category=...)`` returns ``{'status': 'invalid', 'category', 'detail'}``. A
``jsonschema.ValidationError`` is described by ``schema_failure_diagnostic`` (failed constraints, not the whole
schema); any other error by its text.
"""
from __future__ import annotations

from jsonschema import ValidationError

from gene_annotation_episode.episodic_workflow.episode_support.forms.boundary_validation import (
    schema_failure_diagnostic)


def rejection_feedback(error, *, category):
    if type(category) is not str or not category:
        raise ValueError('rejection_feedback_category_required')
    detail = schema_failure_diagnostic(error) if isinstance(error, ValidationError) else str(error)
    return {'status': 'invalid', 'category': category, 'detail': detail}


__all__ = ['rejection_feedback']
