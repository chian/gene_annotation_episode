"""A110 annotation credit selects the original projector and exact scientific operands."""
from __future__ import annotations

def project_credit(workflow, source):
    projector = workflow.scientific_projector_for_context(workflow.binding_context(source))
    result = workflow.projection_view(projector, source.scope, **workflow.projection_arguments(source))
    return result

