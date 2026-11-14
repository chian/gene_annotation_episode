"""Original private A108 annotation credit responsibility."""
from __future__ import annotations

def scientific_source_credit(workflow, source):
    projector = workflow.scientific_projector_for_context(workflow.binding_context(source))
    result = workflow.projection_view(projector, source.scope, **workflow.projection_arguments(source))
    return result
