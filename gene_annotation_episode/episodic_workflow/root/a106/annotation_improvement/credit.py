"""A106 original implicit improvement responsibility; distinct private invocation."""
from __future__ import annotations
from ..library.live_runtime_functions import bind_functions as _bind_functions

def project_credit(self, source):
    projector = self.scientific_projector_for_context(self.binding_context(source))
    result = self.projection_view(projector, source.scope, **self.projection_arguments(source))
    return result

def _bind_original_runtime(namespace):
    names = {'project_credit': 'project_credit'}
    globals().update(_bind_functions(namespace, {name: globals()[name] for name in names},
        runtime_module='gene_annotation_episode.episodic_workflow.root.a106.runtime', qualified_names=names,
        defining_module='gene_annotation_episode.episodic_workflow.root.a106.annotation_improvement.credit'))

from .. import runtime as _original_namespace
_bind_original_runtime(vars(_original_namespace))
