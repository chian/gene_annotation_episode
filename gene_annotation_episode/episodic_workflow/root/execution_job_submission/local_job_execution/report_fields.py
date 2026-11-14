"""Private report_fields responsibility with original returned-value semantics."""
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


class LocalExecutionReportFields:
    def fact_sources(self, role):
        if role != 'launch_local':
            raise ValueError('fixed_execution_role_required')
        from .resource_to_parent import LocalToParent
        from gene_annotation_episode.episodic_workflow.root.library.hmmer_native_result_views import native_hmmer_fact_sources
        values = native_hmmer_fact_sources()
        self.native_flux_balance_results is not None and False
        from gene_annotation_episode.episodic_workflow.root.library.sequence_masking_result_views import masking_fact_sources
        values.update(masking_fact_sources())
        from gene_annotation_episode.episodic_workflow.root.library.blast_utility_result_views import blast_utility_fact_sources
        values.update(blast_utility_fact_sources())
        self._has_uniprot() and False
        self._has_enrichr() and False
        self._has_addgene() and False
        self.native_expression_nmf_results is not None and False
        self.atac_results is not None and False
        self.native_chromatin_interaction_results is not None and False
        self.native_genomic_overlap_results is not None and False
        self.rna_structure_comparison_results is not None and False
        if self.native_rna_structure_results is not None:
            from gene_annotation_episode.episodic_workflow.root.library.rna_structure_result_views import rna_structure_fact_sources
            values.update(rna_structure_fact_sources())
        if self.native_blast_standard_database_results is not None:
            from gene_annotation_episode.episodic_workflow.root.library.native_blast_standard_database_result_views import standard_blast_database_fact_sources
            values.update(standard_blast_database_fact_sources())
        if self.native_blast_database_results is not None:
            from gene_annotation_episode.episodic_workflow.root.library.native_blast_database_result_views import native_blast_database_fact_sources
            values.update(native_blast_database_fact_sources())
        if self.native_hmmer_preparation_results is not None:
            from gene_annotation_episode.episodic_workflow.root.library.hmmer_preparation_result_views import preparation_fact_sources
            values.update(preparation_fact_sources())
        if self.native_infernal_preparation_results is not None:
            from gene_annotation_episode.episodic_workflow.root.library.infernal_preparation_result_views import preparation_fact_sources
            values.update(preparation_fact_sources())
        self._has_rfam() and False
        if self.native_blast_results is not None:
            from gene_annotation_episode.episodic_workflow.root.library.blast_pairwise_result_views import native_blast_fact_sources
            values.update(native_blast_fact_sources())
            values['execution_blast_pairwise_result_refs'] = self._blast_reference_source()
        if self.native_infernal_results is not None:
            from gene_annotation_episode.episodic_workflow.root.library.infernal_native_result_views import native_infernal_fact_sources
            values.update(native_infernal_fact_sources())
            values['execution_infernal_result_refs'] = self._infernal_reference_source()
        if self._has_appservice():
            values.update(self._appservice_sources())
        from gene_annotation_episode.episodic_workflow.root.library.bvbrc_data_views import bvbrc_data_fact_sources
        values.update(bvbrc_data_fact_sources())
        if self.api_execution is not None and any((service.service == 'bvbrc_minhash' for service in self.api_execution.services.values())):
            from gene_annotation_episode.episodic_workflow.root.library.bvbrc_minhash_views import minhash_fact_sources
            values.update(minhash_fact_sources())
        values.update(LocalToParent.fact_sources(None, 'launch_local'))
        for key, namespace, meaning in (('execution_handoff_refs', 'execution_handoff', 'Qualified original handoff sources actually available to this episode, including authenticated original failed native database or RNA attempts for partial-output acquisition; failed attempts do not establish a successful native endpoint.'), ('execution_result_refs', 'execution_result', 'Qualified actual requested result acquisitions available to this episode. Generic native windows retain current-filesystem observations. Explicit BLAST/HMMER/Infernal/RNA producer bundles retain original attempt outputs matched by digest and requested numerical facts. RNA source delivery alone grants no auxiliary artifacts or unrequested rows.')):
            values[key] = {'type': 'array', 'meaning': meaning, 'report_schema': {'type': 'array', 'uniqueItems': True, 'items': {'type': 'string', 'format': 'reference', 'x-reference-namespace': namespace}, 'x-source': key}}
        values['execution_completed'] = {'type': 'boolean', 'meaning': 'Whether this assignment has actual verified endpoint information. Generic native results mean requested current-filesystem acquisition plus independently observed successful exact execution, without a producing-attempt or atomic-version claim. RNA results mean complete requested original-bundle or retained-sheet delivery, including specific unavailable values; this does not assert native success. Yielding alone is false.'}
        from gene_annotation_episode.episodic_workflow.root.library.native_hmmer_acquisition import ORIGIN as hmmer_origin
        from gene_annotation_episode.episodic_workflow.root.native_fluorescence_results import ORIGIN as fluorescence_origin
        origins = [NATIVE_RESULT_ORIGIN, hmmer_origin, fluorescence_origin]
        if self.native_flux_balance_results is not None:
            from gene_annotation_episode.episodic_workflow.root.native_flux_balance_results import ORIGIN as fba_origin
            origins.append(fba_origin)
        if self.native_expression_nmf_results is not None:
            from gene_annotation_episode.episodic_workflow.root.native_expression_nmf_results import ORIGIN as nmf_origin
            origins.append(nmf_origin)
        if self.atac_results is not None:
            from gene_annotation_episode.episodic_workflow.root.native_atac_differential_results import ORIGIN as atac_origin, SAVED_ORIGIN as saved_atac_origin
            origins.extend([atac_origin, saved_atac_origin])
        values['execution_result_origin'] = {'type': ['object', 'null'], 'meaning': 'Actual acquisition semantics of retained results: current-file windows, original producer output, or explicitly received saved numerical data. ATAC records distinguish captured original occurrences from received sheet/table bundles and do not imply native success. No qualified retained data yields null. RNA failed native attempts and saved-sheet recalculations return null even when qualified delivery completes.', 'report_schema': {**obj({key: {'type': 'string', 'enum': list(dict.fromkeys((origin[key] for origin in origins)))} for key in NATIVE_RESULT_ORIGIN}), 'type': ['object', 'null'], 'x-source': 'execution_result_origin'}}
        from gene_annotation_episode.episodic_workflow.root.library.blast_result_views import BLAST_HSP_FACT_SCHEMA
        values['execution_blast_hsps'] = {'type': 'array', 'meaning': 'Optional explicitly requested native measurements for all published HSPs of this acquired result. No automatic ranking, top-N or significance filter. target_coverage is native reference/hit coverage, not original gene-target coverage. HSP/reference records support later scoped reads; selected HSP references can instead be returned through a parent-chosen typed field. No functional assignment or annotation score.', 'report_schema': {**deepcopy(BLAST_HSP_FACT_SCHEMA), 'x-source': 'execution_blast_hsps'}}
        return values

