"""Private A103 Results retained utility reader."""
from __future__ import annotations

class ResultsRetainedUtilityReader:

    @staticmethod
    def _utility_selector(assignment):
        return assignment.get('selector', {}).get('version') in {'native_blast_utility_result_selector_v1', 'native_blast_utility_result_selector_v2'}

    def _utility_inputs(self, context, assignment):
        return self.native_blast_utility_results.validate_job_inputs(context, assignment)

    def _retained_utility_target(self, context, assignment, scope):
        if not self._utility_selector(assignment):
            return None
        return self.native_blast_utility_results.retained_target(context, assignment=assignment, scope=scope)

    def _utility_reference_access(self, context, reference, namespace):
        access = self.native_blast_utility_results.retained_reference_access(context, reference, namespace)
        if access is not None:
            return access
        from gene_annotation_episode.episodic_workflow.root.a103.blast_utility_result_views import IDENTIFIER_NAMESPACES
        if self.native_blast_utility_results.applies(context):
            resolved = self.native_blast_utility_results.resolve(context, reference, namespace)
        else:
            resolved = self.native_blast_utility_returns.resolve_received(context, reference, namespace)
        if resolved:
            return True
        return False if namespace in IDENTIFIER_NAMESPACES else None
