from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a104.library.hmmer_record_values import *

class HMMERObserver:

    def __init__(self, reader):
        self.reader = reader

    def observe_target(self, target, *, operation_key):
        target = validate_target(plain(target))
        qualified = self.reader.read_target(target['handle'], target['scope'])
        if target != qualified:
            raise ValueError('api_observation_target_identity_conflict')
        row = self.reader.store.db.execute('SELECT * FROM api_execution_observations WHERE operation_key=?', (operation_key,)).fetchone()
        if row is not None:
            if row['target'] != canonical(target):
                raise ValueError('api_observation_operation_key_conflict')
            if row['observation'] is not None:
                return json.loads(row['observation'])
            observation = self._unknown_observation(target, 'api_observation_response_unknown')
            with self.reader.store.transaction():
                self.reader.store.db.execute('UPDATE api_execution_observations SET observation=? WHERE operation_key=?', (canonical(observation), operation_key))
            return observation
        with self.reader.store.transaction():
            self.reader.store.db.execute('INSERT INTO api_execution_observations VALUES(?,?,NULL)', (operation_key, canonical(target)))
        body = self.reader._read_handoff(target['handle'], target['scope'])
        try:
            snapshot = self.reader.clients.hmmer_status(target['execution_id'])
            saved = self.reader._snapshot(snapshot)
            native, native_state, state = _native_status(snapshot, body['request'], target['execution_id'])
            provenance = self.reader.store.artifact(saved, 'application/json')
            observation = {'observed_at': snapshot.retrieved_at, 'state': state, 'returncode': None, 'failure_code': 'remote_search_failed' if state == 'failed' else None, 'result_available': state == 'completed', 'measurements': [], 'outputs': [], 'logs': [], 'provenance_refs': [target['handle'], provenance], 'native': {'service': 'ebi_hmmer', 'execution_id': target['execution_id'], 'native_state': native_state, 'status': native, 'snapshot': json.loads(saved)}}
        except Exception as error:
            from gene_annotation_episode.episodic_workflow.root.a104.api_error_feedback import api_error_feedback
            observation = self._unknown_observation(target, getattr(error, 'code', 'api_status_observation_failed'))
            observation['native']['error'] = api_error_feedback(error)
            if getattr(error, 'snapshot', None) is not None:
                saved = self.reader._snapshot(error.snapshot)
                observation['provenance_refs'].append(self.reader.store.artifact(saved, 'application/json'))
                observation['native']['snapshot'] = json.loads(saved)
        with self.reader.store.transaction():
            self.reader.store.db.execute('UPDATE api_execution_observations SET observation=? WHERE operation_key=?', (canonical(observation), operation_key))
        return observation

    def _unknown_observation(self, target, code):
        return {'observed_at': _now(), 'state': 'unknown', 'returncode': None, 'failure_code': code, 'result_available': False, 'measurements': [], 'outputs': [], 'logs': [], 'provenance_refs': [target['handle']], 'native': {'service': 'ebi_hmmer', 'execution_id': target['execution_id'], 'failure_code': code}}
