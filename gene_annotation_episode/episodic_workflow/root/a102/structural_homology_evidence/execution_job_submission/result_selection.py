"""Private A102 Launch result selection."""
from __future__ import annotations
from .execution_contracts import NATIVE_SELECTOR_SCHEMA, RESULTS_SCHEMA, ROLE_KINDS, canonical, checked, confined, is_file_source_selector, is_native_protein_structure_target, json, plain

class LaunchResultSelection:

    def _target(self, context):
        assignment = checked(context.assignment, RESULTS_SCHEMA, 'invalid_execution_results_assignment')
        retained = self._retained_protein_result(context, assignment, context.scope)
        return retained['body']['intent']['target'] if retained is not None else self.job_progress_provider.targets.read_target(assignment['handoff_ref'], context.scope)

    def _selector(self, assignment, target):
        if is_file_source_selector(assignment.get('selector')):
            return self.local_file_sources.selector(assignment, target)
        if assignment.get('selector', {}).get('version') == 'protein_structure_result_selector_v1' or is_native_protein_structure_target(target):
            if not is_native_protein_structure_target(target):
                raise ValueError('original_commission_mismatch')
            from gene_annotation_episode.episodic_workflow.root.a102.protein_structure_selection import validate_protein_structure_result_selector
            return validate_protein_structure_result_selector(assignment['selector'], request=target['assignment']['requested_job']['native_protein_structure']['request'])
        if target['resource_kind'] == 'api':
            return self.api_execution.validate_result_selector(target, assignment['selector'])
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
            from gene_annotation_episode.episodic_workflow.root.a102.episode_receipts import EpisodeReceipts
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
            if canonical(launch['requests'].get(resource_id)) != canonical(selected):
                raise ValueError('execution_handoff_assignment_conflict')
        elif context.role in ROLE_KINDS:
            if canonical(target['assignment']) != canonical(context.assignment):
                raise ValueError('execution_handoff_assignment_conflict')
        elif context.role == 'results' and target != self._target(context):
            raise ValueError('execution_result_target_conflict')
        return target
