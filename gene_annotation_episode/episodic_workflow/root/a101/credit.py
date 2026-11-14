"""Original A101 annotation projector and progress units."""

def project_credit(self, source):
    projector = self.scientific_projector_for_context(self.binding_context(source))
    result = self.projection_view(projector, source.scope, **self.projection_arguments(source))
    return result

def _bind_original_runtime(namespace):
    from gene_annotation_episode.episodic_workflow.root.a101.library.live_runtime_functions import bind_functions
    selected = bind_functions(namespace, {name: globals()[name] for name in ('project_credit',)},
        runtime_module='gene_annotation_episode.episodic_workflow.root.a101.runtime', qualified_names={'project_credit': 'project_credit'},
        defining_module='gene_annotation_episode.episodic_workflow.root.a101.credit')
    globals().update(selected)

from gene_annotation_episode.episodic_workflow.root.a101 import runtime as _original_runtime
_bind_original_runtime(vars(_original_runtime))
