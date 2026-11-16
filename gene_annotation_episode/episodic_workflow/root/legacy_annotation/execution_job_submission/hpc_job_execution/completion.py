"""Private completion responsibility with original configured behavior."""
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


class HPCExecutionCompletion:
    def completion_for_action(self, context, operation_key):
        if context.role != 'launch_hpc' or context.run_id != self.run_id:
            raise ValueError('fixed_execution_context_required')
        if self.native_flux_balance_results is not None and self.native_flux_balance_results.applies(context):
            proof = self.native_flux_balance_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        if self.native_blast_masking_results.applies(context):
            proof = self.native_blast_masking_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        if self.native_blast_utility_results.applies(context):
            proof = self.native_blast_utility_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        if self.native_fluorescence_results.applies(context):
            proof = self.native_fluorescence_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        if self.native_expression_nmf_results is not None and self.native_expression_nmf_results.applies(context):
            proof = self.native_expression_nmf_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        if self.atac_results is not None and self.atac_results.applies(context):
            proof = self.atac_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        if self.native_chromatin_interaction_results is not None and self.native_chromatin_interaction_results.applies(context):
            proof = self.native_chromatin_interaction_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        if self.native_genomic_overlap_results is not None and self.native_genomic_overlap_results.applies(context):
            proof = self.native_genomic_overlap_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        if self.native_protein_structure_results.applies(context):
            proof = self.native_protein_structure_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        if self.rna_structure_comparison_results is not None and self.rna_structure_comparison_results.applies(context):
            proof = self.rna_structure_comparison_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        if self.native_rna_structure_results is not None and self.native_rna_structure_results.applies(context):
            proof = self.native_rna_structure_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        if self.native_blast_standard_database_results is not None and self.native_blast_standard_database_results.applies(context):
            proof = self.native_blast_standard_database_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        if self.native_blast_database_results is not None and self.native_blast_database_results.applies(context):
            proof = self.native_blast_database_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        return self._delegate(context).completion_for_action(self._practical_context(context), operation_key)
        if self.native_hmmer_preparation_results is not None and self.native_hmmer_preparation_results.applies(context):
            proof = self.native_hmmer_preparation_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        if self.native_infernal_preparation_results is not None and self.native_infernal_preparation_results.applies(context):
            proof = self.native_infernal_preparation_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        if self.native_blast_results is not None and self.native_blast_results.applies(context):
            proof = self.native_blast_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        if self.native_infernal_results is not None and self.native_infernal_results.applies(context):
            proof = self.native_infernal_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        if self.native_hmmer_results.applies(context):
            proof = self.native_hmmer_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        return self._proof_for_action(context, operation_key)

    def verify_completion(self, context, proof):
        if context.role != 'launch_hpc' or context.run_id != self.run_id:
            raise ValueError('fixed_execution_context_required')
        try:
            proof = validate_completion_proof(plain(proof))
        except (ValueError, TypeError):
            return False
        closed_verdict = self._closed_completion_verdict(context, proof)
        if closed_verdict is not None:
            return closed_verdict
        if self.native_flux_balance_results is not None and self.native_flux_balance_results.applies(context):
            return proof == self.native_flux_balance_results.completion(context)
        if self.native_blast_masking_results.applies(context):
            return proof == self.native_blast_masking_results.completion(context)
        if self.native_blast_utility_results.applies(context):
            return proof == self.native_blast_utility_results.completion(context)
        if self.native_fluorescence_results.applies(context):
            return proof == self.native_fluorescence_results.completion(context)
        if self.native_expression_nmf_results is not None and self.native_expression_nmf_results.applies(context):
            return proof == self.native_expression_nmf_results.completion(context)
        if self.atac_results is not None and self.atac_results.applies(context):
            return proof == self.atac_results.completion(context)
        if self.native_chromatin_interaction_results is not None and self.native_chromatin_interaction_results.applies(context):
            return proof == self.native_chromatin_interaction_results.completion(context)
        if self.native_genomic_overlap_results is not None and self.native_genomic_overlap_results.applies(context):
            return proof == self.native_genomic_overlap_results.completion(context)
        if self.native_protein_structure_results.applies(context):
            return proof == self.native_protein_structure_results.completion(context)
        if self.rna_structure_comparison_results is not None and self.rna_structure_comparison_results.applies(context):
            return proof == self.rna_structure_comparison_results.completion(context)
        if self.native_rna_structure_results is not None and self.native_rna_structure_results.applies(context):
            return proof == self.native_rna_structure_results.completion(context)
        if self.native_blast_standard_database_results is not None and self.native_blast_standard_database_results.applies(context):
            return proof == self.native_blast_standard_database_results.completion(context)
        if self.native_blast_database_results is not None and self.native_blast_database_results.applies(context):
            return proof == self.native_blast_database_results.completion(context)
        return self.state(context).verify_completion(proof)
        if self.native_hmmer_preparation_results is not None and self.native_hmmer_preparation_results.applies(context):
            return proof == self.native_hmmer_preparation_results.completion(context)
        if self.native_infernal_preparation_results is not None and self.native_infernal_preparation_results.applies(context):
            return proof == self.native_infernal_preparation_results.completion(context)
        if self.native_blast_results is not None and self.native_blast_results.applies(context):
            return proof == self.native_blast_results.completion(context)
        if self.native_infernal_results is not None and self.native_infernal_results.applies(context):
            return proof == self.native_infernal_results.completion(context)
        if self.native_hmmer_results.applies(context):
            return proof == self.native_hmmer_results.completion(context)
        return bool(proof and canonical(proof) == canonical(self._proof_for_action(context, proof.get('operation_key', ''))))

