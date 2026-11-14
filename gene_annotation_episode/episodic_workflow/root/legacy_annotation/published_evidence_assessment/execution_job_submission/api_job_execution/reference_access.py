"""Private reference_access responsibility with original returned-value semantics."""
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


class APIExecutionReferenceAccess:
    def resolve(self, context, reference, namespace):
        if context.role != 'launch_api' or context.run_id != self.run_id:
            raise ValueError('fixed_execution_context_required')
        try:
            fba = self._flux_balance_reference_access(context, reference, namespace)
            if fba is not None:
                return fba
            masking = self._masking_reference_access(context, reference, namespace)
            if masking is not None:
                return masking
            utility = self._utility_reference_access(context, reference, namespace)
            if utility is not None:
                return utility
            if self._has_uniprot():
                resolved = self.api_execution.uniprot_returns.resolve_received(context, reference, namespace)
                if resolved is not None:
                    return resolved
            if self._has_enrichr():
                resolved = self.api_execution.enrichr_returns.resolve_received(context, reference, namespace)
                if resolved is not None:
                    return resolved
            if self._has_addgene():
                resolved = self.api_execution.addgene_returns.resolve_received(context, reference, namespace)
                if resolved is not None:
                    return resolved
            fluorescence = self._fluorescence_reference_access(context, reference, namespace)
            if fluorescence is not None:
                return fluorescence
            nmf = self._expression_nmf_reference_access(context, reference, namespace)
            if nmf is not None:
                return nmf
            atac = self._atac_reference_access(context, reference, namespace)
            if atac is not None:
                return atac
            chromatin = self._chromatin_reference_access(context, reference, namespace)
            if chromatin is not None:
                return chromatin
            overlap = self._genomic_overlap_reference_access(context, reference, namespace)
            if overlap is not None:
                return overlap
            access = self._protein_reference_access(context, reference, namespace)
            if access is not None:
                return access
            if self.rna_structure_comparison_results is not None:
                from gene_annotation_episode.episodic_workflow.root.library.rna_comparison_result_records import IDENTIFIER_NAMESPACES as COMPARISON_NAMESPACES
                if namespace in COMPARISON_NAMESPACES:
                    return self.rna_structure_comparison_returns.resolve_received(context, reference, namespace)
                access = self.rna_structure_comparison_results.retained_reference_access(context, reference, namespace)
                if access is not None:
                    return access
            if self.native_rna_structure_results is not None:
                access = self.native_rna_structure_results.retained_reference_access(context, reference, namespace)
                if access is not None:
                    return access
                from gene_annotation_episode.episodic_workflow.root.library.rna_structure_result_views import IDENTIFIER_NAMESPACES as RNA_NAMESPACES
                if namespace in RNA_NAMESPACES:
                    return self.native_rna_structure_returns.resolve_received(context, reference, namespace)
                if self.native_rna_structure_results.resolve(context, reference, namespace):
                    return True
            if self.native_blast_standard_database_results is not None:
                from gene_annotation_episode.episodic_workflow.root.native_blast_standard_database_results import IDENTIFIER_NAMESPACES as DATABASE_NAMESPACES
                if namespace in DATABASE_NAMESPACES:
                    return self.native_blast_standard_database_returns.resolve_received(context, reference, namespace)
                if self.native_blast_standard_database_results.resolve(context, reference, namespace):
                    return True
            if self.native_blast_database_results is not None:
                from gene_annotation_episode.episodic_workflow.root.native_blast_database_results import IDENTIFIER_NAMESPACES as DATABASE_NAMESPACES
                if namespace in DATABASE_NAMESPACES:
                    return self.native_blast_database_returns.resolve_received(context, reference, namespace)
                if self.native_blast_database_results.resolve(context, reference, namespace):
                    return True
            if self.native_hmmer_preparation_results is not None:
                from gene_annotation_episode.episodic_workflow.root.library.hmmer_preparation_result_views import IDENTIFIER_NAMESPACES as HMMER_PREPARATION_NAMESPACES
                if namespace in HMMER_PREPARATION_NAMESPACES:
                    return self.native_hmmer_preparation_returns.resolve_received(context, reference, namespace)
                if self.native_hmmer_preparation_results.resolve(context, reference, namespace):
                    return True
            if self.native_infernal_preparation_results is not None:
                from gene_annotation_episode.episodic_workflow.root.library.infernal_preparation_result_views import IDENTIFIER_NAMESPACES as PREPARATION_NAMESPACES
                if namespace in PREPARATION_NAMESPACES:
                    return self.native_infernal_preparation_returns.resolve_received(context, reference, namespace)
                if self.native_infernal_preparation_results.resolve(context, reference, namespace):
                    return True
            if self._has_rfam():
                from gene_annotation_episode.episodic_workflow.root.rfam_batch_returns import IDENTIFIER_NAMESPACES as RFAM_NAMESPACES
                if namespace in RFAM_NAMESPACES:
                    return self.api_execution.rfam_returns.resolve_received(context, reference, namespace)
            if self.native_blast_results is not None:
                if namespace in {'native_blast_pairwise_row', 'native_blast_artifact_key', 'native_blast_search_pointer'}:
                    return self.native_blast_returns.resolve_received(context, reference, namespace)
                if self.native_blast_results.resolve(context, reference, namespace):
                    return True
            if self.native_infernal_results is not None:
                from gene_annotation_episode.episodic_workflow.root.library.infernal_native_result_views import IDENTIFIER_NAMESPACES as INFERNAL_NAMESPACES
                if namespace in INFERNAL_NAMESPACES:
                    return self.native_infernal_returns.resolve_received(context, reference, namespace)
                if self.native_infernal_results.resolve(context, reference, namespace):
                    return True
            if self._has_appservice():
                from gene_annotation_episode.episodic_workflow.root.bvbrc_homology_returns import IDENTIFIER_NAMESPACES
                if namespace in IDENTIFIER_NAMESPACES:
                    return self.api_execution.homology_returns.resolve_received(context, reference, namespace)
                from gene_annotation_episode.episodic_workflow.root.bvbrc_phylogeny_returns import IDENTIFIER_NAMESPACES as PHYLOGENY_NAMESPACES
                if namespace in PHYLOGENY_NAMESPACES:
                    return self.api_execution.phylogeny_returns.resolve_received(context, reference, namespace)
                from gene_annotation_episode.episodic_workflow.root.bvbrc_alignment_returns import IDENTIFIER_NAMESPACES as ALIGNMENT_NAMESPACES
                if namespace in ALIGNMENT_NAMESPACES:
                    return self.api_execution.alignment_returns.resolve_received(context, reference, namespace)
                from gene_annotation_episode.episodic_workflow.root.bvbrc_genome_alignment_returns import IDENTIFIER_NAMESPACES as GENOME_ALIGNMENT_NAMESPACES
                if namespace in GENOME_ALIGNMENT_NAMESPACES:
                    return self.api_execution.genome_alignment_returns.resolve_received(context, reference, namespace)
                from gene_annotation_episode.episodic_workflow.root.bvbrc_proteome_returns import IDENTIFIER_NAMESPACES as PROTEOME_NAMESPACES
                if namespace in PROTEOME_NAMESPACES:
                    return self.api_execution.proteome_returns.resolve_received(context, reference, namespace)
                from gene_annotation_episode.episodic_workflow.root.bvbrc_comparative_systems_returns import IDENTIFIER_NAMESPACES as COMPARATIVE_NAMESPACES
                if namespace in COMPARATIVE_NAMESPACES:
                    return self.api_execution.comparative_systems_returns.resolve_received(context, reference, namespace)
                from gene_annotation_episode.bvbrc_fastqutils_returns import IDENTIFIER_NAMESPACES as FASTQUTILS_NAMESPACES
                if namespace in FASTQUTILS_NAMESPACES:
                    return self.api_execution.fastqutils_returns.resolve_received(context, reference, namespace)
                from gene_annotation_episode.episodic_workflow.root.bvbrc_application_returns import IDENTIFIER_NAMESPACES as APPLICATION_NAMESPACES
                if namespace in APPLICATION_NAMESPACES:
                    return self.api_execution.application_returns.resolve_received(context, reference, namespace)
                resolved = self.api_execution.appservice.resolve(context, reference, namespace)
                if resolved is not None:
                    return resolved
            if namespace == 'bvbrc_minhash_genome':
                if self.api_execution is None:
                    return False
                return self.api_execution.minhash.resolve_received(context, reference, namespace)
            from gene_annotation_episode.episodic_workflow.root.library.bvbrc_data_views import IDENTIFIER_NAMESPACES
            if namespace in IDENTIFIER_NAMESPACES:
                return self.api_execution is not None and self.api_execution.bvbrc_data.resolve(context, reference, namespace)
            if namespace in {'execution_handle', 'execution'}:
                from gene_annotation_episode.episodic_workflow.root.episode_bindings import reference_in_context
                return bool(self.services is not None and reference_in_context(self.services, context, reference, namespace))
            if self.native_hmmer_results.resolve(context, reference, namespace):
                return True
            source = self.store.get(reference)
            if source.get('provider') == LOCAL_FILE_SOURCE_PROVIDER:
                return namespace in {None, 'source'} and self.local_file_sources.read_source(reference, context.scope) is not None
            if source.get('provider') == RESULT_PROVIDER:
                if source.get('version') in {'native_blast_utility_bundle_v1', 'native_blast_masking_bundle_v1', 'native_hmmer_bundle_v1', 'native_blast_bundle_v1', 'native_blast_database_bundle_v1', 'native_blast_standard_database_bundle_v1', 'native_infernal_bundle_v1', 'native_infernal_preparation_bundle_v1', 'native_hmmer_preparation_bundle_v1', 'native_protein_structure_bundle_v1', 'native_rna_structure_bundle_v1'}:
                    return False
                if namespace not in {None, 'source', 'execution_result'}:
                    return False
                body = self._read_result(reference, context.scope)
                return bool(body['windows']) if namespace == 'execution_result' else True
            if namespace in {None, 'source', 'execution_handoff'}:
                try:
                    target = self.job_progress_provider.targets.read_target(reference, context.scope)
                    return namespace != 'execution_handoff' or self.job_progress_provider.targets.returnable_handoff(target)
                except ValueError:
                    if namespace == 'execution_handoff':
                        return False
            if PracticalReceiptInformation(self.store, self.run_id).resolve(context, reference, namespace):
                return True
            if self.api_execution is not None and self.api_execution.resolve(context, reference, namespace):
                return True
            if self.native_hmmer_preparation_results is not None:
                access = self.native_hmmer_preparation_results.retained_reference_access(context, reference, namespace)
                if access is not None:
                    return access
            if self.native_infernal_preparation_results is not None:
                access = self.native_infernal_preparation_results.retained_reference_access(context, reference, namespace)
                if access is not None:
                    return access
            if source.get('provider') == 'episode.practical_receipt' or (self.api_execution is not None and self.api_execution.is_handoff_source(reference)):
                return False
            if self.services is not None:
                from gene_annotation_episode.episodic_workflow.root.episode_bindings import reference_in_context
                return bool(reference_in_context(self.services, context, reference, namespace))
            kind = source['record_type']
            return bool(self.store.reference_subset([reference], plain(context.scope)) and (namespace in {None, kind} or (namespace == 'subject' and kind in {'input', 'feature', 'product', 'read_subject'})))
        except (ValueError, KeyError, OSError):
            return False

