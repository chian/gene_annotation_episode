"""Private initial_references responsibility with original returned-value semantics."""
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


class ExecutionSubmissionInitialReferences:
    def initial_references(self, context):
        if context.role != 'launch' or context.run_id != self.run_id:
            raise ValueError('fixed_execution_context_required')
        from gene_annotation_episode.episodic_workflow.root.library.lumpy_request_binding import is_compact_assignment as is_lumpy_assignment, is_compact_launch as is_lumpy_launch, read_request_binding as read_lumpy_binding
        if is_lumpy_launch(plain(context.assignment)) or is_lumpy_assignment(plain(context.assignment)):
            control = read_lumpy_binding(self.store, self.run_id, context.episode_id)
            refs = []
            if self._closed_operational_credit_view(context, None) is not None:
                from gene_annotation_episode.native_file_capture import _identity, _metadata
                from gene_annotation_episode.episodic_workflow.root.received_native_file_inputs import received_file_context
                known, _ = received_file_context(self.store, context, failure_prefix='lumpy_input_', baseline=True)
                original_initial = {row['record_ref'] for row in self.store.db.execute("SELECT record_ref FROM runtime_record_receipts WHERE run_id=? AND episode_id=? AND receipt_kind='initial'", (self.run_id, context.episode_id))}
                for row in control['requests']:
                    versions = []
                    for supplied in row['input_files']:
                        file = _identity(supplied)
                        reference = file['artifact_ref']
                        version = dict(reference=reference, version=None, content_sha256=file['sha256'])
                        if version not in versions:
                            versions.append(version)
                        if reference not in known or reference not in original_initial:
                            raise ValueError('lumpy_input_original_admission_conflict')
                        if self.resolve_received_reference(context, reference, None) is False:
                            raise ValueError('lumpy_input_protected_reference_denied')
                        metadata = _metadata(self.store, reference)
                        if metadata['sha256'] != file['sha256'] or metadata['size'] != file['size_bytes']:
                            raise ValueError('lumpy_input_file_metadata_conflict')
                        refs.append(reference)
                    if canonical(row['input_versions']) != canonical(versions):
                        raise ValueError('lumpy_input_version_conflict')
                return list(dict.fromkeys(refs))
            for row in control['requests']:
                refs.extend(self._lumpy_inputs(context, row['assignment']))
            return list(dict.fromkeys(refs))
        from gene_annotation_episode.episodic_workflow.root.library.macs2_peak_request_binding import is_compact_assignment as is_macs2_assignment, is_compact_launch as is_macs2_launch, read_request_binding as read_macs2_binding
        if is_macs2_launch(plain(context.assignment)) or is_macs2_assignment(plain(context.assignment)):
            control = read_macs2_binding(self.store, self.run_id, context.episode_id)
            refs = []
            if self._closed_operational_credit_view(context, None) is not None:
                from gene_annotation_episode.episodic_workflow.root.received_native_file_inputs import received_file_context, received_file_source
                known, receiving_scope = received_file_context(self.store, context, failure_prefix='macs2_peak_input_', baseline=True)
                original_initial = {row['record_ref'] for row in self.store.db.execute("SELECT record_ref FROM runtime_record_receipts WHERE run_id=? AND episode_id=? AND receipt_kind='initial'", (self.run_id, context.episode_id))}
                for row in control['requests']:
                    versions = []
                    for file in row['input_files']:
                        version = dict(reference=file['artifact_ref'], version=None, content_sha256=file['sha256'])
                        if version not in versions:
                            versions.append(version)
                    if canonical(row['input_versions']) != canonical(versions):
                        raise ValueError('macs2_peak_input_version_conflict')
                    reference = row['assignment']['requested_job']['native_macs2_peak']['request']['reference']
                    metadata_refs = [source for value in [reference, *reference['contigs'], *reference['aliases']] for source in value['source_refs']]
                    selected = [file['artifact_ref'] for file in row['input_files']]
                    for reference in [*selected, *metadata_refs]:
                        if reference not in known or reference not in original_initial:
                            raise ValueError('macs2_peak_input_original_admission_conflict')
                        if self.resolve_received_reference(context, reference, None) is False:
                            raise ValueError('macs2_peak_input_protected_reference_denied')
                        if reference in metadata_refs:
                            if reference not in self.store.reference_subset([reference], receiving_scope):
                                raise ValueError('macs2_peak_input_input_outside_scope')
                            received_file_source(self.store, reference, metadata=True, failure_prefix='macs2_peak_input_')
                        refs.append(reference)
                return list(dict.fromkeys(refs))
            for row in control['requests']:
                refs.extend(self._macs2_peak_inputs(context, row['assignment']))
            return list(dict.fromkeys(refs))
        from gene_annotation_episode.episodic_workflow.root.library.flux_balance_request_binding import is_compact_assignment, is_compact_launch, read_request_binding
        if is_compact_assignment(plain(context.assignment)) or is_compact_launch(plain(context.assignment)):
            control = read_request_binding(self.store, self.run_id, context.episode_id)
            return list(dict.fromkeys((version['reference'] for row in control['requests'] for version in row['input_versions'])))
        if self._has_appservice() and (self.api_execution.appservice.owns_context(context) or any((value.get('service') == 'bvbrc_appservice' for value in plain(context.assignment).get('requests', {}).values()))):
            return self.api_execution.appservice.initial_references(context)
        from gene_annotation_episode.episodic_workflow.root.library.rna_result_operand_authority import validate_rna_structure_job_inputs
        from gene_annotation_episode.episodic_workflow.root.protein_structure_operands import validate_protein_structure_job_inputs
        assignment = plain(context.assignment)
        requests = assignment.get('requests', {}).values()
        references = []
        for request in requests:
            references.extend(self._masking_inputs(context, request))
            references.extend(self._utility_inputs(context, request))
            references.extend(self._fluorescence_inputs(context, request))
            references.extend(self._expression_nmf_inputs(context, request))
            references.extend(self._flux_balance_inputs(context, request))
            references.extend(self._macs2_peak_inputs(context, request))
            references.extend(self._lumpy_inputs(context, request))
            references.extend(self._atac_inputs(context, request))
            references.extend(self._chromatin_inputs(context, request))
            references.extend(self._genomic_overlap_inputs(context, request))
            references.extend(validate_protein_structure_job_inputs(self.store, context, request, returns=self.native_protein_structure_returns))
            references.extend(validate_rna_structure_job_inputs(self.store, context, request))
        return list(dict.fromkeys(references))
        assignment = plain(context.assignment)
        selected = [assignment['handoff_ref']]
        target = self._target(context)
        if self.native_flux_balance_results is not None and self.native_flux_balance_results.applies(context):
            selector = self._selector(assignment, target)
            if selector['mode'] == 'saved_sheet_recalculation':
                self.native_flux_balance_returns.authenticate_received_saved_sheet(context, selector['saved_sheet_file'])
                selected.append(selector['saved_sheet_file']['artifact_ref'])
            return list(dict.fromkeys(selected))
        if self.native_blast_masking_results.applies(context):
            self._selector(assignment, target)
            return self.native_blast_masking_results.validate_selected_inputs(context, assignment)
        if self.native_blast_utility_results.applies(context):
            self._selector(assignment, target)
            return self.native_blast_utility_results.validate_selected_inputs(context, assignment)
        if self.native_fluorescence_results.applies(context):
            selector = self._selector(assignment, target)
            if selector['mode'] == 'saved_sheet_recalculation':
                self.native_fluorescence_returns.authenticate_received_saved_sheet(context, selector['saved_sheet_file'])
                selected.append(selector['saved_sheet_file']['artifact_ref'])
            return list(dict.fromkeys(selected))
        if self.native_expression_nmf_results is not None and self.native_expression_nmf_results.applies(context):
            selector = self._selector(assignment, target)
            if selector['mode'] == 'saved_sheet_recalculation':
                self.native_expression_nmf_returns.authenticate_received_saved_sheet(context, selector['saved_sheet_file'])
                selected.append(selector['saved_sheet_file']['artifact_ref'])
            return list(dict.fromkeys(selected))
        if self.atac_results is not None and self.atac_results.applies(context):
            selector = self._selector(assignment, target)
            if selector['mode'] == 'saved_sheet_recalculation':
                bundle = selector['saved_sheet_bundle']
                self.atac_returns.authenticate_received_saved_bundle(context, bundle)
                selected.extend([bundle['sheet']['artifact_ref'], *(row['file']['artifact_ref'] for row in bundle['tables'])])
            return list(dict.fromkeys(selected))
        if self.native_chromatin_interaction_results is not None and self.native_chromatin_interaction_results.applies(context):
            selector = self._selector(assignment, target)
            if selector['mode'] == 'saved_sheet_recalculation':
                bundle = selector['saved_sheet_bundle']
                self.native_chromatin_interaction_returns.authenticate_received_saved_bundle(context, bundle)
                selected.extend((file['artifact_ref'] for file in [bundle['sheet'], *bundle['tables']]))
            return list(dict.fromkeys(selected))
        if self.native_genomic_overlap_results is not None and self.native_genomic_overlap_results.applies(context):
            selector = self._selector(assignment, target)
            if selector['mode'] == 'saved_sheet_recalculation':
                self.native_genomic_overlap_returns.authenticate_received_saved_sheet(context, selector['saved_sheet_file'])
                selected.append(selector['saved_sheet_file']['artifact_ref'])
            return list(dict.fromkeys(selected))
        if self.native_protein_structure_results.applies(context):
            self._selector(assignment, target)
            from gene_annotation_episode.episodic_workflow.root.protein_structure_operands import validate_protein_structure_selected_inputs
            return validate_protein_structure_selected_inputs(self.store, context, assignment['selector'], handoff_ref=assignment['handoff_ref'], returns=self.native_protein_structure_returns)
        if self._comparison_selector(assignment):
            self._selector(assignment, target)
            from gene_annotation_episode.episodic_workflow.root.rna_structure_comparison_operands import validate_rna_comparison_selected_inputs
            return validate_rna_comparison_selected_inputs(self.store, context, assignment['selector'], anchor_handoff_ref=assignment['handoff_ref'], returns=self.native_rna_structure_returns)
        if is_native_rna_structure_target(target):
            from gene_annotation_episode.episodic_workflow.root.library.rna_result_operand_authority import validate_rna_structure_selected_inputs
            selected.extend(validate_rna_structure_selected_inputs(self.store, context, assignment['selector'], handoff_ref=assignment['handoff_ref'], returns=self.native_rna_structure_returns))
        if is_standard_blast_database_target(target):
            from gene_annotation_episode.episodic_workflow.root.library.native_blast_standard_database_result_publication import validate_standard_blast_selected_inputs
            selected.extend(validate_standard_blast_selected_inputs(self.store, context, assignment['selector'], handoff_ref=assignment['handoff_ref']))
        if is_native_blast_database_target(target):
            from gene_annotation_episode.episodic_workflow.root.library.native_blast_database_result_publication import validate_selected_inputs
            selected.extend(validate_selected_inputs(self.store, context, assignment['selector'], handoff_ref=assignment['handoff_ref']))
        from gene_annotation_episode.episodic_workflow.root.bvbrc_data_host import is_bvbrc_request
        if target['resource_kind'] == 'api' and is_bvbrc_request(target['assignment'].get('request')):
            extra = list(dict.fromkeys((row['source_ref'] for row in assignment['selector']['inputs'])))
            for reference in extra:
                self.api_execution.bvbrc_data.possession(context, reference)
            selected.extend(extra)
        if target['resource_kind'] == 'api' and target['assignment'].get('service') == 'bvbrc_minhash':
            extra = self.api_execution.minhash._selected_input_refs(assignment)
            for reference in extra:
                self.api_execution.minhash.possession(context, reference)
            selected.extend((reference for reference in extra if reference not in selected))
        return selected

