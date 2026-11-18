"""Private A107 Launch context receipts"""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a107.native_blast_database_acquisition import is_native_blast_database_target
from gene_annotation_episode.episodic_workflow.root.a107.native_rna_structure_acquisition import is_native_rna_structure_target
from gene_annotation_episode.episodic_workflow.root.a107.native_blast_standard_database_acquisition import is_standard_blast_database_target
from gene_annotation_episode.episodic_workflow.root.a107.communication import plain

class LaunchContextReceipts:

    def required_return_sources(self, parent, role):
        """Preserve the original job identity across a scientific owner return."""
        if parent is not None and parent.path[-1][0] == 'partner_presence_evidence' and getattr(self.services, 'annotation_task_required', lambda: False)():
            return ('execution_handoff_refs',)
        return ()

    def initial_references(self, context):
        if context.role != 'results':
            assignment = plain(context.assignment)
            requests = assignment.get('requests', {}).values() if context.role == 'launch' else [assignment] if context.role == 'launch_local' else []
            references = []
            from gene_annotation_episode.episodic_workflow.root.a107.native_rna_structure_result_publication import validate_rna_structure_job_inputs
            for request in requests:
                references.extend(validate_rna_structure_job_inputs(self.store, context, request))
                references.extend(self._masking_inputs(context, request))
                references.extend(self._utility_inputs(context, request))
                references.extend(self._expression_nmf_inputs(context, request))
            return list(dict.fromkeys(references))
        assignment = plain(context.assignment)
        target = self._target(context)
        if self.native_blast_masking_results.applies(context):
            self._selector(assignment, target)
            return self.native_blast_masking_results.validate_selected_inputs(context, assignment)
        if self.native_blast_utility_results.applies(context):
            self._selector(assignment, target)
            return self.native_blast_utility_results.validate_selected_inputs(context, assignment)
        selected = [assignment['handoff_ref']]
        if self.native_expression_nmf_results is not None and self.native_expression_nmf_results.applies(context):
            selector = self._selector(assignment, target)
            if selector['mode'] == 'saved_sheet_recalculation':
                self.native_expression_nmf_returns.authenticate_received_saved_sheet(context, selector['saved_sheet_file'])
                selected.append(selector['saved_sheet_file']['artifact_ref'])
            return list(dict.fromkeys(selected))
        if self._comparison_selector(assignment):
            from gene_annotation_episode.episodic_workflow.root.a107.rna_structure_comparison_operands import validate_rna_comparison_selected_inputs
            selected.extend(validate_rna_comparison_selected_inputs(self.store, context, assignment['selector'], anchor_handoff_ref=assignment['handoff_ref'], returns=self.native_rna_structure_returns))
        elif is_native_rna_structure_target(target):
            from gene_annotation_episode.episodic_workflow.root.a107.native_rna_structure_result_publication import validate_rna_structure_selected_inputs
            selected.extend(validate_rna_structure_selected_inputs(self.store, context, assignment['selector'], handoff_ref=assignment['handoff_ref'], returns=self.native_rna_structure_returns))
        if is_standard_blast_database_target(target):
            from gene_annotation_episode.episodic_workflow.root.a107.native_blast_standard_database_result_publication import validate_standard_blast_selected_inputs
            selected.extend(validate_standard_blast_selected_inputs(self.store, context, assignment['selector'], handoff_ref=assignment['handoff_ref']))
        if is_native_blast_database_target(target):
            from gene_annotation_episode.episodic_workflow.root.a107.native_blast_database_result_publication import validate_selected_inputs
            selected.extend(validate_selected_inputs(self.store, context, assignment['selector'], handoff_ref=assignment['handoff_ref']))
        return list(dict.fromkeys(selected))
