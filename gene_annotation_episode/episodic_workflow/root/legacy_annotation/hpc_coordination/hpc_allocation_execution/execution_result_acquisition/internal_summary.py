"""Private internal_summary responsibility with original configured behavior."""
from __future__ import annotations
import base64
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
from gene_annotation_episode.domain import identity
from gene_annotation_episode.episodic_workflow.root.communication import plain
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.immutable_json_records import _immutable, _read
from gene_annotation_episode.execution_contracts import checked, obj
from gene_annotation_episode.episodic_workflow.root.communication import validate_form
from gene_annotation_episode.episodic_workflow.root.execution_source_declarations import (VERSION, LAUNCH_VERSION, RESULTS_VERSION, RESULT_PROVIDER, _CLOSED_CREDIT, ROLES, KINDS, ROLE_KINDS, TEXT, OFFSET, LIMIT, FILE_LIMIT, NATIVE_RESULT_ORIGIN, NATIVE_RESULT_ORIGIN_SCHEMA, RESULTS_SCHEMA, BLAST_GRADED_REQUEST_VERSION, BLAST_GRADED_REQUEST_SCHEMA, BLAST_GRADED_RETURN_SOURCE, BLAST_GRADED_RETURN_SCHEMA, NATIVE_SELECTOR_SCHEMA, launch_operation_catalog, native_result_operation_catalog, _outcome, LOCAL_FILE_SOURCE_SELECTOR_SCHEMA, MACS2_FILE_SOURCE_SELECTOR_SCHEMA, MACS2_FILE_SOURCE_SELECTOR_VERSION, LUMPY_FILE_SOURCE_SELECTOR_SCHEMA, LUMPY_FILE_SOURCE_SELECTOR_VERSION, LOCAL_FILE_SOURCE_RECEIPT_VERSION, LOCAL_FILE_SOURCE_PROVIDER, is_file_source_selector, is_macs2_file_source_selector, is_lumpy_file_source_selector, ASSIGNMENT_SCHEMA, GENERIC_REQUESTED_JOB_SCHEMA, INPUT_VERSION_SCHEMA, SELECTION_SCHEMA, validate_assignment, validate_completion_proof, operation_catalog, confined, PracticalReceiptInformation, LocalFileSourceResults, is_native_hmmer_target, is_native_blast_target, is_native_blast_masking_target, is_native_blast_utility_target, is_native_blast_database_target, is_standard_blast_database_target, is_native_infernal_target, is_native_infernal_preparation_target, is_native_hmmer_preparation_target, is_native_rna_structure_target, is_native_protein_structure_target)


