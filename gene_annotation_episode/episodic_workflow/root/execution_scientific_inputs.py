"""Complete original execution scientific inputs responsibility."""
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

class ExecutionScientificInputs:
    def _protein_reference_access(self, context, reference, namespace):
        """Classify before ordinary resolution; a protected denial cannot fall through."""
        if isinstance(reference, str) and reference.startswith('protein_structure_result_receipt:') or (isinstance(namespace, str) and namespace.startswith('protein_structure_')):
            return False
        if namespace in {'execution', 'execution_handle'}:
            return None
        try:
            record = self.store.get(reference)
        except (ValueError, KeyError):
            return None
        if record['record_type'] in {'feature', 'product'}:
            from gene_annotation_episode.episodic_workflow.root.protein_structure_operands import is_protein_structure_sequence_operand
            if is_protein_structure_sequence_operand(self.store, reference):
                return False
        if self.native_protein_structure_results.owns_reference(reference):
            return self.native_protein_structure_returns.resolve_received(context, reference, namespace)
        return None

    def _genomic_overlap_reference_access(self, context, reference, namespace):
        host = self.native_genomic_overlap_results
        if host is None or not host.owns_reference(reference):
            return None
        if namespace not in {None, 'artifact'}:
            return False
        if host.applies(context):
            if host.resolve_own(context, reference, namespace):
                return True
            selector = plain(context.assignment)['selector']
            supplied = selector.get('saved_sheet_file')
            if selector.get('mode') == 'saved_sheet_recalculation' and isinstance(supplied, dict) and (supplied.get('artifact_ref') == reference):
                self.native_genomic_overlap_returns.authenticate_received_saved_sheet(context, supplied)
                return True
        return self.native_genomic_overlap_returns.resolve_received(context, reference, namespace)

    def _fluorescence_reference_access(self, context, reference, namespace):
        host = self.native_fluorescence_results
        if not host.owns_reference(reference):
            return None
        if namespace not in {None, 'artifact'}:
            return False
        if host.applies(context):
            if host.resolve_own(context, reference, namespace):
                return True
            selector = plain(context.assignment)['selector']
            supplied = selector.get('saved_sheet_file')
            if selector.get('mode') == 'saved_sheet_recalculation' and isinstance(supplied, dict) and (supplied.get('artifact_ref') == reference):
                self.native_fluorescence_returns.authenticate_received_saved_sheet(context, supplied)
                return True
        return self.native_fluorescence_returns.resolve_received(context, reference, namespace)

    @staticmethod
    def _fluorescence_selector(assignment):
        return assignment.get('selector', {}).get('version') == 'fluorescence_result_selector_v1'

    def _retained_fluorescence_target(self, context, assignment, scope):
        if not self._fluorescence_selector(assignment):
            return None
        if context.role == 'results':
            from gene_annotation_episode.episodic_workflow.root.library.fluorescence_result_contracts import validate_fluorescence_selector
            from gene_annotation_episode.episodic_workflow.root.library.fluorescence_return_views import CONTEXT_SOURCE, requested_fluorescence_sources
            selector = validate_fluorescence_selector(assignment['selector'])
            schema = plain(context.request)['report_contract']['measurements']['schema']
            if bool(selector['context_fields']) != (CONTEXT_SOURCE in requested_fluorescence_sources(schema)):
                raise ValueError('fluorescence_context_selection_mismatch')
        return self.native_fluorescence_results.retained_target(context, assignment, scope)

    def _fluorescence_inputs(self, context, assignment):
        if 'native_fluorescence' not in assignment.get('requested_job', {}):
            return []
        from gene_annotation_episode.episodic_workflow.root.library.fluorescence_operands import validate_fluorescence_job_inputs
        return validate_fluorescence_job_inputs(self.store, context, assignment, reference_access=self.resolve_received_reference)

    def _expression_nmf_reference_access(self, context, reference, namespace):
        host = self.native_expression_nmf_results
        if host is None or not host.owns_reference(reference):
            return None
        if namespace not in {None, 'artifact'}:
            return False
        if host.applies(context):
            if host.resolve_own(context, reference, namespace):
                return True
            selector = plain(context.assignment)['selector']
            supplied = selector.get('saved_sheet_file')
            if selector.get('mode') == 'saved_sheet_recalculation' and isinstance(supplied, dict) and (supplied.get('artifact_ref') == reference):
                self.native_expression_nmf_returns.authenticate_received_saved_sheet(context, supplied)
                return True
        return self.native_expression_nmf_returns.resolve_received(context, reference, namespace)

    def _flux_balance_reference_access(self, context, reference, namespace):
        if self.native_flux_balance_returns is not None and self.native_flux_balance_returns.ordinary_backend is not None and (context.role in {'annotation', 'scientific_process'}) and (namespace in {None, 'artifact'}) and self.native_flux_balance_returns.resolve_received(context, reference, namespace):
            return True
        host = self.native_flux_balance_results
        if host is None or not host.owns_reference(reference):
            return None
        if namespace not in {None, 'artifact'}:
            return False
        if host.applies(context):
            if host.resolve_own(context, reference, namespace):
                return True
            selector = plain(context.assignment)['selector']
            supplied = selector.get('saved_sheet_file')
            if selector.get('mode') == 'saved_sheet_recalculation' and isinstance(supplied, dict) and (supplied.get('artifact_ref') == reference):
                self.native_flux_balance_returns.authenticate_received_saved_sheet(context, supplied)
                return True
        return self.native_flux_balance_returns.resolve_received(context, reference, namespace)

    @staticmethod
    def _flux_balance_selector(assignment):
        return assignment.get('selector', {}).get('version') == 'flux_balance_result_selector_v1'

    def _retained_flux_balance_target(self, context, assignment, scope):
        if not self._flux_balance_selector(assignment):
            return None
        if self.native_flux_balance_results is None:
            raise ValueError('native_flux_balance_results_binding_unavailable')
        return self.native_flux_balance_results.retained_target(context, assignment, scope)

    @staticmethod
    def _expression_nmf_selector(assignment):
        return assignment.get('selector', {}).get('version') == 'expression_nmf_result_selector_v1'

    def _retained_expression_nmf_target(self, context, assignment, scope):
        if not self._expression_nmf_selector(assignment):
            return None
        if self.native_expression_nmf_results is None:
            raise ValueError('native_expression_nmf_results_binding_unavailable')
        return self.native_expression_nmf_results.retained_target(context, assignment, scope)

    def _atac_reference_access(self, context, reference, namespace):
        host = self.atac_results
        if host is None or not host.owns_reference(reference):
            return None
        if namespace not in {None, 'artifact'}:
            return False
        if host.applies(context):
            if host.resolve_own(context, reference, namespace):
                return True
            selector = plain(context.assignment)['selector']
            supplied = selector.get('saved_sheet_bundle')
            if selector.get('mode') == 'saved_sheet_recalculation' and isinstance(supplied, dict) and (reference in [supplied['sheet']['artifact_ref'], *(row['file']['artifact_ref'] for row in supplied['tables'])]):
                self.atac_returns.authenticate_received_saved_bundle(context, supplied)
                return True
        return self.atac_returns.resolve_received(context, reference, namespace)

    @staticmethod
    def _atac_selector(assignment):
        return assignment.get('selector', {}).get('version') == 'atac_differential_result_selector_v1'

    def _retained_atac_target(self, context, assignment, scope):
        if not self._atac_selector(assignment):
            return None
        if self.atac_results is None:
            raise ValueError('native_atac_results_binding_unavailable')
        return self.atac_results.retained_target(context, assignment, scope)

    def _macs2_peak_inputs(self, context, assignment):
        if 'native_macs2_peak' not in assignment.get('requested_job', {}):
            return []
        from gene_annotation_episode.episodic_workflow.root.received_native_file_inputs import validate_macs2_peak_job_inputs
        return validate_macs2_peak_job_inputs(self.store, context, assignment, reference_access=self.resolve_received_reference)

    def _lumpy_inputs(self, context, assignment):
        if 'native_lumpy' not in assignment.get('requested_job', {}):
            return []
        from gene_annotation_episode.episodic_workflow.root.library.lumpy_request_binding import validate_lumpy_job_inputs
        return validate_lumpy_job_inputs(self.store, context, assignment, reference_access=self.resolve_received_reference)

    def read_macs2_peak_capture_selection(self, context, capture_source_refs, *, before_decision_index=None):
        """Read explicitly received generic captures against their original MACS2 seal.

            Current delivery authenticates before private custody or seal bytes.
            Original target/start controls are retained records; this read never
            consults the original workspace, input bytes or installed software.
            Generic capture provenance is preserved, and an unselected sibling in
            a wrapper does not become a received File or Source.
            """
        from gene_annotation_episode.episodic_workflow.root.episode_return_records import EpisodeReturnRecords
        from gene_annotation_episode.episodic_workflow.root.episode_bindings import BindingContext
        from gene_annotation_episode.episodic_workflow.root.local_file_capture_results import FILE_PROVIDER, RESULT_PROVIDER, RECEIPT_VERSION
        from gene_annotation_episode.native_file_capture import NativeFileCaptureError, retained_native_file
        from gene_annotation_episode.episodic_workflow.root.library.native_macs2_peak_execution import POLICY, macs2_peak_plan, validate_macs2_peak_seal, validate_macs2_peak_original_controls
        from gene_annotation_episode.episodic_workflow.root.library.native_atac_differential_driver import decode_json
        from gene_annotation_episode.episodic_workflow.root.received_native_file_inputs import received_file_context

        def require(condition, code):
            if not condition:
                raise ValueError('macs2_peak_capture_' + code)
        require(isinstance(context, BindingContext) and context.run_id == self.run_id, 'context_conflict')
        require(type(capture_source_refs) in (list, tuple) and bool(capture_source_refs) and all((type(ref) is str for ref in capture_source_refs)) and (len(set(capture_source_refs)) == len(capture_source_refs)), 'source_selection_invalid')
        require(before_decision_index is None or (type(before_decision_index) is int and before_decision_index >= 0), 'cutoff_invalid')
        known, _ = received_file_context(self.store, context, failure_prefix='macs2_peak_capture_', baseline=False)
        records = EpisodeReturnRecords(self.store, self.run_id, failure_prefix='macs2_peak_capture_')
        selected = []
        for reference in capture_source_refs:
            require(reference in known and (before_decision_index is None or records._received_before(context.episode_id, reference, before_decision_index)), 'source_not_received')
            source = self.store.get(reference)
            require(source.get('record_type') == 'source' and source.get('origin') == 'tool' and (source.get('provider') == FILE_PROVIDER or (source.get('provider') == RESULT_PROVIDER and source.get('version') == RECEIPT_VERSION)), 'source_selection_invalid')
            selected.append((reference, source['provider']))
        plan, source_roles, unavailable_paths = (None, {}, set())
        for reference, provider in selected:
            if provider == FILE_PROVIDER:
                captured = self.local_file_sources.read_source(reference, context.scope)
                require(captured is not None, 'source_receipt_missing')
                target, observation = (captured['target'], captured['observation'])
            else:
                captured = self.local_file_sources.read_wrapper(reference, context.scope)
                require(captured is not None, 'wrapper_receipt_missing')
                target, observation = (captured['target'], captured['observation'])
            require(target['resource_kind'] == 'local' and 'native_macs2_peak' in target['assignment']['requested_job'], 'producer_target_conflict')
            authenticated, original = self.job_progress_provider.targets._native(target['handle'], context.scope)
            require(canonical(authenticated) == canonical(target), 'producer_target_conflict')
            detail = original['receipt']['outcome'].get('native_outcome') or {}
            original_plan = validate_macs2_peak_original_controls(detail.get('native_macs2_peak_plan'), detail.get('native_macs2_peak_handle'), detail.get('native_macs2_peak_request_raw'))
            rebuilt = macs2_peak_plan(target['assignment'], original_plan['identity'], policy=POLICY)
            require(canonical(rebuilt) == canonical(original_plan), 'original_plan_conflict')
            native = observation.get('native', {})
            require(native.get('terminal') is True and native.get('quiescent') is True and (native.get('execution_id') == target['execution_id']) and (native.get('metadata', {}).get('policy') == POLICY), 'original_observation_conflict')
            observed_plan = validate_macs2_peak_original_controls(native.get('native_macs2_peak_plan'), native.get('native_macs2_peak_handle'), native.get('native_macs2_peak_request_raw'))
            require(canonical(observed_plan) == canonical(original_plan) and all((canonical(native.get(key)) == canonical(detail.get(key)) for key in ('native_macs2_peak_handle', 'native_macs2_peak_request_raw'))), 'original_observation_conflict')
            if plan is None:
                plan = original_plan
            else:
                require(canonical(plan) == canonical(original_plan), 'mixed_producer_selection')
            paths = {str(Path(plan['attempt_directory']) / row['relative_path']): row for row in plan['outputs']}
            if provider == FILE_PROVIDER:
                spec = paths.get(captured['resolved_path'])
                require(spec is not None and captured['file'] is not None and (captured['selection']['format'] == spec['format']) and (captured['file']['format'] == spec['format']), 'output_role_conflict')
                require(spec['role'] not in source_roles, 'duplicate_output_role')
                source_roles[spec['role']] = {'source_ref': reference, 'file': deepcopy(captured['file'])}
            else:
                for row in captured['captured_files']:
                    path = row['resolved_path']
                    spec = paths.get(path)
                    if spec is not None and row['file'] is None:
                        require(row['selection']['format'] == spec['format'], 'output_role_conflict')
                        unavailable_paths.add(path)
        require(plan is not None, 'original_plan_required')
        roles = []
        for spec in plan['outputs']:
            supplied = source_roles.get(spec['role'])
            path = str(Path(plan['attempt_directory']) / spec['relative_path'])
            roles.append({'specification': deepcopy(spec), 'source_ref': None if supplied is None else supplied['source_ref'], 'file': None if supplied is None else supplied['file'], 'availability': 'retained' if supplied is not None else 'unavailable' if path in unavailable_paths else 'not_selected', 'qualification': None if supplied is not None else {'code': 'selected_output_unavailable' if path in unavailable_paths else 'output_not_selected'}})
        seal_role = next((row for row in roles if row['specification']['role'] == 'seal'))
        seal = None
        if seal_role['file'] is not None:
            try:
                raw = retained_native_file(self.store, seal_role['file']).read_bytes()
            except NativeFileCaptureError as error:
                if error.code not in {'retained_artifact_unavailable', 'retained_artifact_mismatch'}:
                    raise
                seal_role.update(availability='unavailable', qualification={'code': error.code})
            else:
                seal = validate_macs2_peak_seal(decode_json(raw), plan=plan)
        if seal is None:
            for role in roles:
                if role['specification']['role'] != 'seal':
                    role['qualification'] = {'code': 'producer_seal_unavailable' if seal_role['source_ref'] is not None else 'producer_seal_not_received'}
        else:
            declarations = {row['specification']['role']: row['declaration'] for row in seal['outputs']}
            for role in roles:
                if role['specification']['role'] == 'seal':
                    continue
                declared = declarations[role['specification']['role']]
                file = role['file']
                if file is not None:
                    if declared['state'] != 'present' or file['sha256'] != declared['sha256'] or file['size_bytes'] != declared['size_bytes']:
                        role.update(availability='unavailable', qualification={'code': 'native_output_identity_conflict'})
                elif declared['state'] == 'absent':
                    role.update(availability='unavailable', qualification={'code': 'native_output_absent'})
        return {'plan': deepcopy(plan), 'seal': deepcopy(seal), 'roles': roles}

    def _atac_inputs(self, context, assignment):
        if 'native_atac_differential' not in assignment.get('requested_job', {}):
            return []
        from gene_annotation_episode.episodic_workflow.root.atac_differential_operands import validate_atac_job_inputs
        return validate_atac_job_inputs(self.store, context, assignment, reference_access=self.resolve_received_reference)

    def _chromatin_reference_access(self, context, reference, namespace):
        host = self.native_chromatin_interaction_results
        if host is None or not host.owns_reference(reference):
            return None
        if namespace not in {None, 'artifact'}:
            return False
        if host.applies(context):
            if host.resolve_own(context, reference, namespace):
                return True
            selector = plain(context.assignment)['selector']
            supplied = selector.get('saved_sheet_bundle')
            if selector.get('mode') == 'saved_sheet_recalculation' and isinstance(supplied, dict) and any((file.get('artifact_ref') == reference for file in [supplied['sheet'], *supplied['tables']])):
                self.native_chromatin_interaction_returns.authenticate_received_saved_bundle(context, supplied)
                return True
        return self.native_chromatin_interaction_returns.resolve_received(context, reference, namespace)

    @staticmethod
    def _chromatin_selector(assignment):
        return assignment.get('selector', {}).get('version') == 'chromatin_interaction_result_selector_v1'

    def _retained_chromatin_target(self, context, assignment, scope):
        if not self._chromatin_selector(assignment):
            return None
        if self.native_chromatin_interaction_results is None:
            raise ValueError('native_chromatin_results_binding_unavailable')
        return self.native_chromatin_interaction_results.retained_target(context, assignment, scope)

    @staticmethod
    def _genomic_overlap_selector(assignment):
        return assignment.get('selector', {}).get('version') == 'genomic_overlap_result_selector_v1'

    def _retained_genomic_overlap_target(self, context, assignment, scope):
        if not self._genomic_overlap_selector(assignment):
            return None
        if self.native_genomic_overlap_results is None:
            raise ValueError('native_genomic_overlap_results_binding_unavailable')
        return self.native_genomic_overlap_results.retained_target(context, assignment, scope)

    @staticmethod
    def _masking_selector(assignment):
        return assignment.get('selector', {}).get('version') == 'native_blast_masking_result_selector_v1'

    def _masking_inputs(self, context, assignment):
        return self.native_blast_masking_results.validate_job_inputs(context, assignment)

    def _retained_masking_target(self, context, assignment, scope):
        if not self._masking_selector(assignment):
            return None
        return self.native_blast_masking_results.retained_target(context, assignment=assignment, scope=scope)

    def _masking_reference_access(self, context, reference, namespace):
        access = self.native_blast_masking_results.retained_reference_access(context, reference, namespace)
        if access is not None:
            return access
        from gene_annotation_episode.episodic_workflow.root.library.sequence_masking_result_views import IDENTIFIER_NAMESPACES
        if self.native_blast_masking_results.applies(context):
            resolved = self.native_blast_masking_results.resolve(context, reference, namespace)
        else:
            resolved = self.native_blast_masking_returns.resolve_received(context, reference, namespace)
        if resolved:
            return True
        return False if namespace in IDENTIFIER_NAMESPACES else None

    @staticmethod
    def _utility_selector(assignment):
        return assignment.get('selector', {}).get('version') in {'native_blast_utility_result_selector_v1', 'native_blast_utility_result_selector_v2'}

    def _utility_inputs(self, context, assignment):
        return self.native_blast_utility_results.validate_job_inputs(context, assignment)

    def _retained_utility_target(self, context, assignment, scope):
        if not self._utility_selector(assignment):
            return None
        return self.native_blast_utility_results.retained_target(context, assignment=assignment, scope=scope)

    def _utility_reference_access(self, context, reference, namespace):
        access = self.native_blast_utility_results.retained_reference_access(context, reference, namespace)
        if access is not None:
            return access
        from gene_annotation_episode.episodic_workflow.root.library.blast_utility_result_views import IDENTIFIER_NAMESPACES
        if self.native_blast_utility_results.applies(context):
            resolved = self.native_blast_utility_results.resolve(context, reference, namespace)
        else:
            resolved = self.native_blast_utility_returns.resolve_received(context, reference, namespace)
        if resolved:
            return True
        return False if namespace in IDENTIFIER_NAMESPACES else None

    def _versions(self, versions, scope, *, context, atac_assignments=(), nmf_assignments=(), fluorescence_assignments=(), flux_balance_assignments=(), macs2_peak_assignments=(), lumpy_assignments=()):
        from gene_annotation_episode.execution_input_versions import validate_execution_input_versions
        return validate_execution_input_versions(self, versions, scope, context=context, atac_assignments=atac_assignments, nmf_assignments=nmf_assignments, fluorescence_assignments=fluorescence_assignments, flux_balance_assignments=flux_balance_assignments, macs2_peak_assignments=macs2_peak_assignments, lumpy_assignments=lumpy_assignments)

    def _expression_nmf_inputs(self, context, assignment):
        if 'native_expression_nmf' not in assignment.get('requested_job', {}):
            return []
        from gene_annotation_episode.episodic_workflow.root.expression_nmf_operands import validate_expression_nmf_job_inputs
        return validate_expression_nmf_job_inputs(self.store, context, assignment, reference_access=self.resolve_received_reference)

    def _flux_balance_inputs(self, context, assignment, *, input_versions=None):
        if 'native_flux_balance' not in assignment.get('requested_job', {}):
            return []
        from gene_annotation_episode.episodic_workflow.root.episode_return_records import EpisodeReturnRecords
        if input_versions is None:
            if context.role == 'launch':
                input_versions = plain(context.assignment)['immutable_input_versions']
            else:
                _, input_versions = self.flux_balance_inputs._original(context)
        frozen = self.flux_balance_inputs.received(context, required=False) if context.role == 'launch_local' and self._matches_flux_balance_assignment(context, assignment) else None
        binding = frozen['receipt']['binding'] if frozen is not None else self.flux_balance_inputs.validate_selected(context, assignment, input_versions=input_versions)
        if not EpisodeReturnRecords._equal(binding['input_versions'], list(input_versions)):
            raise ValueError('flux_balance_execution_input_original_versions_conflict')
        return list(dict.fromkeys((row['reference'] for row in binding['input_versions'])))

    def _matches_flux_balance_assignment(self, context, assignment):
        from gene_annotation_episode.episodic_workflow.root.library.flux_balance_request_binding import is_compact_assignment, materialized_assignment
        original = materialized_assignment(self.store, context) if is_compact_assignment(plain(context.assignment)) else plain(context.assignment)
        return canonical(original) == canonical(assignment)

    def _genomic_overlap_inputs(self, context, assignment):
        if 'native_genomic_overlap' not in assignment.get('requested_job', {}):
            return []
        from gene_annotation_episode.episodic_workflow.root.library.genomic_overlap_operands import validate_genomic_overlap_job_inputs
        return validate_genomic_overlap_job_inputs(self.store, context, assignment, reference_access=self.resolve_received_reference)

    def _chromatin_inputs(self, context, assignment):
        if 'native_chromatin_interactions' not in assignment.get('requested_job', {}):
            return []
        from gene_annotation_episode.episodic_workflow.root.chromatin_interaction_operands import validate_chromatin_job_inputs
        return validate_chromatin_job_inputs(self.store, context, assignment, reference_access=self.resolve_received_reference)

    def _check_parent_inputs(self, context):
        from gene_annotation_episode.episodic_workflow.root.library.lumpy_request_binding import is_compact_assignment as is_lumpy_assignment, read_request_binding as read_lumpy_binding
        if is_lumpy_assignment(plain(context.assignment)):
            control = read_lumpy_binding(self.store, self.run_id, context.episode_id)
            row, = control['requests']
            self._lumpy_inputs(context, row['assignment'])
            self._versions(row['input_versions'], context.scope, context=context, lumpy_assignments=[row['assignment']])
            return
        from gene_annotation_episode.episodic_workflow.root.library.macs2_peak_request_binding import is_compact_assignment as is_macs2_assignment, read_request_binding as read_macs2_binding
        if is_macs2_assignment(plain(context.assignment)):
            control = read_macs2_binding(self.store, self.run_id, context.episode_id)
            row, = control['requests']
            self._macs2_peak_inputs(context, row['assignment'])
            self._versions(row['input_versions'], context.scope, context=context, macs2_peak_assignments=[row['assignment']])
            return
        from gene_annotation_episode.episodic_workflow.root.library.flux_balance_request_binding import is_compact_assignment, read_request_binding
        if is_compact_assignment(plain(context.assignment)):
            read_request_binding(self.store, self.run_id, context.episode_id)
            self.flux_balance_inputs.received(context)
            return
        if len(context.path) < 2 or context.path[-2][0] != 'launch':
            return
        row = self.store.db.execute('SELECT request FROM runtime_episodes WHERE run_id=? AND path=?', (self.run_id, canonical(context.path[:-1]))).fetchone()
        if row is not None:
            original = self._launch(json.loads(row['request'])['message']['episode_assignment'])
            if context.role == 'launch_api':
                self._validate_blast_api_parent_request(original, plain(context.assignment), context.scope)
            self._masking_inputs(context, plain(context.assignment))
            self._utility_inputs(context, plain(context.assignment))
            self._fluorescence_inputs(context, plain(context.assignment))
            self._expression_nmf_inputs(context, plain(context.assignment))
            self._flux_balance_inputs(context, plain(context.assignment), input_versions=original['immutable_input_versions'])
            self._macs2_peak_inputs(context, plain(context.assignment))
            self._lumpy_inputs(context, plain(context.assignment))
            self._atac_inputs(context, plain(context.assignment))
            self._chromatin_inputs(context, plain(context.assignment))
            self._genomic_overlap_inputs(context, plain(context.assignment))
            from gene_annotation_episode.episodic_workflow.root.protein_structure_operands import validate_protein_structure_job_inputs
            validate_protein_structure_job_inputs(self.store, context, plain(context.assignment), returns=self.native_protein_structure_returns)
            self._versions(original['immutable_input_versions'], context.scope, context=context, macs2_peak_assignments=[plain(context.assignment)], lumpy_assignments=[plain(context.assignment)], atac_assignments=[plain(context.assignment)], nmf_assignments=[plain(context.assignment)], fluorescence_assignments=[plain(context.assignment)], flux_balance_assignments=[plain(context.assignment)])
            from gene_annotation_episode.episodic_workflow.root.library.native_blast_database_result_publication import validate_native_job_inputs
            from gene_annotation_episode.episodic_workflow.root.library.native_blast_standard_database_result_publication import validate_standard_blast_job_inputs
            validate_native_job_inputs(self.store, context, plain(context.assignment))
            validate_standard_blast_job_inputs(self.store, context, plain(context.assignment))
            from gene_annotation_episode.episodic_workflow.root.library.rna_result_operand_authority import validate_rna_structure_job_inputs
            validate_rna_structure_job_inputs(self.store, context, plain(context.assignment))
            return
        raise ValueError('execution_original_launch_assignment_unavailable')
