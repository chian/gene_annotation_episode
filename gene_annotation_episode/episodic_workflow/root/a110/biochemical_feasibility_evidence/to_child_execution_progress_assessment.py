"""Prepare the scientific parent's original progress question and return requirement."""
from gene_annotation_episode.episodic_workflow.root.a110.communication import plain
from gene_annotation_episode.episodic_workflow.root.a110.domain import validate_schema
from .execution_progress_assessment.contracts import _ASSIGNMENT


def prepare_request(assignment):
    # Preserve the selected target, known observations, requested fields and
    # permitted records. This parent requests information; it never polls here.
    value = plain(assignment)
    validate_schema(value, _ASSIGNMENT)
    return value


def required_return_sources(services):
    if getattr(services, 'annotation_task_required', lambda: False)():
        return ('monitoring_progress_refs',)
    return ()
