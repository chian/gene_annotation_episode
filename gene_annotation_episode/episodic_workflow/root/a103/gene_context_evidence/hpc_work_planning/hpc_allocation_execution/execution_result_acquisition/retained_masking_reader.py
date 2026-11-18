"""Private A103 Results retained masking reader."""
from __future__ import annotations

class ResultsRetainedMaskingReader:

    @staticmethod
    def _masking_selector(assignment):
        return assignment.get('selector', {}).get('version') == 'native_blast_masking_result_selector_v1'

    def _masking_inputs(self, context, assignment):
        return self.native_blast_masking_results.validate_job_inputs(context, assignment)

    def _retained_masking_target(self, context, assignment, scope):
        if not self._masking_selector(assignment):
            return None
        return self.native_blast_masking_results.retained_target(context, assignment=assignment, scope=scope)

    def _masking_reference_access(self, context, reference, namespace):
        access = self.native_blast_masking_results.retained_reference_access(context, reference, namespace)
        if access is not None:
            return access
        from gene_annotation_episode.episodic_workflow.root.a103.sequence_masking_result_views import IDENTIFIER_NAMESPACES
        if self.native_blast_masking_results.applies(context):
            resolved = self.native_blast_masking_results.resolve(context, reference, namespace)
        else:
            resolved = self.native_blast_masking_returns.resolve_received(context, reference, namespace)
        if resolved:
            return True
        return False if namespace in IDENTIFIER_NAMESPACES else None
