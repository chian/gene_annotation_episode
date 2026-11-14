"""Original received handoff, selection and Results commission custody.

The actual receiver supplies Store, services, original target/readers and
scientific request materializers. No role registration, constructor or dispatch.
"""
from __future__ import annotations

import hashlib
import json

from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.episodic_workflow.root.communication import plain


RESULT_PROVIDER = 'episode.execution_result'
ROLE_KINDS = {'launch_api': 'api', 'launch_local': 'local', 'launch_hpc': 'hpc'}
BLAST_GRADED_REQUEST_VERSION = 'blast_database_grader_return_request_v1'


class ExecutionReceivedCustody:
    def _recorded_results_assignment(self, parent, selected, scope, operation_key):
        """Restore a successfully returned original Results commission only."""
        from .episode_receipts import EpisodeReceipts
        from .episode_return_records import EpisodeReturnRecords
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
        attempt = self.store.db.execute('SELECT child_episode_id,contract,form,failure '
            'FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? AND decision_index=?',
            (self.run_id, parent.episode_id, index)).fetchone()
        if attempt is None or attempt['form'] is None or attempt['failure'] is not None:
            return None
        try:
            form, contract = json.loads(attempt['form']), json.loads(attempt['contract'])
            schema = contract['measurements']['schema']
        except (ValueError, TypeError, KeyError) as error:
            raise ValueError('recorded_results_original_return_invalid') from error
        if proof.recorded_admission_references(parent, form, schema, index) is None:
            return None
        child = proof.context(attempt['child_episode_id'])
        proof._require(child.role == 'results' and child.path[:-1] == parent.path
            and child.path[-1] == ('results', 'child_' + str(index)), 'original_child_conflict')
        state = self.store.db.execute('SELECT state FROM runtime_episodes WHERE run_id=? AND episode_id=?',
            (self.run_id, child.episode_id)).fetchone()
        if state['state'] != 'yielded':
            return None
        action = self.store.db.execute('SELECT action FROM runtime_actions WHERE run_id=? '
            'AND episode_id=? AND decision_index=?', (self.run_id, parent.episode_id, index)).fetchone()
        original = json.loads(action['action'])
        proof._require(original.get('kind') == 'episode_child' and original.get('role') == 'results',
            'original_selection_conflict')
        proof._require(proof._equal(selected, original.get('assignment'))
            and proof._equal(selected, child.assignment), 'assignment_conflict')
        proof._require(proof._equal(scope, original.get('scope'))
            and proof._equal(scope, child.scope), 'scope_conflict')
        return plain(child.assignment)

    def _selection(self, context, supplied=None):
        if supplied is None and self.services is not None:
            callback = getattr(self.services, 'record_selection', None)
            supplied = None if callback is None else callback(context)
        if supplied is None:
            from .episode_receipts import EpisodeReceipts
            table = self.store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='runtime_receipt_inheritance'").fetchone()
            if table and self.store.db.execute('SELECT 1 FROM runtime_receipt_inheritance WHERE run_id=? AND episode_id=?',
                    (self.run_id, context.episode_id)).fetchone():
                receipts = EpisodeReceipts(self.store, self.run_id)
                supplied = {'run_id': self.run_id, 'episode_id': context.episode_id,
                    'known_record_refs': list(receipts.known(context.episode_id)),
                    'initial_known_record_refs': list(receipts.known(context.episode_id, baseline=True))}
            else:
                rows = self.store.db.execute('SELECT result FROM runtime_actions WHERE run_id=? AND episode_id=? '
                    'AND result IS NOT NULL ORDER BY decision_index', (self.run_id, context.episode_id))
                supplied = {'run_id': self.run_id, 'episode_id': context.episode_id,
                    'known_record_refs': list(dict.fromkeys(ref for row in rows
                        for ref in json.loads(row[0]).get('record_refs', []))), 'initial_known_record_refs': []}
        supplied = plain(supplied)
        if supplied.get('run_id') != self.run_id or supplied.get('episode_id') != context.episode_id:
            raise ValueError('execution_receiver_identity_conflict')
        for key in ('known_record_refs', 'initial_known_record_refs'):
            if not isinstance(supplied.get(key), list) or any(not isinstance(ref, str) or not ref for ref in supplied[key]):
                raise ValueError('execution_receiver_references_required')
        if not set(supplied['initial_known_record_refs']) <= set(supplied['known_record_refs']):
            raise ValueError('execution_initial_references_must_be_known')
        return supplied

    def _context_target(self, context, target):
        from gene_annotation_episode.episodic_workflow.root.library.lumpy_assignment_identity import (is_compact_assignment as is_lumpy_assignment,
            is_compact_launch as is_lumpy_launch)
        from gene_annotation_episode.episodic_workflow.root.library.lumpy_request_binding import read_request_binding as read_lumpy_binding
        if is_lumpy_launch(plain(context.assignment)) or is_lumpy_assignment(plain(context.assignment)):
            own = read_lumpy_binding(self.store, self.run_id, context.episode_id)
            original = read_lumpy_binding(self.store, self.run_id, target['origin_episode_id'])
            if (not any(canonical(row['assignment']) == canonical(target['assignment']) for row in own['requests'])
                    or canonical(target['assignment']) != canonical(original['requests'][0]['assignment'])
                    or context.role == 'launch' and original['parent_file'] != own['file']):
                raise ValueError('execution_handoff_assignment_conflict')
            return target

        from gene_annotation_episode.episodic_workflow.root.library.macs2_peak_assignment_identity import (is_compact_assignment as is_macs2_assignment,
            is_compact_launch as is_macs2_launch)
        from gene_annotation_episode.episodic_workflow.root.library.macs2_peak_request_binding import read_request_binding as read_macs2_binding
        if is_macs2_launch(plain(context.assignment)) or is_macs2_assignment(plain(context.assignment)):
            own = read_macs2_binding(self.store, self.run_id, context.episode_id)
            original = read_macs2_binding(self.store, self.run_id, target['origin_episode_id'])
            if (not any(canonical(row['assignment']) == canonical(target['assignment']) for row in own['requests'])
                    or canonical(target['assignment']) != canonical(original['requests'][0]['assignment'])
                    or context.role == 'launch' and original['parent_file'] != own['file']):
                raise ValueError('execution_handoff_assignment_conflict')
            return target
        from gene_annotation_episode.episodic_workflow.root.library.flux_balance_assignment_identity import is_compact_assignment, is_compact_launch
        from gene_annotation_episode.episodic_workflow.root.library.flux_balance_request_binding import read_request_binding
        if (is_compact_launch(plain(context.assignment)) or is_compact_assignment(plain(context.assignment))):
            own = read_request_binding(self.store, self.run_id, context.episode_id)
            original = read_request_binding(self.store, self.run_id, target['origin_episode_id'])
            if (not any(row['assignment'] == target['assignment'] for row in own['requests'])
                    or target['assignment'] != original['requests'][0]['assignment']
                    or context.role == 'launch' and original['parent_file'] != own['file']):
                raise ValueError('execution_handoff_assignment_conflict')
            return target
        if context.role == 'launch':
            launch = self._launch(plain(context.assignment), scope=context.scope)
            selected = target['assignment']
            resource_id = target['resource_id']
            request = launch['requests'].get(resource_id)
            if request is not None and request.get('version') == BLAST_GRADED_REQUEST_VERSION:
                self._validate_blast_launch_selection(launch, selected, context.scope)
                handoff = self.api_execution._read_handoff(target['handle'], plain(context.scope))
                subject_ref = selected['request']['subject_ref']
                sequence = self.tool_registry._sequence(subject_ref,
                    molecule_model=self.store.subject_molecule(subject_ref))
                expected = hashlib.sha256(f'>{subject_ref}\n{sequence}'.encode()).hexdigest()
                if handoff['snapshot']['request'].get('query_sha256') != expected:
                    raise ValueError('blast_grader_submitted_query_conflict')
        elif context.role in ROLE_KINDS:
            if canonical(target['assignment']) != canonical(context.assignment):
                raise ValueError('execution_handoff_assignment_conflict')
        elif context.role == 'results' and target != self._target(context):
            raise ValueError('execution_result_target_conflict')
        return target

    def _received(self, context, selection=None, *, _handoff_read=None):
        with self.store.read_snapshot():
            selection = self._selection(context, selection)
            read = self.job_progress_provider.targets._handoff_reader() if _handoff_read is None else _handoff_read
            handoffs, results = {}, {}
            for reference in dict.fromkeys(selection['known_record_refs']):
                source = self.store.get(reference)
                if source.get('provider') == RESULT_PROVIDER:
                    if source.get('version') in {'native_blast_utility_bundle_v1', 'native_blast_masking_bundle_v1', 'native_hmmer_bundle_v1', 'native_blast_bundle_v1', 'native_blast_database_bundle_v1', 'native_blast_standard_database_bundle_v1', 'native_infernal_bundle_v1',
                            'native_infernal_preparation_bundle_v1', 'native_hmmer_preparation_bundle_v1',
                            'native_protein_structure_bundle_v1',
                            'native_rna_structure_bundle_v1'}:
                        # Original bundle acquisitions have their own exact-row
                        # receipts; they are not current-filesystem byte windows.
                        continue
                    body = self._read_result(reference, context.scope)
                    if context.role == 'results' and body['assignment'] != plain(context.assignment):
                        continue
                    results[reference] = body
                    continue
                if (source.get('provider') != 'episode.practical_receipt'
                        and not (self.api_execution is not None
                            and self.api_execution.is_handoff_source(reference))):
                    continue
                try:
                    target, _, returnable = read(reference, context.scope)
                except (ValueError, KeyError):
                    continue  # A preparation/status-only receipt is no handoff.
                try:
                    self._context_target(context, target)
                except ValueError:
                    # An inherited handoff for different work stays valid context,
                    # without becoming this assignment's contribution or endpoint.
                    continue
                if returnable:
                    handoffs[reference] = target
            return selection, handoffs, results

