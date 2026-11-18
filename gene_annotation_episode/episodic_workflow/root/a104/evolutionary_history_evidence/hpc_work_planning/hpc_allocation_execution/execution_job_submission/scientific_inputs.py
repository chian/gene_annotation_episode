"""Private A104 Launch scientific inputs."""
from __future__ import annotations

class LaunchScientificInputs:

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
        from gene_annotation_episode.episodic_workflow.root.a104.sequence_masking_result_views import IDENTIFIER_NAMESPACES
        if self.native_blast_masking_results.applies(context):
            resolved = self.native_blast_masking_results.resolve(context, reference, namespace)
        else:
            resolved = self.native_blast_masking_returns.resolve_received(context, reference, namespace)
        if resolved:
            return True
        return False if namespace in IDENTIFIER_NAMESPACES else None

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
        from gene_annotation_episode.episodic_workflow.root.a104.blast_utility_result_views import IDENTIFIER_NAMESPACES
        if self.native_blast_utility_results.applies(context):
            resolved = self.native_blast_utility_results.resolve(context, reference, namespace)
        else:
            resolved = self.native_blast_utility_returns.resolve_received(context, reference, namespace)
        if resolved:
            return True
        return False if namespace in IDENTIFIER_NAMESPACES else None
