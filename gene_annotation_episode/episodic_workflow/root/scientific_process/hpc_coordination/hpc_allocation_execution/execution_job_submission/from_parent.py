"""Private from_parent responsibility with original configured behavior."""
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


class ExecutionSubmissionParentAssignment:
    def assignment_schema(self, role, *, internal=False):
        if role != 'launch':
            raise ValueError('fixed_execution_role_required')
        self.credit_kind('launch')
        schema = obj({'version': {'const': LAUNCH_VERSION}, 'requests': {'type': 'object', 'properties': {key: {'anyOf': [self._request_schema(key, selected=False, internal=internal, compact=False), {**deepcopy(BLAST_GRADED_REQUEST_SCHEMA), 'properties': {**deepcopy(BLAST_GRADED_REQUEST_SCHEMA['properties']), 'resource_id': {'const': key}}}]} if self.resources[key].get('service') == 'ncbi_blast' else self._request_schema(key, selected=False, internal=internal, compact=False) for key in self.resources}, 'minProperties': 1, 'additionalProperties': False}, 'immutable_input_versions': {'type': 'array', 'items': deepcopy(INPUT_VERSION_SCHEMA)}, 'constraints': {'type': 'object'}})
        schema['properties']['launch_instructions'] = deepcopy(SELECTION_SCHEMA)
        alternatives = [schema]
        if any((value.get('native_flux_balance') for value in self.resources.values())):
            from gene_annotation_episode.episodic_workflow.root.library.flux_balance_request_binding import launch_assignment_schema
            alternatives.append(launch_assignment_schema(self.resources))
        if any((value.get('native_macs2_peak') for value in self.resources.values())):
            from gene_annotation_episode.episodic_workflow.root.library.macs2_peak_request_binding import launch_assignment_schema
            alternatives.append(launch_assignment_schema(self.resources))
        if any((value.get('native_lumpy') for value in self.resources.values())):
            from gene_annotation_episode.episodic_workflow.root.library.lumpy_request_binding import launch_assignment_schema
            alternatives.append(launch_assignment_schema(self.resources))
        return {'anyOf': alternatives} if len(alternatives) > 1 else schema

    def prepare_assignment(self, parent, role, selection, scope, operation_key):
        if role != 'launch':
            raise ValueError('fixed_execution_role_required')
        selected = checked(selection, self.assignment_schema('launch', internal=True), 'invalid_execution_assignment')
        if parent.role in ('hpc', 'hpc_execution') and True:
            from gene_annotation_episode.episodic_workflow.root.library.hpc_launch_authentication import authenticate_launch
            authenticate_launch(parent, selected, operation_key, self.directory)
        from gene_annotation_episode.episodic_workflow.root.library.lumpy_request_binding import is_compact_assignment as is_lumpy_assignment, is_compact_launch as is_lumpy_launch, read_request_binding as read_lumpy_binding
        if is_lumpy_launch(selected):
            return self.lumpy_requests.preview(parent, selected)[0]
        from gene_annotation_episode.episodic_workflow.root.library.macs2_peak_request_binding import is_compact_assignment as is_macs2_assignment, is_compact_launch as is_macs2_launch, read_request_binding as read_macs2_binding
        if is_macs2_launch(selected):
            return self.macs2_peak_requests.preview(parent, selected)[0]
        from gene_annotation_episode.episodic_workflow.root.library.flux_balance_request_binding import is_compact_assignment, is_compact_launch, read_request_binding
        if is_compact_launch(selected):
            return self.flux_balance_requests.preview(parent, selected)[0]
        selected = self._launch(selected, scope=scope)
        from gene_annotation_episode.episodic_workflow.root.protein_structure_operands import validate_protein_structure_job_inputs
        for request in selected['requests'].values():
            self._masking_inputs(parent, request)
            self._utility_inputs(parent, request)
            self._fluorescence_inputs(parent, request)
            self._expression_nmf_inputs(parent, request)
            self._flux_balance_inputs(parent, request, input_versions=selected['immutable_input_versions'])
            self._macs2_peak_inputs(parent, request)
            self._lumpy_inputs(parent, request)
            self._atac_inputs(parent, request)
            self._chromatin_inputs(parent, request)
            self._genomic_overlap_inputs(parent, request)
            validate_protein_structure_job_inputs(self.store, parent, request, returns=self.native_protein_structure_returns)
        self._versions(selected['immutable_input_versions'], scope, context=parent, macs2_peak_assignments=selected['requests'].values(), lumpy_assignments=selected['requests'].values(), atac_assignments=selected['requests'].values(), nmf_assignments=selected['requests'].values(), fluorescence_assignments=selected['requests'].values(), flux_balance_assignments=selected['requests'].values())
        from gene_annotation_episode.episodic_workflow.root.library.native_blast_database_result_publication import validate_native_job_inputs
        from gene_annotation_episode.episodic_workflow.root.library.native_blast_standard_database_result_publication import validate_standard_blast_job_inputs
        for request in selected['requests'].values():
            validate_native_job_inputs(self.store, parent, request)
            validate_standard_blast_job_inputs(self.store, parent, request)
            from gene_annotation_episode.episodic_workflow.root.library.rna_result_operand_authority import validate_rna_structure_job_inputs
            validate_rna_structure_job_inputs(self.store, parent, request)
        return selected

