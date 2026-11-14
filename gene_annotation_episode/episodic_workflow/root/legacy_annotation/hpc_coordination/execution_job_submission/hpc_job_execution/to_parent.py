"""Private to_parent responsibility with original configured behavior."""
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


class HPCExecutionParentReport:
    def required_return_sources(self, parent, role):
        """Own selected parent return policy; received-report validation stays intact."""
        if role != 'launch_hpc':
            raise ValueError('fixed_execution_role_required')
        parent is not None and parent.path[-1][0] == 'scientific_process' and getattr(self.services, 'annotation_task_required', lambda: False)()
        return ()

    def validate_report(self, context, form, original_schema):
        if context.role != 'launch_hpc' or context.run_id != self.run_id:
            raise ValueError('fixed_execution_context_required')
        if self.native_flux_balance_returns is not None:
            self.native_flux_balance_returns.validate_received_report(context, form, original_schema)
        self.native_blast_masking_returns.validate_received_report(context, form, original_schema)
        self.native_blast_utility_returns.validate_received_report(context, form, original_schema)
        frozen_facts = None
        if self._has_uniprot():
            from gene_annotation_episode.episodic_workflow.root.library.uniprot_return_contracts import requested_uniprot_selection
            if requested_uniprot_selection(plain(original_schema)) is not None:
                host = self.api_execution.uniprot_returns
                host.validate_received_report(context, form, original_schema)
                if host._successful_closed(context):
                    frozen_facts = host._closed(context)['facts']
        if self._has_enrichr():
            from gene_annotation_episode.enrichr_returns import OWN_WITNESSES, requested_enrichr_fields
            host = self.api_execution.enrichr_returns
            if requested_enrichr_fields(plain(original_schema)):
                host.validate_received_report(context, form, original_schema)
            closed = host._closed(context)
            if closed is not None and OWN_WITNESSES in closed['facts'] and host._successful_closed(context):
                full_schema = (plain(context.request).get('report_contract') or {}).get('measurements', {}).get('schema', {})
                host.facts_for_closure(context, full_schema)
                frozen_facts = closed['facts']
        if self._has_addgene():
            from gene_annotation_episode.addgene_sequence_returns import OWN_BINDINGS, requested_addgene_fields
            host = self.api_execution.addgene_returns
            if requested_addgene_fields(plain(original_schema)):
                host.validate_received_report(context, form, original_schema)
            closed = host._closed(context)
            if closed is not None and OWN_BINDINGS in closed['facts']:
                full_schema = (plain(context.request).get('report_contract') or {}).get('measurements', {}).get('schema', {})
                if OWN_BINDINGS not in host.facts_for_closure(context, full_schema):
                    raise ValueError('addgene_sequence_return_original_schema_conflict')
                frozen_facts = closed['facts']
        if plain(original_schema).get('properties') is not None:
            self.native_fluorescence_returns.validate_received_report(context, form, original_schema)
        if self.native_expression_nmf_returns is not None:
            self.native_expression_nmf_returns.validate_received_report(context, form, original_schema)
        if self.atac_returns is not None:
            self.atac_returns.validate_received_report(context, form, original_schema)
        if self.native_chromatin_interaction_returns is not None:
            self.native_chromatin_interaction_returns.validate_received_report(context, form, original_schema)
        if self.native_genomic_overlap_returns is not None:
            self.native_genomic_overlap_returns.validate_received_report(context, form, original_schema)
        self.native_protein_structure_returns.validate_received_report(context, form, original_schema)
        validate_form(form, original_schema, lambda ref, ns: self.resolve(context, ref, ns))
        fact_fields = {name: declared['x-source'] for name, declared in plain(original_schema).get('properties', {}).items() if declared.get('x-source') is not None}
        if not fact_fields:
            return
        facts = self.facts(context, {}) if frozen_facts is None else frozen_facts
        for name, source in fact_fields.items():
            if source in facts and form[name] != facts[source]:
                raise ValueError('execution_report_disagrees_with_recorded_facts')
