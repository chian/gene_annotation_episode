"""Actual annotation/improvement -> unregistered improvement boundaries."""
from __future__ import annotations


def exchange_for_child(workflow, source, role):
    from ..episode import is_annotation_parent
    from .episode import is_improvement_parent
    if type(role) is not str or role != 'improvement':
        return None
    if is_annotation_parent(workflow, source):
        if workflow.structural_homology_evidence_binding is not None:
            return None
        from ..to_child_annotation_improvement import prepare_request
        from ..from_child_annotation_improvement import admit_return
    elif is_improvement_parent(workflow, source):
        from .to_child_annotation_improvement import prepare_request
        from .from_child_annotation_improvement import admit_return
    else:
        return None
    return prepare_request, admit_return
