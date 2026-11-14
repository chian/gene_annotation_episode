"""Private report_delivery responsibility with original returned-value semantics."""
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


class ExecutionSubmissionReportDelivery:
    def facts(self, context, completion_snapshot):
        if context.role != 'launch' or context.run_id != self.run_id:
            raise ValueError('fixed_execution_context_required')
        return {**self._live_facts(context, completion_snapshot), **self._closed_credit_facts(context, completion_snapshot)}

    def _live_facts(self, context, completion_snapshot):
        from gene_annotation_episode.episodic_workflow.root.library.hmmer_native_result_views import FAMILY_SOURCES
        native_empty = {source: [] for source in FAMILY_SOURCES.values()}
        if self.native_flux_balance_results is not None:
            from gene_annotation_episode.episodic_workflow.root.library.flux_balance_return_views import fba_fact_sources
            native_empty.update({source: [] for source in fba_fact_sources()})
            if self.native_flux_balance_results.applies(context):
                return {**native_empty, **self.native_flux_balance_results.facts(context)}
        from gene_annotation_episode.episodic_workflow.root.library.sequence_masking_result_views import masking_fact_sources
        native_empty.update({source: [] for source in masking_fact_sources()})
        from gene_annotation_episode.episodic_workflow.root.library.blast_utility_result_views import blast_utility_fact_sources
        native_empty.update({source: [] for source in blast_utility_fact_sources()})
        if self.native_blast_masking_results.applies(context):
            return {**native_empty, **self.native_blast_masking_results.facts(context)}
        if self.native_blast_utility_results.applies(context):
            return {**native_empty, **self.native_blast_utility_results.facts(context)}
        from gene_annotation_episode.episodic_workflow.root.library.fluorescence_return_views import FACT_SOURCES as FLUORESCENCE_SOURCES
        native_empty.update({source: [] for source in FLUORESCENCE_SOURCES})
        if self.native_fluorescence_results.applies(context):
            return {**native_empty, **self.native_fluorescence_results.facts(context)}
        if self.native_expression_nmf_results is not None:
            from gene_annotation_episode.episodic_workflow.root.library.expression_nmf_return_views import FACT_SOURCES
            native_empty.update({source: [] for source in FACT_SOURCES})
            if self.native_expression_nmf_results.applies(context):
                return {**native_empty, **self.native_expression_nmf_results.facts(context)}
        if self.atac_results is not None:
            from gene_annotation_episode.episodic_workflow.root.library.atac_differential_return_views import FACT_SOURCES
            native_empty.update({source: [] for source in FACT_SOURCES})
            if self.atac_results.applies(context):
                return {**native_empty, **self.atac_results.facts(context)}
        if self.native_chromatin_interaction_results is not None:
            from gene_annotation_episode.episodic_workflow.root.library.chromatin_interaction_return_views import FACT_SOURCES
            native_empty.update({source: [] for source in FACT_SOURCES})
            if self.native_chromatin_interaction_results.applies(context):
                return {**native_empty, **self.native_chromatin_interaction_results.facts(context)}
        if self.native_genomic_overlap_results is not None:
            from gene_annotation_episode.episodic_workflow.root.library.genomic_overlap_return_views import FACT_SOURCES
            native_empty.update({source: [] for source in FACT_SOURCES})
            if self.native_genomic_overlap_results.applies(context):
                return {**native_empty, **self.native_genomic_overlap_results.facts(context)}
        from gene_annotation_episode.episodic_workflow.root.library.protein_structure_result_views import protein_structure_fact_sources
        native_empty.update({source: [] for source in protein_structure_fact_sources()})
        if self.native_protein_structure_results.applies(context):
            return {**native_empty, **self.native_protein_structure_results.facts(context, verify_artifacts=False)}
        if self.rna_structure_comparison_results is not None:
            from gene_annotation_episode.episodic_workflow.root.library.rna_structure_comparison_views import rna_comparison_fact_sources
            native_empty.update({source: [] for source in rna_comparison_fact_sources()})
            if self.rna_structure_comparison_results.applies(context):
                from gene_annotation_episode.episodic_workflow.root.library.rna_structure_result_views import rna_structure_fact_sources
                native_empty.update({source: [] for source in rna_structure_fact_sources()})
                return {**native_empty, **self.rna_structure_comparison_results.facts(context)}
        if self.native_rna_structure_results is not None:
            from gene_annotation_episode.episodic_workflow.root.library.rna_structure_result_views import rna_structure_fact_sources
            native_empty.update({source: [] for source in rna_structure_fact_sources()})
            if self.native_rna_structure_results.applies(context):
                return {**native_empty, **self.native_rna_structure_results.facts(context)}
        if self.native_blast_standard_database_results is not None:
            from gene_annotation_episode.episodic_workflow.root.native_blast_standard_database_results import empty_facts
            native_empty.update(empty_facts())
            if self.native_blast_standard_database_results.applies(context):
                return {**native_empty, **self.native_blast_standard_database_results.facts(context)}
        if self.native_blast_database_results is not None:
            from gene_annotation_episode.episodic_workflow.root.native_blast_database_results import empty_facts
            native_empty.update(empty_facts())
            if self.native_blast_database_results.applies(context):
                return {**native_empty, **self.native_blast_database_results.facts(context)}
        if self.native_hmmer_preparation_results is not None:
            from gene_annotation_episode.episodic_workflow.root.library.hmmer_preparation_result_views import preparation_fact_sources
            native_empty.update({source: [] for source in preparation_fact_sources()})
            if self.native_hmmer_preparation_results.applies(context):
                return {**native_empty, **self.native_hmmer_preparation_results.facts(context)}
        if self.native_infernal_preparation_results is not None:
            from gene_annotation_episode.episodic_workflow.root.library.infernal_preparation_result_views import preparation_fact_sources
            native_empty.update({source: [] for source in preparation_fact_sources()})
            if self.native_infernal_preparation_results.applies(context):
                return {**native_empty, **self.native_infernal_preparation_results.facts(context)}
        if self.native_blast_results is not None:
            from gene_annotation_episode.episodic_workflow.root.library.blast_pairwise_result_views import FAMILY_SOURCES as BLAST_SOURCES
            native_empty.update({source: [] for source in BLAST_SOURCES.values()})
            native_empty['execution_blast_pairwise_result_refs'] = []
            if self.native_blast_results.applies(context):
                return {**native_empty, **self.native_blast_results.facts(context)}
        if self.native_infernal_results is not None:
            from gene_annotation_episode.episodic_workflow.root.library.infernal_native_result_views import FAMILY_SOURCES as INFERNAL_SOURCES
            native_empty.update({source: [] for source in INFERNAL_SOURCES.values()})
            native_empty['execution_infernal_result_refs'] = []
            if self.native_infernal_results.applies(context):
                return {**native_empty, **self.native_infernal_results.facts(context)}
        if self.native_hmmer_results.applies(context):
            return {**native_empty, **self.native_hmmer_results.facts(context)}
        extra = {}
        with self.store.read_snapshot():
            read = self.job_progress_provider.targets._handoff_reader()
            _, handoffs, results = self._received(context, _handoff_read=read)
            completed = any((read(reference, context.scope)[1] for reference in handoffs))
            return {**native_empty, **extra, 'execution_handoff_refs': sorted(handoffs), **({'bvbrc_appservice_support_refs': self.api_execution.appservice.received_support_refs(context)} if self._has_appservice() else {}), 'execution_blast_hsps': [], 'execution_result_refs': sorted((ref for ref, body in results.items() if body['windows'])), 'execution_file_source_refs': sorted({row['source_ref'] for body in results.values() for row in body.get('captured_files', []) if row['source_ref'] is not None}), 'execution_file_capture_outcomes': self.local_file_sources.outcomes_for_context(context) if self.local_file_sources.applies(context) else [], 'execution_result_origin': deepcopy(NATIVE_RESULT_ORIGIN) if any((body['windows'] for body in results.values())) else None, 'execution_completed': completed}

