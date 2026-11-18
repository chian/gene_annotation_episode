"""Private A101 results execution state."""
from __future__ import annotations
from .execution_contracts import BLAST_GRADED_REQUEST_VERSION, BLAST_GRADED_RETURN_SCHEMA, BLAST_GRADED_RETURN_SOURCE, RESULTS_SCHEMA, ROLE_KINDS, canonical, checked, hashlib, json, plain

class OperationalExecutionState:

    def _delegate(self, context):
        assignment = self._validate_request(plain(context.assignment))
        return self.api_execution if context.role == 'launch_api' else self._practical[assignment['resource_id']]

    def _practical_context(self, context):
        return context

    def initialize(self, context):
        self.credit_kind(context.role)
        if self.local_file_sources.applies(context):
            target = self._target(context)
            self.local_file_sources.selector(plain(context.assignment), target, validate_paths=False)
            return self._result_directory(context)
        if 'results' in ROLE_KINDS:
            self._check_parent_inputs(context)
            return self._delegate(context).initialize(context)
        target = self._target(context)
        self._selector(plain(context.assignment), target)
        required = self._blast_target_requirement(target, context.scope)
        if required is not None:
            schema = plain(context.request)['report_contract']['measurements']['schema']
            if not any((node.get('x-source') == BLAST_GRADED_RETURN_SOURCE and node == BLAST_GRADED_RETURN_SCHEMA for node in schema.get('properties', {}).values())):
                raise ValueError('blast_grader_typed_return_required')
        if self._masking_selector(plain(context.assignment)) or self._utility_selector(plain(context.assignment)):
            self.initial_references(context)
        if target['resource_kind'] == 'api':
            return self.api_execution.initialize(context)
        self._result_directory(context)

    def _check_parent_inputs(self, context):
        if len(context.path) < 2 or context.path[-2][0] != 'launch':
            return
        row = self.store.db.execute('SELECT request FROM runtime_episodes WHERE run_id=? AND path=?', (self.run_id, canonical(context.path[:-1]))).fetchone()
        if row is not None:
            original = self._launch(json.loads(row['request'])['message']['episode_assignment'])
            if context.role == 'launch_api':
                pass
            self._masking_inputs(context, plain(context.assignment))
            self._utility_inputs(context, plain(context.assignment))
            self._versions(original['immutable_input_versions'], context.scope, context=context)
            from gene_annotation_episode.episodic_workflow.root.a101.native_blast_database_result_publication import validate_native_job_inputs
            from gene_annotation_episode.episodic_workflow.root.a101.native_blast_standard_database_result_publication import validate_standard_blast_job_inputs
            validate_native_job_inputs(self.store, context, plain(context.assignment))
            validate_standard_blast_job_inputs(self.store, context, plain(context.assignment))
            return
        raise ValueError('execution_original_launch_assignment_unavailable')

    def state(self, context):
        """Expose the original practical state for its original resource role."""
        if context.role not in {'launch_local', 'launch_hpc'}:
            raise ValueError('practical_resource_role_required')
        return self._delegate(context).state(self._practical_context(context))

    def _target(self, context):
        assignment = checked(context.assignment, RESULTS_SCHEMA, 'invalid_execution_results_assignment')
        masking = self._retained_masking_target(context, assignment, context.scope)
        if masking is not None:
            return masking
        utility = self._retained_utility_target(context, assignment, context.scope)
        if utility is not None:
            return utility
        return self.job_progress_provider.targets.read_target(assignment['handoff_ref'], context.scope)

    def _selection(self, context, supplied=None):
        if supplied is None and self.services is not None:
            callback = getattr(self.services, 'record_selection', None)
            supplied = None if callback is None else callback(context)
        if supplied is None:
            from gene_annotation_episode.episodic_workflow.root.a101.episode_receipts import EpisodeReceipts
            table = self.store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='runtime_receipt_inheritance'").fetchone()
            if table and self.store.db.execute('SELECT 1 FROM runtime_receipt_inheritance WHERE run_id=? AND episode_id=?', (self.run_id, context.episode_id)).fetchone():
                receipts = EpisodeReceipts(self.store, self.run_id)
                supplied = {'run_id': self.run_id, 'episode_id': context.episode_id, 'known_record_refs': list(receipts.known(context.episode_id)), 'initial_known_record_refs': list(receipts.known(context.episode_id, baseline=True))}
            else:
                rows = self.store.db.execute('SELECT result FROM runtime_actions WHERE run_id=? AND episode_id=? AND result IS NOT NULL ORDER BY decision_index', (self.run_id, context.episode_id))
                supplied = {'run_id': self.run_id, 'episode_id': context.episode_id, 'known_record_refs': list(dict.fromkeys((ref for row in rows for ref in json.loads(row[0]).get('record_refs', [])))), 'initial_known_record_refs': []}
        supplied = plain(supplied)
        if supplied.get('run_id') != self.run_id or supplied.get('episode_id') != context.episode_id:
            raise ValueError('execution_receiver_identity_conflict')
        for key in ('known_record_refs', 'initial_known_record_refs'):
            if not isinstance(supplied.get(key), list) or any((not isinstance(ref, str) or not ref for ref in supplied[key])):
                raise ValueError('execution_receiver_references_required')
        if not set(supplied['initial_known_record_refs']) <= set(supplied['known_record_refs']):
            raise ValueError('execution_initial_references_must_be_known')
        return supplied

    def _context_target(self, context, target):
        if context.role == 'launch':
            pass
        elif context.role in ROLE_KINDS:
            if canonical(target['assignment']) != canonical(context.assignment):
                raise ValueError('execution_handoff_assignment_conflict')
        elif context.role == 'results' and target != self._target(context):
            raise ValueError('execution_result_target_conflict')
        return target