class ResultAcquisitionInternalSummary:
    def decision_context(self, context, current_view):
        if context.role != 'results' or context.run_id != self.run_id:
            raise ValueError('fixed_execution_context_required')
        from gene_annotation_episode.episodic_workflow.root.library.lumpy_request_binding import is_compact_assignment as is_lumpy_assignment
        if is_lumpy_assignment(plain(context.assignment)):
            progress = self.state(context).credit_view()
            return self._with_selected_execution_task(context, {'practical_assignment': plain(context.assignment), 'practical_progress': {key: deepcopy(progress[key]) for key in ('credit', 'satisfied_keys') if key in progress}, 'practical_completed': self.state(context).completion_proof() is not None})
        from gene_annotation_episode.episodic_workflow.root.library.macs2_peak_request_binding import is_compact_assignment as is_macs2_assignment
        if is_macs2_assignment(plain(context.assignment)):
            progress = self.state(context).credit_view()
            return self._with_selected_execution_task(context, {'practical_assignment': plain(context.assignment), 'practical_progress': {key: deepcopy(progress[key]) for key in ('credit', 'satisfied_keys') if key in progress}, 'practical_completed': self.state(context).completion_proof() is not None})
        from gene_annotation_episode.episodic_workflow.root.library.flux_balance_request_binding import is_compact_assignment
        if is_compact_assignment(plain(context.assignment)):
            state = self.state(context)
            progress = state.credit_view()
            return {'practical_assignment': plain(context.assignment), 'practical_progress': {key: deepcopy(progress[key]) for key in ('credit', 'satisfied_keys') if key in progress}, 'practical_completed': state.completion_proof() is not None}
        value = {'execution_assignment': plain(context.assignment), 'execution_progress': self.facts(context, {})}
        assignment = plain(context.assignment)
        if self.local_file_sources.applies(context):
            from gene_annotation_episode.episodic_workflow.root.local_file_capture_results import ORIGIN
            value['execution_target'] = {'resource_kind': 'local', **({'output_roles': deepcopy(assignment['selector']['output_roles'])} if is_macs2_file_source_selector(assignment['selector']) or is_lumpy_file_source_selector(assignment['selector']) else {'files': deepcopy(assignment['selector']['files'])})}
            value['execution_target_description'] = {'status_operations': ['execution.results.status'], 'acquisition_operations': ['execution.results.collect'], 'provenance': deepcopy(ORIGIN)}
            return self._with_selected_execution_task(context, value)
        retained = self._retained_protein_result(context, assignment, context.scope)
        if self._flux_balance_selector(assignment):
            from gene_annotation_episode.episodic_workflow.root.library.flux_balance_request_binding import scientific_job_view
            target = self._target(context)
            value['execution_target'] = {'resource_kind': 'local', 'request': scientific_job_view(target['assignment']['requested_job']['native_flux_balance'])}
            value['execution_target_description'] = {'operation': 'perform_flux_balance_analysis', 'mode': assignment['selector']['mode'], 'status_operations': ['execution.results.status'], 'acquisition_operations': ['execution.results.collect']}
        elif self._fluorescence_selector(assignment):
            from gene_annotation_episode.episodic_workflow.root.library.fluorescence_execution_information import describe_fluorescence_result
            value['execution_target'] = self._target(context)
            value['execution_target_description'] = describe_fluorescence_result(value['execution_target'], selector=assignment['selector'])
        elif self._expression_nmf_selector(assignment):
            from gene_annotation_episode.episodic_workflow.root.library.expression_nmf_execution_information import describe_expression_nmf_result
            value['execution_target'] = self._target(context)
            value['execution_target_description'] = describe_expression_nmf_result(value['execution_target'], selector=assignment['selector'])
        elif self._atac_selector(assignment):
            from gene_annotation_episode.episodic_workflow.root.library.atac_differential_execution_information import describe_atac_result
            value['execution_target'] = self._target(context)
            value['execution_target_description'] = describe_atac_result(value['execution_target'], selector=assignment['selector'])
        elif self._chromatin_selector(assignment):
            from gene_annotation_episode.episodic_workflow.root.library.chromatin_interaction_execution_information import describe_chromatin_result
            value['execution_target'] = self._target(context)
            value['execution_target_description'] = describe_chromatin_result(value['execution_target'], selector=assignment['selector'])
        elif self._genomic_overlap_selector(assignment):
            from gene_annotation_episode.episodic_workflow.root.library.genomic_overlap_execution_information import describe_genomic_overlap_result
            value['execution_target'] = self._target(context)
            value['execution_target_description'] = describe_genomic_overlap_result(value['execution_target'], selector=assignment['selector'])
        elif retained is None:
            value['execution_target'] = self._target(context)
            value['execution_target_description'] = self.job_progress_provider.targets.describe_target(value['execution_target']['handle'], context.scope, selector=assignment['selector'])
        else:
            from gene_annotation_episode.episodic_workflow.root.library.protein_structure_execution_information import describe_protein_structure_result
            value['execution_target'] = retained['body']['intent']['target']
            called = retained['body']['handoff_proof']['body']['receipt']['tool_name']
            value['execution_target_description'] = describe_protein_structure_result(value['execution_target'], called_operation=called, selector=assignment['selector'])
        from gene_annotation_episode.episodic_workflow.root.bvbrc_data_host import is_bvbrc_request
        if value['execution_target']['resource_kind'] == 'api' and is_bvbrc_request(value['execution_target']['assignment'].get('request')):
            value['own_bvbrc_values'] = self.api_execution.bvbrc_data.own_values(context)
        return self._with_selected_execution_task(context, value)
