"""Private A107 Launch input versions"""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_information.received_result_readers import resolve_received_execution_reference
from gene_annotation_episode.episodic_workflow.root.a107.execution_contracts import canonical
import json
from gene_annotation_episode.episodic_workflow.root.a107.communication import plain

class LaunchInputVersions:

    def _masking_inputs(self, context, assignment):
        return self.native_blast_masking_results.validate_job_inputs(context, assignment)

    def _utility_inputs(self, context, assignment):
        return self.native_blast_utility_results.validate_job_inputs(context, assignment)

    def _expression_nmf_inputs(self, context, assignment):
        if 'native_expression_nmf' not in assignment.get('requested_job', {}):
            return []
        from gene_annotation_episode.episodic_workflow.root.a107.expression_nmf_operands import validate_expression_nmf_job_inputs
        return validate_expression_nmf_job_inputs(self.store, context, assignment, reference_access=resolve_received_execution_reference.__get__(self))

    def _versions(self, versions, scope, *, context, nmf_assignments=()):
        from gene_annotation_episode.episodic_workflow.root.a107.execution_input_versions import validate_execution_input_versions
        return validate_execution_input_versions(self, versions, scope, context=context, nmf_assignments=nmf_assignments)
