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


class APIExecutionParentAssignment:
    def assignment_schema(self, role, *, internal=False):
        if role != 'launch_api':
            raise ValueError('fixed_execution_role_required')
        self.credit_kind('launch_api')
        alternatives = [self._request_schema(key, selected=True, internal=internal) for key, config in self.resources.items() if KINDS[config['kind']] == {'launch_api': 'api', 'launch_local': 'local', 'launch_hpc': 'hpc'}['launch_api']]
        return {'anyOf': alternatives} if alternatives else {'not': {}}

    def prepare_assignment(self, parent, role, selection, scope, operation_key):
        if role != 'launch_api':
            raise ValueError('fixed_execution_role_required')
        selected = checked(selection, self.assignment_schema('launch_api', internal=True), 'invalid_execution_assignment')
        parent.role in ('hpc', 'hpc_execution') and False
        from gene_annotation_episode.episodic_workflow.root.library.lumpy_request_binding import is_compact_assignment as is_lumpy_assignment, is_compact_launch as is_lumpy_launch, read_request_binding as read_lumpy_binding
        from gene_annotation_episode.episodic_workflow.root.library.macs2_peak_request_binding import is_compact_assignment as is_macs2_assignment, is_compact_launch as is_macs2_launch, read_request_binding as read_macs2_binding
        from gene_annotation_episode.episodic_workflow.root.library.flux_balance_request_binding import is_compact_assignment, is_compact_launch, read_request_binding
        selected = self._validate_request(selected)
        if {'launch_api': 'api', 'launch_local': 'local', 'launch_hpc': 'hpc'}['launch_api'] == 'api':
            selected = self.api_execution.validate_assignment(selected, scope=scope)
        if {'launch_api': 'api', 'launch_local': 'local', 'launch_hpc': 'hpc'}['launch_api'] != KINDS[self.resources[selected['resource_id']]['kind']]:
            raise ValueError('execution_resource_kind_conflict')
        if parent.role != 'launch':
            raise ValueError('resource_child_role_owned_by_launch')
        original = self._launch(plain(parent.assignment))
        self._validate_blast_launch_selection(original, selected, scope)
        self._masking_inputs(parent, selected)
        self._utility_inputs(parent, selected)
        self._fluorescence_inputs(parent, selected)
        self._expression_nmf_inputs(parent, selected)
        self._flux_balance_inputs(parent, selected, input_versions=original['immutable_input_versions'])
        self._macs2_peak_inputs(parent, selected)
        self._lumpy_inputs(parent, selected)
        self._atac_inputs(parent, selected)
        self._chromatin_inputs(parent, selected)
        self._genomic_overlap_inputs(parent, selected)
        from gene_annotation_episode.episodic_workflow.root.protein_structure_operands import validate_protein_structure_job_inputs
        validate_protein_structure_job_inputs(self.store, parent, selected, returns=self.native_protein_structure_returns)
        self._versions(original['immutable_input_versions'], scope, context=parent, macs2_peak_assignments=[selected], lumpy_assignments=[selected], atac_assignments=[selected], nmf_assignments=[selected], fluorescence_assignments=[selected], flux_balance_assignments=[selected])
        from gene_annotation_episode.episodic_workflow.root.library.native_blast_database_result_publication import validate_native_job_inputs
        from gene_annotation_episode.episodic_workflow.root.library.native_blast_standard_database_result_publication import validate_standard_blast_job_inputs
        validate_native_job_inputs(self.store, parent, selected)
        validate_standard_blast_job_inputs(self.store, parent, selected)
        from gene_annotation_episode.episodic_workflow.root.library.rna_result_operand_authority import validate_rna_structure_job_inputs
        validate_rna_structure_job_inputs(self.store, parent, selected)
        return selected
