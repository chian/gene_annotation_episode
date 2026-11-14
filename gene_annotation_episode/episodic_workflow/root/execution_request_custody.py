"""Complete original execution request and receipt custody responsibility."""
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

class ExecutionRequestCustody:
    @staticmethod
    def _request_yield_class(request):
        """Classify the original execution request without generated IDs."""
        request = plain(request)
        version = request.get('version')
        if version != 'practical_assignment_v1':
            if version in ('api_execution_assignment_v1', 'api_service_assignment_v1'):
                parts = ['api', request.get('service', 'unknown')]
                for field in ('algorithm', 'database'):
                    if field in request:
                        parts.append(request[field])
                return '_'.join(parts) + '_handoff'
            return 'compact_' + str(version)
        requested = request['requested_job']
        native = sorted((key for key in requested if key.startswith('native_')))
        parts = ['practical', request['resource_kind']]
        parts.extend(native)
        parts.append({'usable_handoff': 'handoff', 'completed_job_outputs': 'outputs'}[request['endpoint']])
        return '_'.join(parts)

    def _task_yield_profile(self, key):
        binding = self.task_yield_profiles.get(key)
        if binding is None:
            raise ValueError('execution_original_task_yield_profile_required:' + key)
        return binding

    def _request_schema(self, resource_id, *, selected, internal=False, compact=True):
        kind = KINDS[self.resources[resource_id]['kind']]
        schema = deepcopy(self.api_execution.assignment_schema(resource_id) if kind == 'api' else ASSIGNMENT_SCHEMA)
        if schema.get('type') != 'object' or not isinstance(schema.get('properties'), dict):
            raise ValueError('concrete_execution_assignment_schema_required')
        schema['properties']['resource_id'] = {'type': 'string', 'const': resource_id}
        if kind != 'api':
            schema['properties']['resource_kind'] = {'type': 'string', 'const': kind}
            alternatives = []
            if internal and self.resources[resource_id].get('native_flux_balance'):
                from gene_annotation_episode.episodic_workflow.root.library.flux_balance_contracts import flux_balance_schema
                for binding in self.resources[resource_id]['native_flux_balance']:
                    alternatives.append({'allOf': [flux_balance_schema('FBARequestedJob'), {'properties': {'native_flux_balance': {'properties': {'operation': {'const': binding['operation']}, 'mode': {'const': binding['mode']}, 'software': {'const': deepcopy(binding['software'])}, 'model_input': {'properties': {'format': {'enum': deepcopy(binding['model_formats'])}}}}}}}]})
            fluorescence = self.resources[resource_id].get('native_fluorescence', [])
            if fluorescence:
                from gene_annotation_episode.episodic_workflow.root.library.native_fluorescence_tool_info import fluorescence_tool_contracts
                alternatives.extend((row['input_schema'] for row in fluorescence_tool_contracts(fluorescence, resource_kind=kind, resource_id=resource_id)))
            nmf = self.resources[resource_id].get('native_expression_nmf', [])
            if nmf:
                from .library.native_expression_nmf_tool_info import expression_nmf_tool_contracts
                alternatives.extend((row['input_schema'] for row in expression_nmf_tool_contracts(nmf, resource_kind=kind, resource_id=resource_id)))
            macs2_peak = self.resources[resource_id].get('native_macs2_peak', [])
            if macs2_peak and internal:
                from gene_annotation_episode.episodic_workflow.root.library.native_macs2_peak_execution import macs2_peak_execution_schema
                alternatives.append(macs2_peak_execution_schema('RequestedJob', bindings=macs2_peak))
            lumpy = self.resources[resource_id].get('native_lumpy', [])
            if lumpy and internal:
                from gene_annotation_episode.episodic_workflow.root.library.native_lumpy_execution import lumpy_execution_schema
                alternatives.append(lumpy_execution_schema('RequestedJob', bindings=lumpy))
            atac = self.resources[resource_id].get('native_atac_differential', [])
            if atac:
                from gene_annotation_episode.episodic_workflow.root.library.native_atac_differential_tool_info import atac_tool_contracts
                alternatives.extend((row['input_schema'] for row in atac_tool_contracts(atac, resource_kind=kind, resource_id=resource_id)))
            chromatin = self.resources[resource_id].get('native_chromatin_interactions', [])
            if chromatin:
                from gene_annotation_episode.episodic_workflow.root.library.native_chromatin_interaction_tool_info import chromatin_interaction_tool_contracts
                alternatives.extend((row['input_schema'] for row in chromatin_interaction_tool_contracts(chromatin, resource_kind=kind, resource_id=resource_id)))
            overlap = self.resources[resource_id].get('native_genomic_overlap', [])
            if overlap:
                from .library.native_genomic_overlap_tool_info import genomic_overlap_tool_contracts
                alternatives.extend((row['input_schema'] for row in genomic_overlap_tool_contracts(overlap, resource_kind=kind, resource_id=resource_id)))
            protein = self.resources[resource_id].get('native_protein_structure', [])
            if protein:
                from gene_annotation_episode.episodic_workflow.root.library.native_protein_structure_tool_info import protein_structure_tool_contracts
                alternatives.extend((row['input_schema'] for row in protein_structure_tool_contracts(protein, resource_kind='local', resource_id=resource_id)))
            rna = self.resources[resource_id].get('native_rna_structure', [])
            if rna:
                from gene_annotation_episode.episodic_workflow.root.library.native_rna_structure_tool_info import rna_structure_tool_contracts
                alternatives.extend((row['input_schema'] for row in rna_structure_tool_contracts(rna, resource_kind=kind, resource_id=resource_id)))
            database = self.resources[resource_id].get('native_blast_standard_database')
            if database:
                from .library.native_blast_standard_database_tool_info import standard_blast_database_tool_contracts
                alternatives.extend((row['input_schema'] for row in standard_blast_database_tool_contracts(database['bindings'], resource_kind=kind, resource_id=resource_id)))
            database = self.resources[resource_id].get('native_blast_database')
            if database:
                from .library.native_blast_database_tool_info import native_blast_database_tool_contracts
                alternatives.extend((row['input_schema'] for row in native_blast_database_tool_contracts(database['bindings'], resource_kind=kind, resource_id=resource_id)))
            native = self.resources[resource_id].get('native_hmmer', [])
            if native:
                from gene_annotation_episode.episodic_workflow.root.library.native_hmmer_tool_info import native_hmmer_tool_contracts
                alternatives.extend((row['input_schema'] for row in native_hmmer_tool_contracts(native, resource_kind=kind, resource_id=resource_id)))
            masking = self.resources[resource_id].get('native_blast_masking', [])
            if masking:
                from gene_annotation_episode.episodic_workflow.root.library.native_blast_masking_tool_info import native_blast_masking_tool_contracts
                alternatives.extend((row['input_schema'] for row in native_blast_masking_tool_contracts(masking, resource_kind=kind, resource_id=resource_id)))
            utility = self.resources[resource_id].get('native_blast_utility', [])
            if utility:
                from gene_annotation_episode.episodic_workflow.root.library.native_blast_utility_tool_info import native_blast_utility_tool_contracts
                alternatives.extend((row['input_schema'] for row in native_blast_utility_tool_contracts(utility, resource_kind=kind, resource_id=resource_id)))
            blast = self.resources[resource_id].get('native_blast', [])
            if blast:
                from gene_annotation_episode.episodic_workflow.root.library.native_blast_tool_info import native_blast_tool_contracts
                alternatives.extend((row['input_schema'] for row in native_blast_tool_contracts(blast, resource_kind=kind, resource_id=resource_id)))
            infernal = self.resources[resource_id].get('native_infernal', [])
            if infernal:
                from gene_annotation_episode.episodic_workflow.root.library.native_infernal_tool_info import native_infernal_tool_contracts
                alternatives.extend((row['input_schema'] for row in native_infernal_tool_contracts(infernal, resource_kind=kind, resource_id=resource_id)))
            preparation = self.resources[resource_id].get('native_infernal_preparation', [])
            if preparation:
                from gene_annotation_episode.episodic_workflow.root.library.native_infernal_preparation_tool_info import native_infernal_preparation_tool_contracts
                alternatives.extend((row['input_schema'] for row in native_infernal_preparation_tool_contracts(preparation, resource_kind=kind, resource_id=resource_id)))
            hmmer_preparation = self.resources[resource_id].get('native_hmmer_preparation', [])
            if hmmer_preparation:
                from gene_annotation_episode.episodic_workflow.root.library.native_hmmer_preparation_tool_info import native_hmmer_preparation_tool_contracts
                alternatives.extend((row['input_schema'] for row in native_hmmer_preparation_tool_contracts(hmmer_preparation, resource_kind=kind, resource_id=resource_id)))
            if alternatives:
                schema['properties']['requested_job'] = {'anyOf': [deepcopy(GENERIC_REQUESTED_JOB_SCHEMA), *alternatives]}
            else:
                schema['properties']['requested_job'] = deepcopy(GENERIC_REQUESTED_JOB_SCHEMA)
        if selected and 'resource_id' not in schema['required']:
            schema['required'].append('resource_id')
        lumpy_compact = []
        if compact and kind == 'local' and self.resources[resource_id].get('native_lumpy'):
            from gene_annotation_episode.episodic_workflow.root.library.lumpy_request_binding import resource_assignment_schema
            lumpy_compact.append(resource_assignment_schema(resource_id, selected=selected, bindings=self.resources[resource_id]['native_lumpy']))
        if compact and kind == 'local' and self.resources[resource_id].get('native_flux_balance'):
            from gene_annotation_episode.episodic_workflow.root.library.flux_balance_request_binding import resource_assignment_schema
            return {'anyOf': [schema, resource_assignment_schema(resource_id, selected=selected), *lumpy_compact]}
        if compact and kind == 'local' and self.resources[resource_id].get('native_macs2_peak'):
            from gene_annotation_episode.episodic_workflow.root.library.macs2_peak_request_binding import resource_assignment_schema
            return {'anyOf': [schema, resource_assignment_schema(resource_id, selected=selected, bindings=self.resources[resource_id]['native_macs2_peak']), *lumpy_compact]}
        if lumpy_compact:
            return {'anyOf': [schema, *lumpy_compact]}
        return schema

    def _validate_request(self, value, *, resource_id=None):
        resource_id = resource_id or value.get('resource_id')
        if resource_id not in self.resources:
            raise ValueError('execution_resource_not_bound')
        config = self.resources[resource_id]
        kind = KINDS[config['kind']]
        from gene_annotation_episode.episodic_workflow.root.library.lumpy_request_binding import is_compact_assignment as is_lumpy_assignment, validate_compact_assignment as validate_lumpy_assignment
        if is_lumpy_assignment(value):
            if kind != 'local' or not config.get('native_lumpy'):
                raise ValueError('lumpy_request_binding_unavailable')
            return validate_lumpy_assignment(value, resource_id, bindings=config['native_lumpy'])
        from gene_annotation_episode.episodic_workflow.root.library.macs2_peak_request_binding import is_compact_assignment as is_macs2_assignment, validate_compact_assignment as validate_macs2_assignment
        if is_macs2_assignment(value):
            if kind != 'local' or not config.get('native_macs2_peak'):
                raise ValueError('macs2_peak_request_binding_unavailable')
            return validate_macs2_assignment(value, resource_id, bindings=config['native_macs2_peak'])
        from gene_annotation_episode.episodic_workflow.root.library.flux_balance_request_binding import is_compact_assignment, validate_compact_assignment
        if is_compact_assignment(value):
            if kind != 'local' or not config.get('native_flux_balance'):
                raise ValueError('flux_balance_request_binding_unavailable')
            return validate_compact_assignment(value, resource_id)
        value = self.api_execution.validate_assignment(value) if kind == 'api' else validate_assignment(value)
        if value.get('resource_id', resource_id) != resource_id:
            raise ValueError('execution_resource_identity_conflict')
        if kind != 'api':
            if value['resource_kind'] != kind:
                raise ValueError('execution_resource_kind_conflict')
            confined(value['workspace'], config['workspace'])
            operations = self._practical[resource_id]._operations(kind)
            validator = getattr(operations, 'validate_assignment', None)
            if validator is not None:
                validator({**value, 'resource_id': resource_id})
        return value

    def _launch(self, value, *, scope=None):
        value = checked(value, self.launch_assignment_schema(internal=True), 'invalid_execution_launch_assignment')
        for resource_id, request in value['requests'].items():
            if request.get('version') == BLAST_GRADED_REQUEST_VERSION:
                checked(request, BLAST_GRADED_REQUEST_SCHEMA, 'blast_database_grader_return_request_invalid')
                if request['resource_id'] != resource_id or self.resources[resource_id].get('service') != 'ncbi_blast':
                    raise ValueError('blast_database_grader_resource_conflict')
                continue
            self._validate_request(request, resource_id=resource_id)
            if scope is not None and KINDS[self.resources[resource_id]['kind']] == 'api':
                self.api_execution.validate_assignment(request, scope=scope)
        self._constraints(value['constraints'])
        return value

    @staticmethod
    def _constraints(constraints):
        for key in ('allowed_resource_ids', 'allowed_kinds'):
            if key in constraints and (not isinstance(constraints[key], list) or any((not isinstance(item, str) or not item for item in constraints[key]))):
                raise ValueError('invalid_execution_resource_constraints')

    def _permitted(self, assignment, resource_id):
        constraints = assignment['constraints']
        kind = KINDS[self.resources[resource_id]['kind']]
        return resource_id in assignment['requests'] and ('allowed_resource_ids' not in constraints or resource_id in constraints['allowed_resource_ids']) and ('allowed_kinds' not in constraints or kind in constraints['allowed_kinds']) and ('resource_id' not in constraints or resource_id == constraints['resource_id']) and ('kind' not in constraints or kind == constraints['kind'])

    def _delegate(self, context):
        assignment = self._validate_request(plain(context.assignment))
        if context.role == 'launch_api':
            return self.api_execution
        original = self._practical[assignment['resource_id']]
        from .execution_binding_catalogue import native_resource_for_context
        return native_resource_for_context(getattr(self, 'owner', self), context,
                                           assignment['resource_id'], original)

    def _practical_context(self, context):
        """An internal execution view; the immutable episode request stays original."""
        from gene_annotation_episode.episodic_workflow.root.library.lumpy_request_binding import is_compact_assignment as is_lumpy_assignment, materialized_assignment as materialized_lumpy_assignment
        if is_lumpy_assignment(plain(context.assignment)):
            from gene_annotation_episode.episodic_workflow.root.episode_bindings import BindingContext
            practical = BindingContext(context.run_id, context.episode_id, context.role, context.path, context.scope, materialized_lumpy_assignment(self.store, context), context.request, context.received_record_refs)
            self.lumpy_requests.validate_practical_history(context, practical, self._delegate(context))
            return practical
        from gene_annotation_episode.episodic_workflow.root.library.macs2_peak_request_binding import is_compact_assignment as is_macs2_assignment, materialized_assignment as materialized_macs2_assignment
        if is_macs2_assignment(plain(context.assignment)):
            from gene_annotation_episode.episodic_workflow.root.episode_bindings import BindingContext
            practical = BindingContext(context.run_id, context.episode_id, context.role, context.path, context.scope, materialized_macs2_assignment(self.store, context), context.request, context.received_record_refs)
            self.macs2_peak_requests.validate_practical_history(context, practical, self._delegate(context))
            return practical
        from gene_annotation_episode.episodic_workflow.root.library.flux_balance_request_binding import is_compact_assignment, materialized_assignment
        if not is_compact_assignment(plain(context.assignment)):
            return context
        from gene_annotation_episode.episodic_workflow.root.episode_bindings import BindingContext
        practical = BindingContext(context.run_id, context.episode_id, context.role, context.path, context.scope, materialized_assignment(self.store, context), context.request, context.received_record_refs)
        self.flux_balance_requests.validate_practical_history(context, practical, self._delegate(context))
        return practical

    def state(self, context):
        """Expose the original practical state for its original resource role."""
        if context.role not in {'launch_local', 'launch_hpc'}:
            raise ValueError('practical_resource_role_required')
        return self._delegate(context).state(self._practical_context(context))

    def initial_references(self, context):
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
        if self._has_appservice() and (self.api_execution.appservice.owns_context(context) or (context.role == 'launch' and any((value.get('service') == 'bvbrc_appservice' for value in plain(context.assignment).get('requests', {}).values())))):
            return self.api_execution.appservice.initial_references(context)
        if context.role != 'results':
            from gene_annotation_episode.episodic_workflow.root.library.rna_result_operand_authority import validate_rna_structure_job_inputs
            from gene_annotation_episode.episodic_workflow.root.protein_structure_operands import validate_protein_structure_job_inputs
            assignment = plain(context.assignment)
            requests = assignment.get('requests', {}).values() if context.role == 'launch' else [assignment] if context.role == 'launch_local' else []
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

    def resolve(self, context, reference, namespace):
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
                from gene_annotation_episode.episodic_workflow.root.library.rna_structure_result_views import IDENTIFIER_NAMESPACES as RNA_NAMESPACES
                if namespace in RNA_NAMESPACES:
                    return self.native_rna_structure_results.resolve(context, reference, namespace) if context.role == 'results' else self.native_rna_structure_returns.resolve_received(context, reference, namespace)
                if self.native_rna_structure_results.resolve(context, reference, namespace):
                    return True
                if context.role in {'annotation', 'scientific_process'}:
                    resolved = self.native_rna_structure_returns.resolve_received(context, reference, namespace)
                    if resolved is not None:
                        return resolved
            if self.native_blast_standard_database_results is not None:
                from gene_annotation_episode.episodic_workflow.root.native_blast_standard_database_results import IDENTIFIER_NAMESPACES as DATABASE_NAMESPACES
                if namespace in DATABASE_NAMESPACES:
                    return self.native_blast_standard_database_results.resolve(context, reference, namespace) if context.role == 'results' else self.native_blast_standard_database_returns.resolve_received(context, reference, namespace)
                if self.native_blast_standard_database_results.resolve(context, reference, namespace):
                    return True
                if context.role in {'annotation', 'scientific_process'}:
                    resolved = self.native_blast_standard_database_returns.resolve_received(context, reference, namespace)
                    if resolved is not None:
                        return resolved
            if self.native_blast_database_results is not None:
                from gene_annotation_episode.episodic_workflow.root.native_blast_database_results import IDENTIFIER_NAMESPACES as DATABASE_NAMESPACES
                if namespace in DATABASE_NAMESPACES:
                    return self.native_blast_database_results.resolve(context, reference, namespace) if context.role == 'results' else self.native_blast_database_returns.resolve_received(context, reference, namespace)
                if self.native_blast_database_results.resolve(context, reference, namespace):
                    return True
                if context.role in {'annotation', 'scientific_process'}:
                    resolved = self.native_blast_database_returns.resolve_received(context, reference, namespace)
                    if resolved is not None:
                        return resolved
            if self.native_hmmer_preparation_results is not None:
                from gene_annotation_episode.episodic_workflow.root.library.hmmer_preparation_result_views import IDENTIFIER_NAMESPACES as HMMER_PREPARATION_NAMESPACES
                if namespace in HMMER_PREPARATION_NAMESPACES:
                    return self.native_hmmer_preparation_results.resolve(context, reference, namespace) if context.role == 'results' else self.native_hmmer_preparation_returns.resolve_received(context, reference, namespace)
                if self.native_hmmer_preparation_results.resolve(context, reference, namespace):
                    return True
                if context.role in {'annotation', 'scientific_process'}:
                    resolved = self.native_hmmer_preparation_returns.resolve_received(context, reference, namespace)
                    if resolved is not None:
                        return resolved
            if self.native_infernal_preparation_results is not None:
                from gene_annotation_episode.episodic_workflow.root.library.infernal_preparation_result_views import IDENTIFIER_NAMESPACES as PREPARATION_NAMESPACES
                if namespace in PREPARATION_NAMESPACES:
                    return self.native_infernal_preparation_results.resolve(context, reference, namespace) if context.role == 'results' else self.native_infernal_preparation_returns.resolve_received(context, reference, namespace)
                if self.native_infernal_preparation_results.resolve(context, reference, namespace):
                    return True
                if context.role in {'annotation', 'scientific_process'}:
                    resolved = self.native_infernal_preparation_returns.resolve_received(context, reference, namespace)
                    if resolved is not None:
                        return resolved
            if self._has_rfam():
                from gene_annotation_episode.episodic_workflow.root.rfam_batch_returns import IDENTIFIER_NAMESPACES as RFAM_NAMESPACES
                if namespace in RFAM_NAMESPACES:
                    return self.api_execution.rfam_returns.resolve_own(context, reference, namespace) if context.role == 'results' else self.api_execution.rfam_returns.resolve_received(context, reference, namespace)
            if self.native_blast_results is not None:
                if namespace in {'native_blast_pairwise_row', 'native_blast_artifact_key', 'native_blast_search_pointer'}:
                    return self.native_blast_results.resolve(context, reference, namespace) if context.role == 'results' else self.native_blast_returns.resolve_received(context, reference, namespace)
                if self.native_blast_results.resolve(context, reference, namespace):
                    return True
                if context.role in {'annotation', 'scientific_process'}:
                    resolved = self.native_blast_returns.resolve_received(context, reference, namespace)
                    if resolved is not None:
                        return resolved
            if self.native_infernal_results is not None:
                from gene_annotation_episode.episodic_workflow.root.library.infernal_native_result_views import IDENTIFIER_NAMESPACES as INFERNAL_NAMESPACES
                if namespace in INFERNAL_NAMESPACES:
                    return self.native_infernal_results.resolve(context, reference, namespace) if context.role == 'results' else self.native_infernal_returns.resolve_received(context, reference, namespace)
                if self.native_infernal_results.resolve(context, reference, namespace):
                    return True
                if context.role in {'annotation', 'scientific_process'}:
                    resolved = self.native_infernal_returns.resolve_received(context, reference, namespace)
                    if resolved is not None:
                        return resolved
            if self._has_appservice():
                from gene_annotation_episode.episodic_workflow.root.bvbrc_homology_returns import IDENTIFIER_NAMESPACES
                if namespace in IDENTIFIER_NAMESPACES:
                    return self.api_execution.homology_returns.resolve_own(context, reference, namespace) if context.role == 'results' else self.api_execution.homology_returns.resolve_received(context, reference, namespace)
                from gene_annotation_episode.episodic_workflow.root.bvbrc_phylogeny_returns import IDENTIFIER_NAMESPACES as PHYLOGENY_NAMESPACES
                if namespace in PHYLOGENY_NAMESPACES:
                    return self.api_execution.phylogeny_returns.resolve_own(context, reference, namespace) if context.role == 'results' else self.api_execution.phylogeny_returns.resolve_received(context, reference, namespace)
                from gene_annotation_episode.episodic_workflow.root.bvbrc_alignment_returns import IDENTIFIER_NAMESPACES as ALIGNMENT_NAMESPACES
                if namespace in ALIGNMENT_NAMESPACES:
                    return self.api_execution.alignment_returns.resolve_own(context, reference, namespace) if context.role == 'results' else self.api_execution.alignment_returns.resolve_received(context, reference, namespace)
                from gene_annotation_episode.episodic_workflow.root.bvbrc_genome_alignment_returns import IDENTIFIER_NAMESPACES as GENOME_ALIGNMENT_NAMESPACES
                if namespace in GENOME_ALIGNMENT_NAMESPACES:
                    return self.api_execution.genome_alignment_returns.resolve_own(context, reference, namespace) if context.role == 'results' else self.api_execution.genome_alignment_returns.resolve_received(context, reference, namespace)
                from gene_annotation_episode.episodic_workflow.root.bvbrc_proteome_returns import IDENTIFIER_NAMESPACES as PROTEOME_NAMESPACES
                if namespace in PROTEOME_NAMESPACES:
                    return self.api_execution.proteome_returns.resolve_own(context, reference, namespace) if context.role == 'results' else self.api_execution.proteome_returns.resolve_received(context, reference, namespace)
                from gene_annotation_episode.episodic_workflow.root.bvbrc_comparative_systems_returns import IDENTIFIER_NAMESPACES as COMPARATIVE_NAMESPACES
                if namespace in COMPARATIVE_NAMESPACES:
                    return self.api_execution.comparative_systems_returns.resolve_own(context, reference, namespace) if context.role == 'results' else self.api_execution.comparative_systems_returns.resolve_received(context, reference, namespace)
                from gene_annotation_episode.bvbrc_fastqutils_returns import IDENTIFIER_NAMESPACES as FASTQUTILS_NAMESPACES
                if namespace in FASTQUTILS_NAMESPACES:
                    return self.api_execution.fastqutils_returns.resolve_own(context, reference, namespace) if context.role == 'results' else self.api_execution.fastqutils_returns.resolve_received(context, reference, namespace)
                from gene_annotation_episode.episodic_workflow.root.bvbrc_application_returns import IDENTIFIER_NAMESPACES as APPLICATION_NAMESPACES
                if namespace in APPLICATION_NAMESPACES:
                    return self.api_execution.application_returns.resolve_own(context, reference, namespace) if context.role == 'results' else self.api_execution.application_returns.resolve_received(context, reference, namespace)
                resolved = self.api_execution.appservice.resolve(context, reference, namespace)
                if resolved is not None:
                    return resolved
            if namespace == 'bvbrc_minhash_genome':
                if self.api_execution is None:
                    return False
                if context.role == 'results':
                    return self.api_execution.minhash.resolve_own(context, reference, namespace)
                return self.api_execution.minhash.resolve_received(context, reference, namespace)
            from gene_annotation_episode.episodic_workflow.root.library.bvbrc_data_views import IDENTIFIER_NAMESPACES
            if namespace in IDENTIFIER_NAMESPACES:
                return self.api_execution is not None and self.api_execution.bvbrc_data.resolve(context, reference, namespace)
            if namespace in {'execution_handle', 'execution'}:
                from gene_annotation_episode.episodic_workflow.root.episode_bindings import reference_in_context
                return bool(self.services is not None and reference_in_context(self.services, context, reference, namespace))
            if context.role in {'launch_local', 'launch_hpc'} and namespace == 'practical_receipt' and (not reference.startswith('source_')):
                return self._delegate(context).resolve(self._practical_context(context), reference, namespace)
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

    def _native_results_complete(self, context, bodies):
        if self.local_file_sources.applies(context):
            return self.local_file_sources.complete(context, bodies)
        if self.native_flux_balance_results is not None and self.native_flux_balance_results.applies(context):
            return False
        if self.native_blast_masking_results.applies(context):
            return False
        if self.native_blast_utility_results.applies(context):
            return False
        if self.native_fluorescence_results.applies(context):
            return False
        if self.native_expression_nmf_results is not None and self.native_expression_nmf_results.applies(context):
            return False
        if self.atac_results is not None and self.atac_results.applies(context):
            return False
        if self.native_chromatin_interaction_results is not None and self.native_chromatin_interaction_results.applies(context):
            return False
        if self.native_genomic_overlap_results is not None and self.native_genomic_overlap_results.applies(context):
            return False
        if self.native_protein_structure_results.applies(context):
            return False
        if is_native_rna_structure_target(self._target(context)):
            return False
        if is_standard_blast_database_target(self._target(context)):
            return False
        if is_native_blast_database_target(self._target(context)):
            return False
        if not bodies:
            return False
        closed = [body for body in bodies if body['observation']['state'] == 'completed' and body['observation']['returncode'] == 0]
        if not closed:
            return False
        target = self._target(context)
        requested = self._windows(self._selector(plain(context.assignment), target))
        for path, (start, length) in requested.items():
            windows = [window for body in closed for window in body['windows'] if window['path'] == path]
            if not windows:
                return False
            end = max((window['size_bytes'] for window in windows))
            if length is not None:
                end = min(end, start + length)
            cursor = start
            for window in sorted(windows, key=lambda item: item['offset']):
                if window['offset'] > cursor:
                    return False
                cursor = max(cursor, window['offset'] + window['returned_bytes'])
            if cursor < end:
                return False
        return True

    def _proof_for_action(self, context, operation_key):
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
        prefix = context.run_id + ':' + context.episode_id + ':'
        index = operation_key.removeprefix(prefix)
        if not operation_key.startswith(prefix) or not index.isdecimal() or str(int(index)) != index:
            return None
        row = self.store.db.execute('SELECT action,result FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?', (context.run_id, context.episode_id, int(index))).fetchone()
        if row is None or row['result'] is None:
            return None
        result = json.loads(row['result'])
        if result.get('status') != 'completed':
            return None
        if context.role == 'launch':
            qualified = []
            for reference in result.get('record_refs', []):
                try:
                    target = self.job_progress_provider.targets.read_target(reference, context.scope)
                    self._context_target(context, target)
                    if self.job_progress_provider.targets.usable_handoff(target):
                        qualified.append(reference)
                except (ValueError, KeyError):
                    pass
            complete = bool(qualified)
            keys, endpoint = (['received_usable_handoff'], 'usable_handoff')
        else:
            bodies = []
            rows = self.store.db.execute('SELECT result FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index<=? AND result IS NOT NULL ORDER BY decision_index', (context.run_id, context.episode_id, int(index)))
            for earlier in rows:
                outcome = json.loads(earlier[0])
                if outcome.get('status') != 'completed':
                    continue
                for reference in outcome.get('record_refs', []):
                    body = self._read_result(reference, context.scope)
                    if body is not None and body['assignment'] == plain(context.assignment):
                        bodies.append(body)
            complete = self._native_results_complete(context, bodies)
            keys = ['requested_filesystem_acquisition', 'successful_exact_attempt_observed', 'attempt_output_version_unverified']
            if self.local_file_sources.applies(context):
                keys = ['requested_complete_file_sources', 'exact_attempt_terminal_quiescent_observed', 'attempt_output_version_unverified']
            endpoint = 'usable_handoff'
        if not complete:
            return None
        receipt = {'action': json.loads(row['action']), 'outcome': result, 'endpoint': endpoint, 'validation_keys': keys}
        if context.role == 'results':
            receipt['supporting_receipt_sha256s'] = [digest(body) for body in bodies]
        return {'version': 'practical_completion_v1', 'run_id': context.run_id, 'episode_id': context.episode_id, 'assignment_sha256': digest(context.assignment), 'endpoint': endpoint, 'operation_key': operation_key, 'receipt_sha256': digest(receipt), 'validation_keys': keys}

    def verify_completion(self, context, proof):
        try:
            proof = validate_completion_proof(plain(proof))
        except (ValueError, TypeError):
            return False
        historical = self._closed_completion_verdict(context, proof)
        if historical is not None:
            return historical
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
        if context.role in {'launch_local', 'launch_hpc'}:
            return self.state(context).verify_completion(proof)
        if context.role == 'launch_api' or (context.role == 'results' and self._target(context)['resource_kind'] == 'api'):
            return self.api_execution.verify_completion(context, proof)
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

    def launch_assignment_schema(self, *, internal=False):
        schema = obj({'version': {'const': LAUNCH_VERSION}, 'requests': {'type': 'object', 'properties': {key: {'anyOf': [self._request_schema(key, selected=False, internal=internal, compact=False), {**deepcopy(BLAST_GRADED_REQUEST_SCHEMA), 'properties': {**deepcopy(BLAST_GRADED_REQUEST_SCHEMA['properties']), 'resource_id': {'const': key}}}]} if self.resources[key].get('service') == 'ncbi_blast' else self._request_schema(key, selected=False, internal=internal, compact=False) for key in self.resources}, 'minProperties': 1, 'additionalProperties': False}, 'immutable_input_versions': {'type': 'array', 'items': deepcopy(INPUT_VERSION_SCHEMA)}, 'constraints': {'type': 'object'}})
        schema['properties']['launch_instructions'] = deepcopy(SELECTION_SCHEMA)
        alternatives = [schema]
        if any((value.get('native_flux_balance') for value in self.resources.values())):
            from gene_annotation_episode.episodic_workflow.root.library.flux_balance_request_binding import launch_assignment_schema
            alternatives.append(launch_assignment_schema(self.resources))
        if any((value.get('native_macs2_peak') for value in self.resources.values())):
            from gene_annotation_episode.episodic_workflow.root.library.macs2_peak_request_binding import launch_assignment_schema
            alternatives.append(launch_assignment_schema(self.resources))
        if any((value.get('native_lumpy') for value in self.resources.values())):
            from gene_annotation_episode.episodic_workflow.root.library.lumpy_request_binding import launch_assignment_schema
            alternatives.append(launch_assignment_schema(self.resources))
        return {'anyOf': alternatives} if len(alternatives) > 1 else schema
        alternatives = [self._request_schema(key, selected=True, internal=internal) for key, config in self.resources.items() if KINDS[config['kind']] == {'launch_api': 'api', 'launch_local': 'local', 'launch_hpc': 'hpc'}['launch']]
        return {'anyOf': alternatives} if alternatives else {'not': {}}
