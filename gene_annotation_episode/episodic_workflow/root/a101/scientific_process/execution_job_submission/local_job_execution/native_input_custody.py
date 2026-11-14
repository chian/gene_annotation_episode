"""Private A101 launch_local native input custody."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a101.execution_contracts import canonical
from .execution_contracts import NATIVE_SELECTOR_SCHEMA, checked, confined, is_file_source_selector, is_native_blast_database_target, is_native_blast_masking_target, is_native_blast_target, is_native_blast_utility_target, is_native_hmmer_preparation_target, is_native_hmmer_target, is_standard_blast_database_target, json, plain

class NativeInputCustody:

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
        from gene_annotation_episode.episodic_workflow.root.a101.library.sequence_masking_result_views import IDENTIFIER_NAMESPACES
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
        from gene_annotation_episode.episodic_workflow.root.a101.library.blast_utility_result_views import IDENTIFIER_NAMESPACES
        if self.native_blast_utility_results.applies(context):
            resolved = self.native_blast_utility_results.resolve(context, reference, namespace)
        else:
            resolved = self.native_blast_utility_returns.resolve_received(context, reference, namespace)
        if resolved:
            return True
        return False if namespace in IDENTIFIER_NAMESPACES else None

    def _versions(self, versions, scope, *, context, atac_assignments=(), nmf_assignments=(),
                  fluorescence_assignments=(), flux_balance_assignments=(), macs2_peak_assignments=(),
                  lumpy_assignments=()):
        from gene_annotation_episode.episodic_workflow.root.a101.execution_input_versions import validate_execution_input_versions
        return validate_execution_input_versions(self, versions, scope, context=context,
            atac_assignments=atac_assignments, nmf_assignments=nmf_assignments,
            fluorescence_assignments=fluorescence_assignments,
            flux_balance_assignments=flux_balance_assignments, macs2_peak_assignments=macs2_peak_assignments,
            lumpy_assignments=lumpy_assignments)

    def _recorded_results_assignment(self, parent, selected, scope, operation_key):
        """Restore a successfully returned original Results commission only."""
        from gene_annotation_episode.episodic_workflow.root.a101.episode_receipts import EpisodeReceipts
        from gene_annotation_episode.episodic_workflow.root.a101.episode_return_records import EpisodeReturnRecords
        inheritance = parent.request.get('message', {}).get('knowledge_inheritance')
        if inheritance is None:
            return None
        try:
            manifest = EpisodeReceipts.read_manifest(self.store.db, self.run_id, parent.episode_id)
        except ValueError as error:
            if str(error) == 'episode_receipts_not_bound':
                return None
            raise ValueError('recorded_results_receipt_history_invalid') from error
        proof = EpisodeReturnRecords(self.store, self.run_id, failure_prefix='recorded_results_')
        proof.authenticate(parent)
        proof._require(proof._equal(inheritance, manifest), 'receipt_context_conflict')
        proof._require(isinstance(operation_key, str), 'operation_required')
        index = proof._admission_index(parent, operation_key + ':typed_form')
        attempt = self.store.db.execute('SELECT child_episode_id,contract,form,failure FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? AND decision_index=?', (self.run_id, parent.episode_id, index)).fetchone()
        if attempt is None or attempt['form'] is None or attempt['failure'] is not None:
            return None
        try:
            form, contract = (json.loads(attempt['form']), json.loads(attempt['contract']))
            schema = contract['measurements']['schema']
        except (ValueError, TypeError, KeyError) as error:
            raise ValueError('recorded_results_original_return_invalid') from error
        if proof.recorded_admission_references(parent, form, schema, index) is None:
            return None
        child = proof.context(attempt['child_episode_id'])
        proof._require(child.role == 'results' and child.path[:-1] == parent.path and (child.path[-1] == ('results', 'child_' + str(index))), 'original_child_conflict')
        state = self.store.db.execute('SELECT state FROM runtime_episodes WHERE run_id=? AND episode_id=?', (self.run_id, child.episode_id)).fetchone()
        if state['state'] != 'yielded':
            return None
        action = self.store.db.execute('SELECT action FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?', (self.run_id, parent.episode_id, index)).fetchone()
        original = json.loads(action['action'])
        proof._require(original.get('kind') == 'episode_child' and original.get('role') == 'results', 'original_selection_conflict')
        proof._require(proof._equal(selected, original.get('assignment')) and proof._equal(selected, child.assignment), 'assignment_conflict')
        proof._require(proof._equal(scope, original.get('scope')) and proof._equal(scope, child.scope), 'scope_conflict')
        return plain(child.assignment)

    def _selector(self, assignment, target):
        if is_file_source_selector(assignment.get('selector')):
            return self.local_file_sources.selector(assignment, target)
        if self._masking_selector(assignment) or is_native_blast_masking_target(target):
            if not is_native_blast_masking_target(target) or target.get('resource_kind') != 'local':
                raise ValueError('native_blast_masking_result_target_conflict')
            from gene_annotation_episode.episodic_workflow.root.a101.library.sequence_masking_result_views import validate_masking_result_selector
            return validate_masking_result_selector(assignment['selector'], operation=target['assignment']['requested_job']['native_blast_masking']['operation'])
        if self._utility_selector(assignment) or is_native_blast_utility_target(target):
            if not is_native_blast_utility_target(target) or target.get('resource_kind') != 'local':
                raise ValueError('native_blast_utility_result_target_conflict')
            from gene_annotation_episode.episodic_workflow.root.a101.library.blast_utility_result_views import validate_blast_utility_result_selector
            return validate_blast_utility_result_selector(assignment['selector'], operation=target['assignment']['requested_job']['native_blast_utility']['operation'])
        if target['resource_kind'] == 'api':
            return self.api_execution.validate_result_selector(target, assignment['selector'])
        if is_standard_blast_database_target(target):
            if self.native_blast_standard_database_results is None:
                raise ValueError('native_blast_standard_database_results_binding_unavailable')
            from gene_annotation_episode.episodic_workflow.root.a101.library.native_blast_standard_database_result_views import validate_standard_blast_database_selector
            return validate_standard_blast_database_selector(assignment['selector'], program=target['assignment']['requested_job']['native_blast_standard_database']['program'])
        if is_native_blast_database_target(target):
            if self.native_blast_database_results is None:
                raise ValueError('native_blast_database_results_binding_unavailable')
            from gene_annotation_episode.episodic_workflow.root.a101.library.native_blast_database_result_views import validate_native_blast_database_result_selector
            return validate_native_blast_database_result_selector(assignment['selector'], program=target['assignment']['requested_job']['native_blast_database']['program'])
        if is_native_hmmer_preparation_target(target):
            if self.native_hmmer_preparation_results is None:
                raise ValueError('native_hmmer_preparation_results_binding_unavailable')
            from gene_annotation_episode.episodic_workflow.root.a101.library.hmmer_preparation_result_views import validate_preparation_result_selector
            job = target['assignment']['requested_job']['native_hmmer_preparation']
            return validate_preparation_result_selector(assignment['selector'], program=job['program'], mode=job['mode'])
        if is_native_hmmer_target(target):
            from gene_annotation_episode.episodic_workflow.root.a101.library.hmmer_native_result_views import validate_native_hmmer_result_selector
            return validate_native_hmmer_result_selector(assignment['selector'], program=target['assignment']['requested_job']['native_hmmer']['program'])
        if is_native_blast_target(target):
            if self.native_blast_results is None:
                raise ValueError('native_blast_results_binding_unavailable')
            from gene_annotation_episode.episodic_workflow.root.a101.library.blast_pairwise_result_views import validate_native_blast_result_selector
            return validate_native_blast_result_selector(assignment['selector'], program=target['assignment']['requested_job']['native_blast']['program'])
        value = checked(assignment['selector'], NATIVE_SELECTOR_SCHEMA, 'invalid_execution_native_selector')
        paths = list(value.get('paths', []))
        if 'path' in value:
            if value['path'] in paths:
                raise ValueError('ambiguous_execution_results_selector')
            paths.append(value['path'])
        if not paths or (('offset' in value or 'limit' in value) and 'path' not in value):
            raise ValueError('execution_results_paths_required')
        for path in paths:
            confined(path, target['assignment']['workspace'])
        return value

    def _protein_reference_access(self, context, reference, namespace):
        """Classify before ordinary resolution; a protected denial cannot fall through."""
        if (isinstance(reference, str) and reference.startswith('protein_structure_result_receipt:')
                or isinstance(namespace, str) and namespace.startswith('protein_structure_')):
            return False
        if namespace in {'execution', 'execution_handle'}:
            return None  # Runtime handles are resolved by their durable service, not Store.
        try:
            record = self.store.get(reference)
        except (ValueError, KeyError):
            return None
        if record['record_type'] in {'feature', 'product'}:
            from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.protein_structure_operands import is_protein_structure_sequence_operand
            if is_protein_structure_sequence_operand(self.store, reference):
                # A descriptor authorizes its exact original sequence reference.
                # A derived wrapper cannot borrow that permission.
                return False
        if self.native_protein_structure_results.owns_reference(reference):
            return self.native_protein_structure_returns.resolve_received(context, reference, namespace)
        return None

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
            if (selector.get('mode') == 'saved_sheet_recalculation' and isinstance(supplied, dict)
                    and reference in [supplied['sheet']['artifact_ref'],
                        *(row['file']['artifact_ref'] for row in supplied['tables'])]):
                self.atac_returns.authenticate_received_saved_bundle(context, supplied)
                return True
        return self.atac_returns.resolve_received(context, reference, namespace)

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
            if (selector.get('mode') == 'saved_sheet_recalculation' and isinstance(supplied, dict)
                    and any(file.get('artifact_ref') == reference
                        for file in [supplied['sheet'], *supplied['tables']])):
                self.native_chromatin_interaction_returns.authenticate_received_saved_bundle(context, supplied)
                return True
        return self.native_chromatin_interaction_returns.resolve_received(context, reference, namespace)

    def _flux_balance_reference_access(self, context, reference, namespace):
        if (self.native_flux_balance_returns is not None
                and self.native_flux_balance_returns.ordinary_backend is not None
                and context.role in {'annotation', 'scientific_process'}
                and namespace in {None, 'artifact'}
                and self.native_flux_balance_returns.resolve_received(context, reference, namespace)):
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
            if (selector.get('mode') == 'saved_sheet_recalculation' and isinstance(supplied, dict)
                    and supplied.get('artifact_ref') == reference):
                self.native_flux_balance_returns.authenticate_received_saved_sheet(context, supplied)
                return True
        return self.native_flux_balance_returns.resolve_received(context, reference, namespace)

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
            if (selector.get('mode') == 'saved_sheet_recalculation' and isinstance(supplied, dict)
                    and supplied.get('artifact_ref') == reference):
                self.native_fluorescence_returns.authenticate_received_saved_sheet(context, supplied)
                return True
        return self.native_fluorescence_returns.resolve_received(context, reference, namespace)

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
            if (selector.get('mode') == 'saved_sheet_recalculation' and isinstance(supplied, dict)
                    and supplied.get('artifact_ref') == reference):
                self.native_expression_nmf_returns.authenticate_received_saved_sheet(context, supplied)
                return True
        return self.native_expression_nmf_returns.resolve_received(context, reference, namespace)

    def _atac_inputs(self, context, assignment):
        if 'native_atac_differential' not in assignment.get('requested_job', {}):
            return []
        from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.atac_differential_operands import validate_atac_job_inputs
        return validate_atac_job_inputs(self.store, context, assignment,
            reference_access=self.resolve_received_reference)

    def _macs2_peak_inputs(self, context, assignment):
        if 'native_macs2_peak' not in assignment.get('requested_job', {}):
            return []
        from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.received_native_file_inputs import validate_macs2_peak_job_inputs
        return validate_macs2_peak_job_inputs(self.store, context, assignment,
            reference_access=self.resolve_received_reference)

    def _lumpy_inputs(self, context, assignment):
        if 'native_lumpy' not in assignment.get('requested_job', {}):
            return []
        from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.lumpy_request_binding import validate_lumpy_job_inputs
        return validate_lumpy_job_inputs(self.store, context, assignment,
            reference_access=self.resolve_received_reference)

    def _expression_nmf_inputs(self, context, assignment):
        if 'native_expression_nmf' not in assignment.get('requested_job', {}):
            return []
        from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.expression_nmf_operands import validate_expression_nmf_job_inputs
        return validate_expression_nmf_job_inputs(self.store, context, assignment,
            reference_access=self.resolve_received_reference)

    def _fluorescence_inputs(self, context, assignment):
        if 'native_fluorescence' not in assignment.get('requested_job', {}):
            return []
        from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.fluorescence_operands import validate_fluorescence_job_inputs
        return validate_fluorescence_job_inputs(self.store, context, assignment,
            reference_access=self.resolve_received_reference)

    def _matches_flux_balance_assignment(self, context, assignment):
        from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.flux_balance_request_binding import is_compact_assignment, materialized_assignment
        original = (materialized_assignment(self.store, context)
            if is_compact_assignment(plain(context.assignment)) else plain(context.assignment))
        return canonical(original) == canonical(assignment)

