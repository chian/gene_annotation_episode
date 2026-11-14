"""Private goal responsibility with original configured behavior."""
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


class ResultAcquisitionGoal:
    def instructions(self, context):
        if context.role != 'results' or context.run_id != self.run_id:
            raise ValueError('fixed_execution_context_required')
        from gene_annotation_episode.episodic_workflow.root.library.rna_structure_comparison_presentation import is_rna_comparison_results_context
        assignment = plain(context.assignment)
        if is_rna_comparison_results_context({'execution_assignment': assignment}):
            from gene_annotation_episode.episodic_workflow.root.rna_structure_comparison_prompt import rna_comparison_results_instructions
            return rna_comparison_results_instructions(assignment)
        from gene_annotation_episode.episodic_workflow.root.library.rna_structure_presentation import is_rna_structure_results_context
        if is_rna_structure_results_context({'execution_assignment': assignment}):
            from gene_annotation_episode.episodic_workflow.root.rna_structure_prompt import rna_structure_results_instructions
            job = self._target(context)['assignment']['requested_job']['native_rna_structure']
            return rna_structure_results_instructions(assignment, job=job)
        return 'Acquire the original selected execution results through the original handoff. Choose bounded status or requested file/page reads using actual preceding outcomes. Preserve partial bytes and native scores. Native paths expose the current resource filesystem: the exact attempt observation does not establish that current file bytes were produced by that attempt. Separate read windows are not an atomic file snapshot. The scientific parent interprets the returned records. Original work, resource and selector stay fixed. Only actual complete acquisition establishes this endpoint.'
        return 'Choose which permitted concrete execution request to commission on an explicit resource_id. Capabilities, recorded inventory and timing information inform the choice. Preserve the original job, immutable inputs, constraints and pinned instructions. A resource child owns iterative execution in the shared loop. Receive its requested typed handoff; no infrastructure chooses an approach. Actual received usable handoff completes this launch endpoint with exact zero future credit.'

