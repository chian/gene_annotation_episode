"""Private A104 Results saved commission."""
from __future__ import annotations
import json
from gene_annotation_episode.episodic_workflow.root.a104.communication import plain

class ResultsSavedCommission:

    def _recorded_results_assignment(self, parent, selected, scope, operation_key):
        """Restore a successfully returned original Results commission only."""
        from gene_annotation_episode.episodic_workflow.root.a104.episode_receipts import EpisodeReceipts
        from gene_annotation_episode.episodic_workflow.root.a104.episode_return_records import EpisodeReturnRecords
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
