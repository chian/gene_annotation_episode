"""Original HMMER handoff custody and independent saved/native observations."""
from __future__ import annotations
import hashlib
import json
from gene_annotation_episode.domain import identity
from gene_annotation_episode.execution_contracts import validate_api_assignment, validate_target
from gene_annotation_episode.episodic_workflow.root.communication import plain
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.episodic_workflow.root.api_hmmer_protocol import PROVIDER, HANDOFF_VERSION, _now, _native_status


class HMMERHandoffRecords:
    def _publish_handoff(self, context, request, receipt):
        body = {'version': HANDOFF_VERSION, 'run_id': self.run_id, 'episode_id': context.episode_id,
            'assignment_sha256': digest(context.assignment), 'assignment': plain(context.assignment),
            'scope': plain(context.scope), 'request': request, 'receipt': receipt,
            'job_ref': receipt['job_ref'], 'execution_id': receipt['execution_id']}
        with self.store.transaction():
            artifact = self.store.artifact(canonical(body), 'application/json')
            request_ref = self.store.artifact(canonical({'assignment': plain(context.assignment),
                'scope': plain(context.scope), 'request': request}), 'application/json')
            return self.store.put('source', {'provider': PROVIDER,
                'accession': 'api_handoff_'+digest([self.run_id, context.episode_id, receipt['operation_key']]),
                'uri': None, 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': request_ref,
                'version': HANDOFF_VERSION, 'retrieved_at': receipt['finished_at']}, origin='tool')['id']

    def _artifact_json(self, reference):
        raw, record = self.store.get_artifact(reference), self.store.get(reference)
        value = json.loads(raw)
        sha = hashlib.sha256(raw).hexdigest()
        if (raw != canonical(value).encode('utf-8') or record.get('sha256') != sha
                or reference != 'artifact_'+sha or record.get('size') != len(raw)):
            raise ValueError('api_handoff_artifact_identity_conflict')
        return value

    def _read_handoff(self, reference, scope):
        source = self.store.get(reference)
        if source.get('provider') != PROVIDER or source.get('record_type') != 'source' or source.get('origin') != 'tool':
            raise ValueError('not_an_api_execution_handoff')
        body = self._artifact_json(source['artifact_ref'])
        assignment = validate_api_assignment(body['assignment'])
        self._constraints(assignment)
        if (body['version'] != HANDOFF_VERSION or body['run_id'] != self.run_id
                or body['assignment_sha256'] != digest(assignment)
                or assignment['resource_id'] not in self.configuration):
            raise ValueError('api_handoff_assignment_identity_conflict')
        self.store.validate_scope(plain(scope))
        self.store.validate_scope(body['scope'], parent_scope=plain(scope))
        manifest = self.store.db.execute('SELECT assignment,scope FROM api_execution_episodes '
            'WHERE run_id=? AND episode_id=?', (self.run_id, body['episode_id'])).fetchone()
        if (manifest is None or manifest['assignment'] != canonical(assignment)
                or manifest['scope'] != canonical(body['scope'])):
            raise ValueError('api_handoff_original_assignment_conflict')
        if self.store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='runtime_episodes'").fetchone():
            episode = self.store.db.execute('SELECT path,request FROM runtime_episodes WHERE run_id=? AND episode_id=?',
                (self.run_id, body['episode_id'])).fetchone()
            if episode is None:
                raise ValueError('api_handoff_original_episode_missing')
            message = json.loads(episode['request']).get('message', {})
            original = message.get('episode_assignment', message.get('assignment'))
            path = json.loads(episode['path'])
            if (canonical(original) != canonical(assignment) or canonical(message.get('scope')) != canonical(body['scope'])
                    or not path or path[-1][0] != 'launch_api'):
                raise ValueError('api_handoff_original_episode_conflict')
        receipt = body['receipt']
        if (receipt['version'] != 'api_execution_receipt_v1' or receipt['run_id'] != self.run_id
                or receipt['episode_id'] != body['episode_id'] or receipt['assignment_sha256'] != digest(assignment)
                or receipt['tool_name'] != 'api.hmmer.check_handoff' or receipt['arguments'] != {}
                or receipt['validation_keys'] != ['usable_handoff']
                or receipt['state'] not in {'submitted', 'running', 'completed'}
                or receipt['job_ref'] != body['job_ref'] or receipt['execution_id'] != body['execution_id']):
            raise ValueError('api_handoff_receipt_identity_conflict')
        original = self.store.db.execute('SELECT * FROM api_execution_actions WHERE operation_key=?',
                                        (receipt['operation_key'],)).fetchone()
        if (original is None or original['run_id'] != self.run_id or original['episode_id'] != body['episode_id']
                or original['name'] != receipt['tool_name'] or original['arguments'] != canonical(receipt['arguments'])
                or original['snapshot'] != canonical(receipt['status_snapshot'])):
            raise ValueError('api_handoff_selected_receipt_conflict')
        from gene_annotation_episode.episodic_workflow.root.receiving_context import BindingContext
        context = BindingContext(self.run_id, body['episode_id'], 'launch_api', (('launch_api', 'original'),),
            body['scope'], assignment, {})
        selected = self._selected(context, receipt['tool_name'], receipt['arguments'], receipt['operation_key'])
        if original['result'] is not None:
            result = json.loads(original['result'])
            if (result['status'] != 'completed' or reference not in result['record_refs']
                    or canonical(result['result'].get('receipt')) != canonical(receipt)):
                raise ValueError('api_handoff_saved_outcome_conflict')
        if selected['result'] is not None:
            result = json.loads(selected['result'])
            if (result.get('status') != 'completed' or reference not in result.get('record_refs', [])
                    or canonical(result.get('result', {}).get('receipt')) != canonical(receipt)):
                raise ValueError('api_handoff_runtime_outcome_conflict')
        job = self._job(body['episode_id'])
        prepared = self.store.db.execute('SELECT request,fasta_ref FROM api_execution_preparations WHERE run_id=? '
            'AND episode_id=?', (self.run_id, body['episode_id'])).fetchone()
        if (job['id'] != body['job_ref'] or job['remote_id'] != body['execution_id']
                or job['request'] != canonical(body['request']) or prepared is None
                or prepared['request'] != canonical(body['request'])):
            raise ValueError('api_handoff_physical_identity_conflict')
        request = body['request']
        from gene_annotation_episode.episodic_workflow.root.episode_input_versions import pin_commission_inputs
        identities = pin_commission_inputs(self.store, [assignment['subject_ref']], resource_input_versions=[
            {'reference': assignment['subject_ref'], 'version': None, 'content_sha256': None}])
        if identities != request['input_identities']:
            raise ValueError('api_handoff_original_input_identity_conflict')
        fasta = self.store.get_artifact(prepared['fasta_ref'])
        from gene_annotation_episode.domain import parse_sequences
        parsed = parse_sequences(fasta.decode('utf-8'), format='fasta', molecule='protein')
        if (len(parsed) != 1 or hashlib.sha256(fasta).hexdigest() != request['query_sha256']
                or hashlib.sha256(parsed[0].sequence.encode('ascii')).hexdigest() != request['sequence_sha256']
                or len(parsed[0].sequence) != request['query_length']
                or any(request[key] != assignment[key] for key in
                       ('subject_ref', 'algorithm', 'database', 'parameters', 'page_size', 'resource_id'))
                or request['assignment_sha256'] != digest(assignment)):
            raise ValueError('api_handoff_query_identity_conflict')
        snapshot = self._load_snapshot(canonical(receipt['status_snapshot']))
        _native, _status, state = _native_status(snapshot, request, body['execution_id'])
        if state != receipt['state']:
            raise ValueError('api_handoff_validation_conflict')
        expected = {'provider': PROVIDER, 'accession': 'api_handoff_'+digest([
            self.run_id, body['episode_id'], receipt['operation_key']]), 'uri': None,
            'artifact_ref': source['artifact_ref'], 'text_ref': source['artifact_ref'],
            'request_ref': source['request_ref'], 'version': HANDOFF_VERSION, 'retrieved_at': receipt['finished_at']}
        payload = {key: value for key, value in source.items() if key not in {'id', 'record_type', 'origin'}}
        if (canonical(payload) != canonical(expected) or reference != identity('source', {'origin': 'tool', 'record': expected})
                or self._artifact_json(source['request_ref']) != {'assignment': assignment, 'scope': body['scope'], 'request': request}):
            raise ValueError('api_handoff_source_identity_conflict')
        return body

    def scope(self, handoff_ref):
        source = self.store.get(handoff_ref)
        body = self._artifact_json(source['artifact_ref'])
        self._read_handoff(handoff_ref, body['scope'])
        return body['scope']

    def read_target(self, handoff_ref, scope):
        body = self._read_handoff(handoff_ref, scope)
        return validate_target({'version': 'execution_target_v1', 'handle': handoff_ref,
            'run_id': self.run_id, 'resource_id': body['assignment']['resource_id'], 'resource_kind': 'api',
            'execution_id': body['execution_id'], 'request_sha256': digest(body['assignment']),
            'origin_episode_id': body['episode_id'], 'assignment': body['assignment'], 'scope': body['scope']})

    def observe_target(self, target, *, operation_key):
        target = validate_target(plain(target))
        qualified = self.read_target(target['handle'], target['scope'])
        if target != qualified:
            raise ValueError('api_observation_target_identity_conflict')
        row = self.store.db.execute('SELECT * FROM api_execution_observations WHERE operation_key=?',
                                  (operation_key,)).fetchone()
        if row is not None:
            if row['target'] != canonical(target):
                raise ValueError('api_observation_operation_key_conflict')
            if row['observation'] is not None:
                return json.loads(row['observation'])
            observation = self._unknown_observation(target, 'api_observation_response_unknown')
            with self.store.transaction():
                self.store.db.execute('UPDATE api_execution_observations SET observation=? WHERE operation_key=?',
                    (canonical(observation), operation_key))
            return observation
        with self.store.transaction():
            self.store.db.execute('INSERT INTO api_execution_observations VALUES(?,?,NULL)',
                                  (operation_key, canonical(target)))
        body = self._read_handoff(target['handle'], target['scope'])
        try:
            snapshot = self.clients.hmmer_status(target['execution_id'])
            saved = self._snapshot(snapshot)
            native, native_state, state = _native_status(snapshot, body['request'], target['execution_id'])
            provenance = self.store.artifact(saved, 'application/json')
            observation = {'observed_at': snapshot.retrieved_at, 'state': state, 'returncode': None,
                'failure_code': 'remote_search_failed' if state == 'failed' else None,
                'result_available': state == 'completed', 'measurements': [], 'outputs': [], 'logs': [],
                'provenance_refs': [target['handle'], provenance],
                'native': {'service': 'ebi_hmmer', 'execution_id': target['execution_id'],
                    'native_state': native_state, 'status': native, 'snapshot': json.loads(saved)}}
        except Exception as error:
            from gene_annotation_episode.api_error_feedback import api_error_feedback
            observation = self._unknown_observation(target, getattr(error, 'code', 'api_status_observation_failed'))
            observation['native']['error'] = api_error_feedback(error)
            if getattr(error, 'snapshot', None) is not None:
                saved = self._snapshot(error.snapshot)
                observation['provenance_refs'].append(self.store.artifact(saved, 'application/json'))
                observation['native']['snapshot'] = json.loads(saved)
        with self.store.transaction():
            self.store.db.execute('UPDATE api_execution_observations SET observation=? WHERE operation_key=?',
                                  (canonical(observation), operation_key))
        return observation

    def _unknown_observation(self, target, code):
        return {'observed_at': _now(), 'state': 'unknown', 'returncode': None, 'failure_code': code,
            'result_available': False, 'measurements': [], 'outputs': [], 'logs': [],
            'provenance_refs': [target['handle']], 'native': {'service': 'ebi_hmmer',
                'execution_id': target['execution_id'], 'failure_code': code}}

