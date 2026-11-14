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


class ResultAcquisitionParentAssignment:
    def assignment_schema(self, role, *, internal=False):
        if role != 'results':
            raise ValueError('fixed_execution_role_required')
        self.credit_kind('results')
        schema = deepcopy(RESULTS_SCHEMA)
        schema['properties']['selector'].setdefault('allOf', []).append({'if': {'required': ['version'], 'properties': {'version': {'const': 'local_file_source_selector_v1'}}}, 'then': deepcopy(LOCAL_FILE_SOURCE_SELECTOR_SCHEMA)})
        schema['properties']['selector']['allOf'].append({'if': {'required': ['version'], 'properties': {'version': {'const': MACS2_FILE_SOURCE_SELECTOR_VERSION}}}, 'then': deepcopy(MACS2_FILE_SOURCE_SELECTOR_SCHEMA)})
        schema['properties']['selector']['allOf'].append({'if': {'required': ['version'], 'properties': {'version': {'const': LUMPY_FILE_SOURCE_SELECTOR_VERSION}}}, 'then': deepcopy(LUMPY_FILE_SOURCE_SELECTOR_SCHEMA)})
        from gene_annotation_episode.episodic_workflow.root.library.sequence_masking_result_views import NATIVE_BLAST_MASKING_RESULT_SELECTOR_SCHEMA
        schema['properties']['selector'].setdefault('allOf', []).append({'if': {'required': ['version'], 'properties': {'version': {'const': 'native_blast_masking_result_selector_v1'}}}, 'then': deepcopy(NATIVE_BLAST_MASKING_RESULT_SELECTOR_SCHEMA)})
        from gene_annotation_episode.episodic_workflow.root.library.blast_utility_result_views import NATIVE_BLAST_UTILITY_RESULT_SELECTOR_SCHEMA
        schema['properties']['selector'].setdefault('allOf', []).append({'if': {'required': ['version'], 'properties': {'version': {'enum': ['native_blast_utility_result_selector_v1', 'native_blast_utility_result_selector_v2']}}}, 'then': deepcopy(NATIVE_BLAST_UTILITY_RESULT_SELECTOR_SCHEMA)})
        from gene_annotation_episode.episodic_workflow.root.library.fluorescence_result_contracts import FLUORESCENCE_RESULT_SELECTOR_SCHEMA
        schema['properties']['selector'].setdefault('allOf', []).append({'if': {'required': ['version'], 'properties': {'version': {'const': 'fluorescence_result_selector_v1'}}}, 'then': deepcopy(FLUORESCENCE_RESULT_SELECTOR_SCHEMA)})
        if self.native_expression_nmf_results is not None:
            from gene_annotation_episode.episodic_workflow.root.library.expression_nmf_result_contracts import EXPRESSION_NMF_RESULT_SELECTOR_SCHEMA
            schema['properties']['selector'].setdefault('allOf', []).append({'if': {'required': ['version'], 'properties': {'version': {'const': 'expression_nmf_result_selector_v1'}}}, 'then': deepcopy(EXPRESSION_NMF_RESULT_SELECTOR_SCHEMA)})
        if self.native_flux_balance_results is not None:
            from gene_annotation_episode.episodic_workflow.root.library.flux_balance_result_selection import FBA_RESULT_SELECTOR_SCHEMA
            schema['properties']['selector'].setdefault('allOf', []).append({'if': {'required': ['version'], 'properties': {'version': {'const': 'flux_balance_result_selector_v1'}}}, 'then': deepcopy(FBA_RESULT_SELECTOR_SCHEMA)})
        if self.atac_results is not None:
            from gene_annotation_episode.episodic_workflow.root.library.atac_differential_execution_information import atac_result_selector_schema
            schema['properties']['selector'].setdefault('allOf', []).append({'if': {'required': ['version'], 'properties': {'version': {'const': 'atac_differential_result_selector_v1'}}}, 'then': atac_result_selector_schema()})
        if self.native_chromatin_interaction_results is not None:
            from gene_annotation_episode.episodic_workflow.root.library.chromatin_interaction_execution_information import chromatin_result_selector_schema
            schema['properties']['selector'].setdefault('allOf', []).append({'if': {'required': ['version'], 'properties': {'version': {'const': 'chromatin_interaction_result_selector_v1'}}}, 'then': chromatin_result_selector_schema()})
        if self.native_rna_structure_results is not None:
            from gene_annotation_episode.episodic_workflow.root.library.rna_structure_result_views import RESULT_SELECTOR_SCHEMA
            from gene_annotation_episode.episodic_workflow.root.library.rna_structure_comparison_contracts import RNA_COMPARISON_SELECTOR_SCHEMA
            alternatives = [*deepcopy(RESULT_SELECTOR_SCHEMA['oneOf']), deepcopy(RNA_COMPARISON_SELECTOR_SCHEMA)]
            versions = [branch['properties']['version']['const'] for branch in alternatives]
            schema['properties']['selector'].setdefault('allOf', []).append({'if': {'required': ['version'], 'properties': {'version': {'enum': versions}}}, 'then': {'oneOf': alternatives}})
        if any((configuration.get('native_protein_structure') for configuration in self.resources.values())):
            from gene_annotation_episode.episodic_workflow.root.library.protein_structure_selection import protein_structure_result_selector_schema
            schema['properties']['selector'].setdefault('allOf', []).append({'if': {'required': ['version'], 'properties': {'version': {'const': 'protein_structure_result_selector_v1'}}}, 'then': protein_structure_result_selector_schema()})
        if self.native_genomic_overlap_results is not None:
            from gene_annotation_episode.episodic_workflow.root.library.genomic_overlap_execution_information import genomic_overlap_result_selector_schema
            schema['properties']['selector'].setdefault('allOf', []).append({'if': {'required': ['version'], 'properties': {'version': {'const': 'genomic_overlap_result_selector_v1'}}}, 'then': genomic_overlap_result_selector_schema()})
        return schema

    def prepare_assignment(self, parent, role, selection, scope, operation_key):
        if role != 'results':
            raise ValueError('fixed_execution_role_required')
        selected = checked(selection, self.assignment_schema('results', internal=True), 'invalid_execution_assignment')
        parent.role in ('hpc', 'hpc_execution') and False
        if is_macs2_file_source_selector(selected.get('selector')) or is_lumpy_file_source_selector(selected.get('selector')):
            self.local_file_sources.admit_handoff(parent, selected)
        recorded = self._recorded_results_assignment(parent, selected, scope, operation_key)
        if recorded is not None:
            return recorded
        from gene_annotation_episode.episodic_workflow.root.library.lumpy_request_binding import is_compact_assignment as is_lumpy_assignment, is_compact_launch as is_lumpy_launch, read_request_binding as read_lumpy_binding
        from gene_annotation_episode.episodic_workflow.root.library.macs2_peak_request_binding import is_compact_assignment as is_macs2_assignment, is_compact_launch as is_macs2_launch, read_request_binding as read_macs2_binding
        from gene_annotation_episode.episodic_workflow.root.library.flux_balance_request_binding import is_compact_assignment, is_compact_launch, read_request_binding
        masking_target = self._retained_masking_target(parent, selected, scope)
        utility_target = self._retained_utility_target(parent, selected, scope)
        fluorescence_target = self._retained_fluorescence_target(parent, selected, scope)
        nmf_target = self._retained_expression_nmf_target(parent, selected, scope)
        atac_target = self._retained_atac_target(parent, selected, scope)
        chromatin_target = self._retained_chromatin_target(parent, selected, scope)
        overlap_target = self._retained_genomic_overlap_target(parent, selected, scope)
        retained = self._retained_protein_result(parent, selected, scope)
        flux_balance_target = self._retained_flux_balance_target(parent, selected, scope)
        target = flux_balance_target if flux_balance_target is not None else utility_target if utility_target is not None else masking_target if masking_target is not None else fluorescence_target if fluorescence_target is not None else nmf_target if nmf_target is not None else atac_target if atac_target is not None else chromatin_target if chromatin_target is not None else overlap_target if overlap_target is not None else retained['body']['intent']['target'] if retained is not None else self.job_progress_provider.targets.read_target(selected['handoff_ref'], scope)
        self._selector(selected, target)
        if is_file_source_selector(selected.get('selector')):
            self.local_file_sources.admit(parent, selected, target)
        if self._masking_selector(selected):
            self.native_blast_masking_results.validate_selected_inputs(parent, selected)
        if self._utility_selector(selected):
            self.native_blast_utility_results.validate_selected_inputs(parent, selected)
        if is_native_protein_structure_target(target):
            from gene_annotation_episode.episodic_workflow.root.protein_structure_operands import validate_protein_structure_selected_inputs
            validate_protein_structure_selected_inputs(self.store, parent, selected['selector'], handoff_ref=selected['handoff_ref'], returns=self.native_protein_structure_returns)
        if self._comparison_selector(selected):
            from gene_annotation_episode.episodic_workflow.root.rna_structure_comparison_operands import validate_rna_comparison_selected_inputs
            validate_rna_comparison_selected_inputs(self.store, parent, selected['selector'], anchor_handoff_ref=selected['handoff_ref'], returns=self.native_rna_structure_returns)
        elif is_native_rna_structure_target(target):
            from gene_annotation_episode.episodic_workflow.root.library.rna_result_operand_authority import validate_rna_structure_selected_inputs
            validate_rna_structure_selected_inputs(self.store, parent, selected['selector'], handoff_ref=selected['handoff_ref'], returns=self.native_rna_structure_returns)
        if is_standard_blast_database_target(target):
            from gene_annotation_episode.episodic_workflow.root.library.native_blast_standard_database_result_publication import validate_standard_blast_selected_inputs
            validate_standard_blast_selected_inputs(self.store, parent, selected['selector'], handoff_ref=selected['handoff_ref'])
        if is_native_blast_database_target(target):
            from gene_annotation_episode.episodic_workflow.root.library.native_blast_database_result_publication import validate_selected_inputs
            validate_selected_inputs(self.store, parent, selected['selector'], handoff_ref=selected['handoff_ref'])
        from gene_annotation_episode.episodic_workflow.root.bvbrc_data_host import is_bvbrc_request
        if target['resource_kind'] == 'api' and is_bvbrc_request(target['assignment'].get('request')):
            self.api_execution.bvbrc_data.validate_inputs(parent, selected['selector'], request=target['assignment']['request'])
        if target['resource_kind'] == 'api' and target['assignment'].get('service') == 'bvbrc_minhash':
            self.api_execution.minhash.validate_commission_inputs(parent, selected, request=target['assignment']['request'], scope=scope, operation_key=operation_key)
        return selected

