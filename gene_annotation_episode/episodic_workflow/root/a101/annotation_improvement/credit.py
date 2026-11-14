"""Original A101 iterative annotation-improvement credit responsibility."""

def project_credit(self, source):
    projector = self.scientific_projector_for_context(self.binding_context(source))
    result = self.projection_view(projector, source.scope, **self.projection_arguments(source))
    return result

def credit_binding(self, source):
    if len(source.path) == 1:
        return self.credit_binding
    raise ValueError('scientific_task_credit_not_declared:' + source.path[-1][0])

def _bind_original_runtime(namespace):
    from gene_annotation_episode.episodic_workflow.root.a101.library.live_runtime_functions import bind_functions
    selected = bind_functions(namespace, {name: globals()[name] for name in ('project_credit', 'credit_binding')},
        runtime_module='gene_annotation_episode.episodic_workflow.root.a101.runtime', qualified_names={'project_credit': 'project_credit', 'credit_binding': 'credit_binding'},
        defining_module='gene_annotation_episode.episodic_workflow.root.a101.annotation_improvement.credit')
    globals().update(selected)

from gene_annotation_episode.episodic_workflow.root.a101 import runtime as _original_runtime
_bind_original_runtime(vars(_original_runtime))
