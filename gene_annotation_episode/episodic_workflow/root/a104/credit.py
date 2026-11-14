"""A104 original credit defining responsibilities."""
from __future__ import annotations
from .library.live_runtime_functions import bind_functions as _bind_functions

def project_credit(self, source):
    from .annotation_improvement.episode import is_improvement_parent
    if is_improvement_parent(self, source):
        from .annotation_improvement.credit import project_credit
        return project_credit(self, source)
    projector = self.scientific_projector_for_context(self.binding_context(source))
    result = self.projection_view(projector, source.scope, **self.projection_arguments(source))
    return result

def _bind_original_runtime(namespace):
    definitions = {name: globals()[name] for name in ['project_credit']}
    globals().update(_bind_functions(namespace, definitions, runtime_module='gene_annotation_episode.episodic_workflow.root.a104.runtime', qualified_names={'project_credit': 'project_credit'}))
from . import runtime as _original_namespace
_bind_original_runtime(vars(_original_namespace))
