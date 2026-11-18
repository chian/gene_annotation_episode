"""Private A107 Results from_parent"""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a107.resource_records import INPUT_VERSION_SCHEMA
from .binding_roles import KINDS
from .received_launch_records import LAUNCH_VERSION
from gene_annotation_episode.episodic_workflow.root.a107.local_file_capture_results import SELECTOR_SCHEMA as LOCAL_FILE_SOURCE_SELECTOR_SCHEMA
from gene_annotation_episode.episodic_workflow.root.a107.library.execution_result_contract import RESULTS_SCHEMA
from .binding_roles import ROLE_KINDS
from gene_annotation_episode.episodic_workflow.root.a107.launch_instructions import SELECTION_SCHEMA
from gene_annotation_episode.episodic_workflow.root.a107.execution_contracts import checked
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a107.local_file_capture_results import is_file_source_selector
from gene_annotation_episode.episodic_workflow.root.a107.native_blast_database_acquisition import is_native_blast_database_target
from gene_annotation_episode.episodic_workflow.root.a107.native_rna_structure_acquisition import is_native_rna_structure_target
from gene_annotation_episode.episodic_workflow.root.a107.native_blast_standard_database_acquisition import is_standard_blast_database_target
from gene_annotation_episode.episodic_workflow.root.a107.a107_execution_bindings import launch_request_schema
from gene_annotation_episode.episodic_workflow.root.a107.execution_contracts import obj
from gene_annotation_episode.episodic_workflow.root.a107.communication import plain
from gene_annotation_episode.episodic_workflow.root.a107.a107_execution_bindings import result_selector_conditions

class ResultsFromParent:

    def required_return_sources(self, parent, role):
        """Preserve the original job identity across a scientific owner return."""
        if parent is not None and parent.path[-1][0] == 'partner_presence_evidence' and getattr(self.services, 'annotation_task_required', lambda: False)():
            return ('execution_result_refs',)
        return ()

    def child_assignment_schema(self, parent, role):
        """A frozen HPC launch exposes only its already authorized request."""
        if parent.role == 'launch' and False:
            pass
        return self.assignment_schema(role)

    def assignment_schema(self, role, *, internal=False):
        self.credit_kind(role)
        schema = deepcopy(RESULTS_SCHEMA)
        schema['properties']['selector'].setdefault('allOf', []).append({'if': {'required': ['version'], 'properties': {'version': {'const': 'local_file_source_selector_v1'}}}, 'then': deepcopy(LOCAL_FILE_SOURCE_SELECTOR_SCHEMA)})
        schema['properties']['selector']['allOf'].extend(result_selector_conditions())
        if self.native_expression_nmf_results is not None:
            from gene_annotation_episode.episodic_workflow.root.a107.expression_nmf_result_contracts import EXPRESSION_NMF_RESULT_SELECTOR_SCHEMA
            schema['properties']['selector'].setdefault('allOf', []).append({'if': {'required': ['version'], 'properties': {'version': {'const': 'expression_nmf_result_selector_v1'}}}, 'then': deepcopy(EXPRESSION_NMF_RESULT_SELECTOR_SCHEMA)})
        if self.native_rna_structure_results is not None:
            from gene_annotation_episode.episodic_workflow.root.a107.rna_structure_result_views import RESULT_SELECTOR_SCHEMA
            from gene_annotation_episode.episodic_workflow.root.a107.rna_structure_comparison_contracts import RNA_COMPARISON_SELECTOR_SCHEMA
            alternatives = [*deepcopy(RESULT_SELECTOR_SCHEMA['oneOf']), deepcopy(RNA_COMPARISON_SELECTOR_SCHEMA)]
            versions = [branch['properties']['version']['const'] for branch in alternatives]
            schema['properties']['selector']['allOf'].append({'if': {'required': ['version'], 'properties': {'version': {'enum': versions}}}, 'then': {'oneOf': alternatives}})
        return schema

    def prepare_assignment(self, parent, role, selection, scope, operation_key):
        selected = checked(selection, self.assignment_schema(role, internal=True), 'invalid_execution_assignment')
        if parent.role in ('hpc', 'hpc_execution') and False:
            pass
        recorded = self._recorded_results_assignment(parent, selected, scope, operation_key)
        if recorded is not None:
            return recorded
        masking = self._retained_masking_target(parent, selected, scope)
        utility = self._retained_utility_target(parent, selected, scope)
        nmf = self._retained_expression_nmf_target(parent, selected, scope)
        target = nmf if nmf is not None else utility if utility is not None else masking if masking is not None else self.job_progress_provider.targets.read_target(selected['handoff_ref'], scope)
        self._selector(selected, target)
        if is_file_source_selector(selected.get('selector')):
            self.local_file_sources.admit(parent, selected, target)
        if self._masking_selector(selected):
            self.native_blast_masking_results.validate_selected_inputs(parent, selected)
        if self._utility_selector(selected):
            self.native_blast_utility_results.validate_selected_inputs(parent, selected)
        if self._comparison_selector(selected):
            from gene_annotation_episode.episodic_workflow.root.a107.rna_structure_comparison_operands import validate_rna_comparison_selected_inputs
            validate_rna_comparison_selected_inputs(self.store, parent, selected['selector'], anchor_handoff_ref=selected['handoff_ref'], returns=self.native_rna_structure_returns)
        elif is_native_rna_structure_target(target):
            from gene_annotation_episode.episodic_workflow.root.a107.native_rna_structure_result_publication import validate_rna_structure_selected_inputs
            validate_rna_structure_selected_inputs(self.store, parent, selected['selector'], handoff_ref=selected['handoff_ref'], returns=self.native_rna_structure_returns)
        if is_standard_blast_database_target(target):
            from gene_annotation_episode.episodic_workflow.root.a107.native_blast_standard_database_result_publication import validate_standard_blast_selected_inputs
            validate_standard_blast_selected_inputs(self.store, parent, selected['selector'], handoff_ref=selected['handoff_ref'])
        if is_native_blast_database_target(target):
            from gene_annotation_episode.episodic_workflow.root.a107.native_blast_database_result_publication import validate_selected_inputs
            validate_selected_inputs(self.store, parent, selected['selector'], handoff_ref=selected['handoff_ref'])
        return selected

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
