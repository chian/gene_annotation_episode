"""A101 annotation-score comparisons and recorded resource forecasts in the report."""

def annotation_report_fields(self, source, facts):
    if self.project_annotation_score is not None:
        annotation = self.annotation_context(source.scope, source=source)
        for key in ('annotation_score', 'proposed_annotations', 'annotation_comparisons'):
            if key in annotation:
                facts[key] = annotation[key]
    if self.resource_estimator is not None:
        facts['resource_tool_estimates'] = recorded_forecasts(self.store, run_id=self.run_id, episode_id=source.episode_id)
    return facts

def _bind_original_runtime(namespace):
    from gene_annotation_episode.episodic_workflow.root.a101.library.live_runtime_functions import bind_functions
    selected = bind_functions(namespace, {name: globals()[name] for name in ('annotation_report_fields',)},
        runtime_module='gene_annotation_episode.episodic_workflow.root.a101.runtime', qualified_names={'annotation_report_fields': 'annotation_report_fields'},
        defining_module='gene_annotation_episode.episodic_workflow.root.a101.report_facts')
    globals().update(selected)

from gene_annotation_episode.episodic_workflow.root.a101 import runtime as _original_runtime
_bind_original_runtime(vars(_original_runtime))
