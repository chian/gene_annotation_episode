"""Original A103 annotation-comparison and recorded-forecast projection."""
from __future__ import annotations

def project_annotation_facts(self, source, facts):
    if self.project_annotation_score is not None:
        annotation = self.annotation_context(source.scope, source=source)
        for key in ('annotation_score', 'proposed_annotations', 'annotation_comparisons'):
            if key in annotation:
                facts[key] = annotation[key]
    if self.resource_estimator is not None:
        facts['resource_tool_estimates'] = _runtime.recorded_forecasts(self.store, run_id=self.run_id, episode_id=source.episode_id)

# Bind original module providers after definitions to admit either import order.
from .. import runtime as _runtime
