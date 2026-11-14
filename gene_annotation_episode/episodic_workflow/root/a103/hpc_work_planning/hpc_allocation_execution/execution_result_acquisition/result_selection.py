"""Private A103 Results result selection."""
from __future__ import annotations
from .execution_contracts import BLAST_GRADED_REQUEST_VERSION, NATIVE_SELECTOR_SCHEMA, RESULTS_SCHEMA, ROLE_KINDS, canonical, checked, confined, hashlib, is_file_source_selector, is_native_blast_database_target, is_native_blast_masking_target, is_native_blast_target, is_native_blast_utility_target, is_native_hmmer_preparation_target, is_native_hmmer_target, is_standard_blast_database_target, json, plain

class ResultsResultSelection:

    def _target(self, context):
        assignment = checked(context.assignment, RESULTS_SCHEMA, 'invalid_execution_results_assignment')
        masking = self._retained_masking_target(context, assignment, context.scope)
        if masking is not None:
            return masking
        utility = self._retained_utility_target(context, assignment, context.scope)
        if utility is not None:
            return utility
        return self.job_progress_provider.targets.read_target(assignment['handoff_ref'], context.scope)

    def _selector(self, assignment, target):
        if is_file_source_selector(assignment.get('selector')):
            return self.local_file_sources.selector(assignment, target)
        if self._masking_selector(assignment) or is_native_blast_masking_target(target):
            if not is_native_blast_masking_target(target) or target.get('resource_kind') != 'local':
                raise ValueError('native_blast_masking_result_target_conflict')
            from gene_annotation_episode.episodic_workflow.root.a103.sequence_masking_result_views import validate_masking_result_selector
            return validate_masking_result_selector(assignment['selector'], operation=target['assignment']['requested_job']['native_blast_masking']['operation'])
        if self._utility_selector(assignment) or is_native_blast_utility_target(target):
            if not is_native_blast_utility_target(target) or target.get('resource_kind') != 'local':
                raise ValueError('native_blast_utility_result_target_conflict')
            from gene_annotation_episode.episodic_workflow.root.a103.blast_utility_result_views import validate_blast_utility_result_selector
            return validate_blast_utility_result_selector(assignment['selector'], operation=target['assignment']['requested_job']['native_blast_utility']['operation'])
        if target['resource_kind'] == 'api':
            return self.api_execution.validate_result_selector(target, assignment['selector'])
        if is_standard_blast_database_target(target):
            if self.native_blast_standard_database_results is None:
                raise ValueError('native_blast_standard_database_results_binding_unavailable')
            from gene_annotation_episode.episodic_workflow.root.a103.native_blast_standard_database_result_views import validate_standard_blast_database_selector
            return validate_standard_blast_database_selector(assignment['selector'], program=target['assignment']['requested_job']['native_blast_standard_database']['program'])
        if is_native_blast_database_target(target):
            if self.native_blast_database_results is None:
                raise ValueError('native_blast_database_results_binding_unavailable')
            from gene_annotation_episode.episodic_workflow.root.a103.native_blast_database_result_views import validate_native_blast_database_result_selector
            return validate_native_blast_database_result_selector(assignment['selector'], program=target['assignment']['requested_job']['native_blast_database']['program'])
        if is_native_hmmer_preparation_target(target):
            if self.native_hmmer_preparation_results is None:
                raise ValueError('native_hmmer_preparation_results_binding_unavailable')
            from gene_annotation_episode.episodic_workflow.root.a103.hmmer_preparation_result_views import validate_preparation_result_selector
            job = target['assignment']['requested_job']['native_hmmer_preparation']
            return validate_preparation_result_selector(assignment['selector'], program=job['program'], mode=job['mode'])
        if is_native_hmmer_target(target):
            from gene_annotation_episode.episodic_workflow.root.a103.hmmer_native_result_views import validate_native_hmmer_result_selector
            return validate_native_hmmer_result_selector(assignment['selector'], program=target['assignment']['requested_job']['native_hmmer']['program'])
        if is_native_blast_target(target):
            if self.native_blast_results is None:
                raise ValueError('native_blast_results_binding_unavailable')
            from gene_annotation_episode.episodic_workflow.root.a103.blast_pairwise_result_views import validate_native_blast_result_selector
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

    def _windows(self, selector):
        values = {path: (0, None) for path in selector.get('paths', [])}
        if 'path' in selector:
            values[selector['path']] = (selector.get('offset', 0), selector.get('limit'))
        return values

    def _selection(self, context, supplied=None):
        if supplied is None and self.services is not None:
            callback = getattr(self.services, 'record_selection', None)
            supplied = None if callback is None else callback(context)
        if supplied is None:
            from gene_annotation_episode.episodic_workflow.root.a103.episode_receipts import EpisodeReceipts
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
            launch = self._launch(plain(context.assignment), scope=context.scope)
            selected = target['assignment']
            resource_id = target['resource_id']
            request = launch['requests'].get(resource_id)
            if request is not None and request.get('version') == BLAST_GRADED_REQUEST_VERSION:
                self._validate_blast_launch_selection(launch, selected, context.scope)
                handoff = self.api_execution._read_handoff(target['handle'], plain(context.scope))
                subject_ref = selected['request']['subject_ref']
                sequence = self.tool_registry._sequence(subject_ref, molecule_model=self.store.subject_molecule(subject_ref))
                expected = hashlib.sha256(f'>{subject_ref}\n{sequence}'.encode()).hexdigest()
                if handoff['snapshot']['request'].get('query_sha256') != expected:
                    raise ValueError('blast_grader_submitted_query_conflict')
        elif context.role in ROLE_KINDS:
            if canonical(target['assignment']) != canonical(context.assignment):
                raise ValueError('execution_handoff_assignment_conflict')
        elif context.role == 'results' and target != self._target(context):
            raise ValueError('execution_result_target_conflict')
        return target
