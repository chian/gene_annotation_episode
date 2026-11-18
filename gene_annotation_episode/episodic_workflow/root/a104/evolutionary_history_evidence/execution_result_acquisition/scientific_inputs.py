"""Private A104 Results scientific inputs."""
from __future__ import annotations

class ResultsScientificInputs:

    def _masking_inputs(self, context, assignment):
        return self.native_blast_masking_results.validate_job_inputs(context, assignment)

    def _utility_inputs(self, context, assignment):
        return self.native_blast_utility_results.validate_job_inputs(context, assignment)

    def _versions(self, versions, scope, *, context):
        from gene_annotation_episode.episodic_workflow.root.a104.library.execution_input_versions import validate_execution_input_versions
        return validate_execution_input_versions(self, versions, scope, context=context)
