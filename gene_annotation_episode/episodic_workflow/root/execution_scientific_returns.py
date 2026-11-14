"""Complete original execution scientific returns responsibility."""
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

class ExecutionScientificReturns:
    def _forwards_bvbrc_reports(self, role):
        return role in {'annotation', 'scientific_process'} and self.api_execution is not None and any((service.service == 'bvbrc_data' for service in self.api_execution.services.values()))

    def _forwards_minhash_reports(self, role):
        return role in {'annotation', 'scientific_process'} and self.api_execution is not None and any((service.service == 'bvbrc_minhash' for service in self.api_execution.services.values()))

    def received_report_sources(self, role):
        from gene_annotation_episode.episodic_workflow.root.execution_result_acquisition.report_fields import ResultAcquisitionReportFields
        result = {}
        if role in {'annotation', 'scientific_process'}:
            for source in ('execution_file_source_refs', 'execution_file_capture_outcomes'):
                definition = ResultAcquisitionReportFields.fact_sources(self, 'results').get(source)
                if definition is not None:
                    result[source] = deepcopy(definition)
        if self.native_flux_balance_returns is not None and role in {'annotation', 'scientific_process'}:
            from gene_annotation_episode.episodic_workflow.root.library.flux_balance_return_views import fba_fact_sources
            sources = fba_fact_sources()
            if self.native_flux_balance_returns.ordinary_backend is None:
                sources = {name: sources[name] for name in ('flux_balance_measurements', 'flux_balance_saved_sheets', 'flux_balance_failures')}
            result.update(sources)
        if role in {'annotation', 'scientific_process'}:
            from gene_annotation_episode.episodic_workflow.root.library.sequence_masking_result_views import masking_fact_sources
            result.update(masking_fact_sources())
            from gene_annotation_episode.episodic_workflow.root.library.blast_utility_result_views import blast_utility_fact_sources
            result.update(blast_utility_fact_sources())
        if self._has_uniprot() and role in {'annotation', 'scientific_process'}:
            from gene_annotation_episode.episodic_workflow.root.library.uniprot_return_contracts import uniprot_fact_sources
            result.update(uniprot_fact_sources())
        if self._has_enrichr() and role in {'annotation', 'scientific_process'}:
            from gene_annotation_episode.episodic_workflow.root.library.enrichr_contracts import enrichr_fact_sources
            result.update(enrichr_fact_sources())
        if self._has_addgene() and role in {'annotation', 'scientific_process'}:
            from gene_annotation_episode.addgene_sequence_returns import addgene_sequence_fact_sources
            result.update(addgene_sequence_fact_sources())
        if role in {'annotation', 'scientific_process'}:
            from gene_annotation_episode.episodic_workflow.root.library.fluorescence_return_views import fluorescence_fact_sources
            result.update(fluorescence_fact_sources())
        if self.native_expression_nmf_returns is not None and role in {'annotation', 'scientific_process'}:
            from gene_annotation_episode.episodic_workflow.root.library.expression_nmf_return_views import expression_nmf_fact_sources
            result.update(expression_nmf_fact_sources())
        if self.atac_returns is not None and role in {'annotation', 'scientific_process'}:
            from gene_annotation_episode.episodic_workflow.root.library.atac_differential_return_views import atac_fact_sources
            result.update(atac_fact_sources())
        if self.native_chromatin_interaction_returns is not None and role in {'annotation', 'scientific_process'}:
            from gene_annotation_episode.episodic_workflow.root.library.chromatin_interaction_return_views import chromatin_fact_sources
            result.update(chromatin_fact_sources())
        if self.native_genomic_overlap_returns is not None and role in {'annotation', 'scientific_process'}:
            from gene_annotation_episode.episodic_workflow.root.library.genomic_overlap_return_views import genomic_overlap_fact_sources
            result.update(genomic_overlap_fact_sources())
        if role in {'annotation', 'scientific_process'}:
            from gene_annotation_episode.episodic_workflow.root.library.protein_structure_result_views import protein_structure_fact_sources
            result.update(protein_structure_fact_sources())
        if self.rna_structure_comparison_returns is not None and role in {'annotation', 'scientific_process'}:
            from gene_annotation_episode.episodic_workflow.root.library.rna_structure_comparison_views import rna_comparison_fact_sources
            result.update(rna_comparison_fact_sources())
        if self.native_rna_structure_returns is not None and role in {'annotation', 'scientific_process'}:
            from gene_annotation_episode.episodic_workflow.root.library.rna_structure_result_views import rna_structure_fact_sources
            result.update(rna_structure_fact_sources())
        if self.native_blast_standard_database_returns is not None and role in {'annotation', 'scientific_process'}:
            from gene_annotation_episode.episodic_workflow.root.library.native_blast_standard_database_result_views import standard_blast_database_fact_sources
            result.update(standard_blast_database_fact_sources())
        if self.native_blast_database_returns is not None and role in {'annotation', 'scientific_process'}:
            from gene_annotation_episode.episodic_workflow.root.library.native_blast_database_result_views import native_blast_database_fact_sources
            result.update(native_blast_database_fact_sources())
        if self.native_hmmer_preparation_returns is not None and role in {'annotation', 'scientific_process'}:
            from gene_annotation_episode.episodic_workflow.root.library.hmmer_preparation_result_views import preparation_fact_sources
            result.update(preparation_fact_sources())
        if self.native_infernal_preparation_returns is not None and role in {'annotation', 'scientific_process'}:
            from gene_annotation_episode.episodic_workflow.root.library.infernal_preparation_result_views import preparation_fact_sources
            result.update(preparation_fact_sources())
        if self._has_rfam() and role in {'annotation', 'scientific_process'}:
            from gene_annotation_episode.episodic_workflow.root.rfam_batch_returns import rfam_fact_sources
            result.update(rfam_fact_sources())
        if self.native_blast_returns is not None and role in {'annotation', 'scientific_process'}:
            from gene_annotation_episode.episodic_workflow.root.library.blast_pairwise_result_views import native_blast_fact_sources
            result.update(native_blast_fact_sources())
            result['execution_blast_pairwise_result_refs'] = self._blast_reference_source()
        if self.native_infernal_returns is not None and role in {'annotation', 'scientific_process'}:
            from gene_annotation_episode.episodic_workflow.root.library.infernal_native_result_views import native_infernal_fact_sources
            result.update(native_infernal_fact_sources())
            result['execution_infernal_result_refs'] = self._infernal_reference_source()
        if self._forwards_bvbrc_reports(role):
            from gene_annotation_episode.episodic_workflow.root.library.bvbrc_data_views import bvbrc_data_fact_sources
            result.update(bvbrc_data_fact_sources())
        if self._forwards_minhash_reports(role):
            from gene_annotation_episode.episodic_workflow.root.library.bvbrc_minhash_views import minhash_fact_sources
            result.update(minhash_fact_sources())
        if self._has_appservice() and role in {'annotation', 'scientific_process'}:
            result.update(self._appservice_sources())
        return result

    def received_report_facts(self, context):
        schema = (plain(context.request).get('report_contract') or {}).get('measurements', {}).get('schema', {})
        result = {}
        if context.role in {'annotation', 'scientific_process'}:
            requested = {node.get('x-source') for node in schema.get('properties', {}).values()}
            if 'execution_file_source_refs' in requested:
                result['execution_file_source_refs'] = self.local_file_sources.received_sources(context)
            if 'execution_file_capture_outcomes' in requested:
                result['execution_file_capture_outcomes'] = self.local_file_sources.received_outcomes(context)
        if self.native_flux_balance_returns is not None and context.role in {'annotation', 'scientific_process'} and (schema.get('properties') is not None):
            result.update(self.native_flux_balance_returns.facts_for_closure(context, schema))
        if context.role in {'annotation', 'scientific_process'}:
            result.update(self.native_blast_masking_returns.received_facts(context, schema))
            result.update(self.native_blast_utility_returns.received_facts(context, schema))
        if self._has_uniprot() and context.role in {'annotation', 'scientific_process'}:
            result.update(self.api_execution.uniprot_returns.facts_for_closure(context, schema))
        if self._has_enrichr() and context.role in {'annotation', 'scientific_process'}:
            result.update(self.api_execution.enrichr_returns.facts_for_closure(context, schema))
        if self._has_addgene() and context.role in {'annotation', 'scientific_process'}:
            result.update(self.api_execution.addgene_returns.received_facts(context, schema))
        if context.role in {'annotation', 'scientific_process'} and schema.get('properties') is not None:
            result.update(self.native_fluorescence_returns.facts_for_closure(context, schema))
        if self.native_expression_nmf_returns is not None and context.role in {'annotation', 'scientific_process'} and (schema.get('properties') is not None):
            result.update(self.native_expression_nmf_returns.facts_for_closure(context, schema))
        if self.atac_returns is not None and context.role in {'annotation', 'scientific_process'} and (schema.get('properties') is not None):
            result.update(self.atac_returns.facts_for_closure(context, schema))
        if self.native_chromatin_interaction_returns is not None and context.role in {'annotation', 'scientific_process'} and (schema.get('properties') is not None):
            result.update(self.native_chromatin_interaction_returns.facts_for_closure(context, schema))
        if self.native_genomic_overlap_returns is not None and context.role in {'annotation', 'scientific_process'} and (schema.get('properties') is not None):
            result.update(self.native_genomic_overlap_returns.facts_for_closure(context, schema))
        if context.role in {'annotation', 'scientific_process'}:
            result.update(self.native_protein_structure_returns.received_facts(context, schema))
        if self.rna_structure_comparison_returns is not None and context.role in {'annotation', 'scientific_process'}:
            result.update(self.rna_structure_comparison_returns.received_facts(context, schema))
        if self.native_rna_structure_returns is not None and context.role in {'annotation', 'scientific_process'}:
            result.update(self.native_rna_structure_returns.received_facts(context, schema))
        if self.native_blast_standard_database_returns is not None and context.role in {'annotation', 'scientific_process'}:
            result.update(self.native_blast_standard_database_returns.received_facts(context, schema))
        if self.native_blast_database_returns is not None and context.role in {'annotation', 'scientific_process'}:
            result.update(self.native_blast_database_returns.received_facts(context, schema))
        if self.native_hmmer_preparation_returns is not None and context.role in {'annotation', 'scientific_process'}:
            result.update(self.native_hmmer_preparation_returns.received_facts(context, schema))
        if self.native_infernal_preparation_returns is not None and context.role in {'annotation', 'scientific_process'}:
            result.update(self.native_infernal_preparation_returns.received_facts(context, schema))
        if self._has_rfam() and context.role in {'annotation', 'scientific_process'}:
            result.update(self.api_execution.rfam_returns.received_facts(context, schema))
        if self.native_blast_returns is not None and context.role in {'annotation', 'scientific_process'}:
            result.update(self.native_blast_returns.received_facts(context, schema))
        if self.native_infernal_returns is not None and context.role in {'annotation', 'scientific_process'}:
            result.update(self.native_infernal_returns.received_facts(context, schema))
        if self._forwards_bvbrc_reports(context.role):
            result.update(self.api_execution.bvbrc_data.received_facts(context, schema))
        if self._forwards_minhash_reports(context.role):
            result.update(self.api_execution.minhash.received_facts(context, schema))
        if self._has_appservice() and context.role in {'annotation', 'scientific_process'}:
            if any((node.get('x-source') == 'bvbrc_appservice_support_refs' for node in schema.get('properties', {}).values())):
                result['bvbrc_appservice_support_refs'] = self.api_execution.appservice.received_support_refs(context)
            result.update(self.api_execution.homology_returns.received_facts(context, schema))
            result.update(self.api_execution.phylogeny_returns.received_facts(context, schema))
            result.update(self.api_execution.alignment_returns.received_facts(context, schema))
            result.update(self.api_execution.genome_alignment_returns.received_facts(context, schema))
            proteome = self.api_execution.proteome_returns.received_facts(context, schema)
            if set(result).intersection(proteome):
                raise ValueError('received_report_fact_conflict')
            result.update(proteome)
            comparative = self.api_execution.comparative_systems_returns.received_facts(context, schema)
            if set(result).intersection(comparative):
                raise ValueError('received_report_fact_conflict')
            result.update(comparative)
            fastqutils = self.api_execution.fastqutils_returns.received_facts(context, schema)
            if set(result).intersection(fastqutils):
                raise ValueError('received_report_fact_conflict')
            result.update(fastqutils)
            application = self.api_execution.application_returns.received_facts(context, schema)
            if set(result).intersection(application):
                raise ValueError('received_report_fact_conflict')
            result.update(application)
        return result

    def received_report_closure_facts(self, context):
        """Private return bindings, called only by the registry at episode closure."""
        if context.role not in {'annotation', 'scientific_process'}:
            return {}
        schema = (plain(context.request).get('report_contract') or {}).get('measurements', {}).get('schema', {})
        result = {}
        if self._has_addgene():
            from gene_annotation_episode.addgene_sequence_returns import CLOSURE_PREFIX
            frozen = self.api_execution.addgene_returns.facts_for_closure(context, schema)
            if CLOSURE_PREFIX in frozen:
                result[CLOSURE_PREFIX] = frozen[CLOSURE_PREFIX]
        if self.native_flux_balance_returns is not None and schema.get('properties') is not None:
            result.update(self.native_flux_balance_returns.ordinary_closure_facts(context, schema))
        return result

    def resolve_received_reference(self, context, reference, namespace):
        captured = self.local_file_sources.reference_access(context, reference, namespace)
        if captured is not None:
            return captured
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
            resolved = self.api_execution.uniprot_returns.resolve_own(context, reference, namespace) if context.role == 'results' else self.api_execution.uniprot_returns.resolve_received(context, reference, namespace)
            if resolved is not None:
                return resolved
        if self._has_enrichr():
            resolved = self.api_execution.enrichr_returns.resolve_own(context, reference, namespace) if context.role == 'results' else self.api_execution.enrichr_returns.resolve_received(context, reference, namespace)
            if resolved is not None:
                return resolved
        if self._has_addgene():
            resolved = self.api_execution.addgene_returns.resolve_own(context, reference, namespace) if context.role == 'results' else self.api_execution.addgene_returns.resolve_received(context, reference, namespace)
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
                return self.rna_structure_comparison_results.resolve(context, reference, namespace) if context.role == 'results' else self.rna_structure_comparison_returns.resolve_received(context, reference, namespace)
            access = self.rna_structure_comparison_results.retained_reference_access(context, reference, namespace)
            if access is not None:
                return access
        if self.native_rna_structure_results is not None:
            access = self.native_rna_structure_results.retained_reference_access(context, reference, namespace)
            if access is not None:
                return access
            if context.role in {'annotation', 'scientific_process'}:
                resolved = self.native_rna_structure_returns.resolve_received(context, reference, namespace)
                if resolved is not None:
                    return resolved
        if self.native_blast_standard_database_returns is not None and context.role in {'annotation', 'scientific_process'}:
            resolved = self.native_blast_standard_database_returns.resolve_received(context, reference, namespace)
            if resolved is not None:
                return resolved
        if self.native_blast_database_returns is not None and context.role in {'annotation', 'scientific_process'}:
            resolved = self.native_blast_database_returns.resolve_received(context, reference, namespace)
            if resolved is not None:
                return resolved
        if self.native_hmmer_preparation_returns is not None and context.role in {'annotation', 'scientific_process'}:
            resolved = self.native_hmmer_preparation_returns.resolve_received(context, reference, namespace)
            if resolved is not None:
                return resolved
        if self.native_infernal_preparation_returns is not None and context.role in {'annotation', 'scientific_process'}:
            resolved = self.native_infernal_preparation_returns.resolve_received(context, reference, namespace)
            if resolved is not None:
                return resolved
        if self._has_rfam() and context.role in {'annotation', 'scientific_process'}:
            resolved = self.api_execution.rfam_returns.resolve_received(context, reference, namespace)
            if resolved is not None:
                return resolved
        if self.native_blast_returns is not None and context.role in {'annotation', 'scientific_process'}:
            resolved = self.native_blast_returns.resolve_received(context, reference, namespace)
            if resolved is not None:
                return resolved
        if self.native_infernal_returns is not None and context.role in {'annotation', 'scientific_process'}:
            resolved = self.native_infernal_returns.resolve_received(context, reference, namespace)
            if resolved is not None:
                return resolved
        if self._has_appservice():
            from gene_annotation_episode.episodic_workflow.root.bvbrc_homology_returns import IDENTIFIER_NAMESPACES
            if namespace in IDENTIFIER_NAMESPACES:
                if context.role == 'results':
                    return None
                return self.api_execution.homology_returns.resolve_received(context, reference, namespace)
            from gene_annotation_episode.episodic_workflow.root.bvbrc_phylogeny_returns import IDENTIFIER_NAMESPACES as PHYLOGENY_NAMESPACES
            if namespace in PHYLOGENY_NAMESPACES:
                if context.role == 'results':
                    return None
                return self.api_execution.phylogeny_returns.resolve_received(context, reference, namespace)
            from gene_annotation_episode.episodic_workflow.root.bvbrc_alignment_returns import IDENTIFIER_NAMESPACES as ALIGNMENT_NAMESPACES
            if namespace in ALIGNMENT_NAMESPACES:
                if context.role == 'results':
                    return None
                return self.api_execution.alignment_returns.resolve_received(context, reference, namespace)
            from gene_annotation_episode.episodic_workflow.root.bvbrc_genome_alignment_returns import IDENTIFIER_NAMESPACES as GENOME_ALIGNMENT_NAMESPACES
            if namespace in GENOME_ALIGNMENT_NAMESPACES:
                if context.role == 'results':
                    return None
                return self.api_execution.genome_alignment_returns.resolve_received(context, reference, namespace)
            from gene_annotation_episode.episodic_workflow.root.bvbrc_proteome_returns import IDENTIFIER_NAMESPACES as PROTEOME_NAMESPACES
            if namespace in PROTEOME_NAMESPACES:
                if context.role == 'results':
                    return None
                return self.api_execution.proteome_returns.resolve_received(context, reference, namespace)
            from gene_annotation_episode.episodic_workflow.root.bvbrc_comparative_systems_returns import IDENTIFIER_NAMESPACES as COMPARATIVE_NAMESPACES
            if namespace in COMPARATIVE_NAMESPACES:
                if context.role == 'results':
                    return None
                return self.api_execution.comparative_systems_returns.resolve_received(context, reference, namespace)
            from gene_annotation_episode.bvbrc_fastqutils_returns import IDENTIFIER_NAMESPACES as FASTQUTILS_NAMESPACES
            if namespace in FASTQUTILS_NAMESPACES:
                if context.role == 'results':
                    return None
                return self.api_execution.fastqutils_returns.resolve_received(context, reference, namespace)
            from gene_annotation_episode.episodic_workflow.root.bvbrc_application_returns import IDENTIFIER_NAMESPACES as APPLICATION_NAMESPACES
            if namespace in APPLICATION_NAMESPACES:
                if context.role == 'results':
                    return None
                return self.api_execution.application_returns.resolve_received(context, reference, namespace)
            resolved = self.api_execution.appservice.resolve(context, reference, namespace)
            if resolved is not None:
                return resolved
        if self._forwards_bvbrc_reports(context.role):
            resolved = self.api_execution.bvbrc_data.resolve_received(context, reference, namespace)
            if resolved is not None:
                return resolved
        if self._forwards_minhash_reports(context.role):
            resolved = self.api_execution.minhash.resolve_received(context, reference, namespace)
            if resolved is not None:
                return resolved
        for results in (self.native_hmmer_preparation_results, self.native_infernal_preparation_results):
            if results is not None:
                resolved = results.retained_reference_access(context, reference, namespace)
                if resolved is not None:
                    return resolved
        return None

    def validate_received_report(self, context, form, schema):
        self.local_file_sources.validate_received_report(context, form, schema)
        if self.native_flux_balance_returns is not None:
            self.native_flux_balance_returns.validate_received_report(context, form, schema)
        self.native_blast_masking_returns.validate_received_report(context, form, schema)
        self.native_blast_utility_returns.validate_received_report(context, form, schema)
        if self._has_uniprot():
            self.api_execution.uniprot_returns.validate_received_report(context, form, schema)
        if self._has_enrichr():
            self.api_execution.enrichr_returns.validate_received_report(context, form, schema)
        if self._has_addgene():
            self.api_execution.addgene_returns.validate_received_report(context, form, schema)
        if plain(schema).get('properties') is not None:
            self.native_fluorescence_returns.validate_received_report(context, form, schema)
        if self.native_expression_nmf_returns is not None:
            self.native_expression_nmf_returns.validate_received_report(context, form, schema)
        if self.atac_returns is not None:
            self.atac_returns.validate_received_report(context, form, schema)
        if self.native_chromatin_interaction_returns is not None:
            self.native_chromatin_interaction_returns.validate_received_report(context, form, schema)
        if self.native_genomic_overlap_returns is not None:
            self.native_genomic_overlap_returns.validate_received_report(context, form, schema)
        self.native_protein_structure_returns.validate_received_report(context, form, schema)
        if self.rna_structure_comparison_returns is not None:
            self.rna_structure_comparison_returns.validate_received_report(context, form, schema)
        if self.native_rna_structure_returns is not None:
            self.native_rna_structure_returns.validate_received_report(context, form, schema)
        if self.native_blast_standard_database_returns is not None:
            self.native_blast_standard_database_returns.validate_received_report(context, form, schema)
        if self.native_blast_database_returns is not None:
            self.native_blast_database_returns.validate_received_report(context, form, schema)
        if self.native_hmmer_preparation_returns is not None:
            self.native_hmmer_preparation_returns.validate_received_report(context, form, schema)
        if self.native_infernal_preparation_returns is not None:
            self.native_infernal_preparation_returns.validate_received_report(context, form, schema)
        if self._has_rfam():
            self.api_execution.rfam_returns.validate_received_report(context, form, schema)
        if self.native_blast_returns is not None:
            self.native_blast_returns.validate_received_report(context, form, schema)
        if self.native_infernal_returns is not None:
            self.native_infernal_returns.validate_received_report(context, form, schema)
        if self._has_appservice():
            self.api_execution.appservice.validate_received_report(context, form, schema)
            self.api_execution.homology_returns.validate_received_report(context, form, schema)
            self.api_execution.phylogeny_returns.validate_received_report(context, form, schema)
            self.api_execution.alignment_returns.validate_received_report(context, form, schema)
            self.api_execution.genome_alignment_returns.validate_received_report(context, form, schema)
            self.api_execution.proteome_returns.validate_received_report(context, form, schema)
            self.api_execution.comparative_systems_returns.validate_received_report(context, form, schema)
            self.api_execution.fastqutils_returns.validate_received_report(context, form, schema)
            self.api_execution.application_returns.validate_received_report(context, form, schema)
        if self._forwards_bvbrc_reports(context.role):
            self.api_execution.bvbrc_data.validate_received_report(context, form, schema)
        if self._forwards_minhash_reports(context.role):
            self.api_execution.minhash.validate_received_report(context, form, schema)

    def _has_appservice(self):
        return self.api_execution is not None and any((service.service == 'bvbrc_appservice' for service in self.api_execution.services.values()))

    def _has_rfam(self):
        return self.api_execution is not None and any((service.service == 'rfam_batch' for service in self.api_execution.services.values()))

    def _has_uniprot(self):
        return self.api_execution is not None and any((service.service == 'uniprot' for service in self.api_execution.services.values()))

    def _has_enrichr(self):
        return self.api_execution is not None and any((service.service == 'enrichr' for service in self.api_execution.services.values()))

    def _has_addgene(self):
        return self.api_execution is not None and any((service.service == 'sequence_support' for service in self.api_execution.services.values()))

    @staticmethod
    def _infernal_reference_source():
        return {'type': 'array', 'meaning': 'Infernal source, observation and model references actually returned through this episode boundary. These references alone do not deliver unrequested numerical rows.', 'report_schema': {'type': 'array', 'uniqueItems': True, 'items': {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'execution_result'}, 'x-source': 'execution_infernal_result_refs'}}

    @staticmethod
    def _appservice_sources():
        from gene_annotation_episode.episodic_workflow.root.bvbrc_homology_returns import homology_fact_sources
        from gene_annotation_episode.episodic_workflow.root.bvbrc_phylogeny_returns import phylogeny_fact_sources
        from gene_annotation_episode.episodic_workflow.root.bvbrc_alignment_returns import alignment_fact_sources
        from gene_annotation_episode.episodic_workflow.root.bvbrc_genome_alignment_returns import genome_alignment_fact_sources
        from gene_annotation_episode.episodic_workflow.root.bvbrc_proteome_returns import proteome_fact_sources
        from gene_annotation_episode.episodic_workflow.root.bvbrc_comparative_systems_returns import comparative_systems_fact_sources
        from gene_annotation_episode.episodic_workflow.root.bvbrc_fastqutils_returns import fastqutils_fact_sources
        from gene_annotation_episode.episodic_workflow.root.bvbrc_application_returns import application_fact_sources
        return {**homology_fact_sources(), **phylogeny_fact_sources(), **alignment_fact_sources(), **genome_alignment_fact_sources(), **proteome_fact_sources(), **comparative_systems_fact_sources(), **fastqutils_fact_sources(), **application_fact_sources(), 'bvbrc_appservice_support_refs': {'type': 'array', 'meaning': 'Actually received AppService preparation, Workspace, upload or observation receipts; these are not scientific result acquisitions.', 'report_schema': {'type': 'array', 'uniqueItems': True, 'items': {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'bvbrc_appservice_support'}, 'x-source': 'bvbrc_appservice_support_refs'}}}

    def received_form_references(self, context, form, schema, operation_key):
        from gene_annotation_episode.episodic_workflow.root.library.hmmer_native_result_views import FAMILY_SOURCES
        references = []
        native_references = set()
        references.extend(self.local_file_sources.admit_return(context, form, schema, operation_key))
        if self.native_flux_balance_returns is not None:
            references.extend(self.native_flux_balance_returns.record_admission(context, form, schema, operation_key))
        if self._has_uniprot():
            references.extend(self.api_execution.uniprot_returns.record_admission(context, form, schema, operation_key))
        if self._has_enrichr():
            admitted = self.api_execution.enrichr_returns.record_admission(context, form, schema, operation_key)
            references.extend(admitted)
            native_references.update(admitted)
        if self._has_addgene():
            admitted = self.api_execution.addgene_returns.record_admission(context, form, schema, operation_key)
            references.extend(admitted)
            native_references.update(admitted)
        if plain(schema).get('properties') is not None:
            references.extend(self.native_fluorescence_returns.record_admission(context, form, schema, operation_key))
        if self.native_expression_nmf_returns is not None:
            references.extend(self.native_expression_nmf_returns.record_admission(context, form, schema, operation_key))
        if self.atac_returns is not None:
            references.extend(self.atac_returns.record_admission(context, form, schema, operation_key))
        if self.native_chromatin_interaction_returns is not None:
            references.extend(self.native_chromatin_interaction_returns.record_admission(context, form, schema, operation_key))
        if self.native_genomic_overlap_returns is not None:
            references.extend(self.native_genomic_overlap_returns.record_admission(context, form, schema, operation_key))
        if self.rna_structure_comparison_returns is not None:
            references.extend(self.rna_structure_comparison_returns.record_admission(context, form, schema, operation_key))
        if self._has_rfam():
            references.extend(self.api_execution.rfam_returns.record_admission(context, form, schema, operation_key))
        admitted = self.native_blast_masking_returns.record_admission(context, form, schema, operation_key)
        native_references.update(admitted)
        references.extend(admitted)
        admitted = self.native_blast_utility_returns.record_admission(context, form, schema, operation_key)
        native_references.update(admitted)
        references.extend(admitted)
        admitted = self.native_protein_structure_returns.record_admission(context, form, schema, operation_key)
        native_references.update(admitted)
        references.extend(admitted)
        if self.native_rna_structure_returns is not None:
            admitted = self.native_rna_structure_returns.record_admission(context, form, schema, operation_key)
            native_references.update(admitted)
            references.extend(admitted)
        if self.native_blast_standard_database_returns is not None:
            admitted = self.native_blast_standard_database_returns.record_admission(context, form, schema, operation_key)
            native_references.update(admitted)
            references.extend(admitted)
        if self.native_blast_database_returns is not None:
            admitted = self.native_blast_database_returns.record_admission(context, form, schema, operation_key)
            native_references.update(admitted)
            references.extend(admitted)
        if self.native_hmmer_preparation_returns is not None:
            admitted = self.native_hmmer_preparation_returns.record_admission(context, form, schema, operation_key)
            native_references.update(admitted)
            references.extend(admitted)
        if self.native_infernal_preparation_returns is not None:
            admitted = self.native_infernal_preparation_returns.record_admission(context, form, schema, operation_key)
            native_references.update(admitted)
            references.extend(admitted)
        if self.native_blast_returns is not None:
            admitted = self.native_blast_returns.record_admission(context, form, schema, operation_key)
            native_references.update(admitted)
            references.extend(admitted)
        if self.native_infernal_returns is not None:
            admitted = self.native_infernal_returns.record_admission(context, form, schema, operation_key)
            native_references.update(admitted)
            references.extend(admitted)
        if self.api_execution is not None:
            references.extend(self.api_execution.record_bvbrc_admission(context, form, schema, operation_key))
            references.extend(self.api_execution.minhash.record_admission(context, form, schema, operation_key))
            references.extend(self.api_execution.homology_returns.record_admission(context, form, schema, operation_key))
            references.extend(self.api_execution.phylogeny_returns.record_admission(context, form, schema, operation_key))
            references.extend(self.api_execution.alignment_returns.record_admission(context, form, schema, operation_key))
            references.extend(self.api_execution.genome_alignment_returns.record_admission(context, form, schema, operation_key))
            references.extend(self.api_execution.proteome_returns.record_admission(context, form, schema, operation_key))
            references.extend(self.api_execution.comparative_systems_returns.record_admission(context, form, schema, operation_key))
            references.extend(self.api_execution.fastqutils_returns.record_admission(context, form, schema, operation_key))
            admitted = self.api_execution.application_returns.record_admission(context, form, schema, operation_key)
            references.extend(admitted)
            native_references.update(admitted)
        for name, declared in plain(schema).get('properties', {}).items():
            if declared.get('x-source') in FAMILY_SOURCES.values():
                for row in form[name]:
                    for reference in [row['source_ref'], row['observation_ref'], *row['reference_refs']]:
                        if reference is None:
                            continue
                        if not self.resolve(context, reference, 'execution_result'):
                            raise ValueError('execution_received_reference_unqualified')
                        references.append(reference)
            if declared.get('x-source') == 'execution_blast_hsps':
                for row in form[name]:
                    for field in ('hsp_ref', 'reference_ref'):
                        reference = row[field]
                        if not self.resolve(context, reference, 'execution_result'):
                            raise ValueError('execution_received_reference_unqualified')
                        references.append(reference)
            if declared.get('x-source') == BLAST_GRADED_RETURN_SOURCE:
                for row in form[name]:
                    if not self.resolve(context, row['result_ref'], 'execution_result'):
                        raise ValueError('blast_grader_result_reference_unqualified')
                    references.append(row['result_ref'])
            if declared.get('x-source') in {'execution_handoff_refs', 'execution_result_refs', 'practical_receipt_refs', 'bvbrc_appservice_support_refs'}:
                for reference in form[name]:
                    namespace = declared['items'].get('x-reference-namespace')
                    already_admitted = namespace == 'execution_result' and reference in native_references
                    if not already_admitted and (not self.resolve(context, reference, namespace)):
                        raise ValueError('execution_received_reference_unqualified')
                    references.append(reference)
        return list(dict.fromkeys(references))
