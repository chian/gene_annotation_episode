"""Bounded HMMER operations inside the shared execution episode.

This adapter contains no polling, retry, model or episode loop. API targets use
``digest(original API assignment)`` as request_sha256; the HTTP request, submitted
FASTA bytes and parsed sequence each retain their own distinct frozen identities.
Native monitoring has independent observation custody and never changes launch
receipts, completion proofs or its closed controller history.
"""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path
from gene_annotation_episode.episodic_workflow.root.a110.acquisition import AcquisitionError, SourceSnapshot
from gene_annotation_episode.episodic_workflow.root.a110.communication import plain
from gene_annotation_episode.episodic_workflow.root.a110.domain import identity
from gene_annotation_episode.episodic_workflow.root.a110.execution_contracts import canonical, digest
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_api_contracts import validate_api_assignment, validate_target
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_provider_job_identity import validate_remote_identity
PROVIDER = 'episode.api_hmmer_handoff'
HANDOFF_VERSION = 'api_hmmer_handoff_v1'

def _native_status(snapshot, request, remote_id):
    try:
        native = json.loads(snapshot.content)
        canonical(native)
        task = native.get('task') if isinstance(native, dict) else None
        if not isinstance(native, dict) or (task is not None and (not isinstance(task, dict) or not isinstance(task.get('status', 'UNKNOWN'), str))):
            raise ValueError('status_object_required')
    except (ValueError, TypeError, UnicodeError) as error:
        raise AcquisitionError('provider_status_response_invalid', snapshot=snapshot, phase='status_response') from error
    try:
        validate_remote_identity(native, request, remote_id)
    except AcquisitionError as error:
        error.snapshot = snapshot
        raise
    status = (task or {}).get('status', 'UNKNOWN')
    states = {'PENDING': 'submitted', 'RECEIVED': 'submitted', 'STARTED': 'running', 'RETRY': 'running', 'SUCCESS': 'completed', 'FAILURE': 'failed', 'REVOKED': 'failed'}
    return (native, status, states.get(status, 'unknown'))

class HMMERAPIExecution:

    def __init__(self, store, *, run_id, directory, configuration, tool_registry, handoff_unit, acquired_record_unit):
        if not isinstance(run_id, str) or not run_id:
            raise ValueError('explicit_api_execution_run_required')
        for value in (handoff_unit, acquired_record_unit):
            if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
                raise ValueError('explicit_positive_operational_credit_units_required')
        self.store, self.run_id, self.directory = (store, run_id, Path(directory))
        self.configuration = json.loads(canonical(configuration))
        if not isinstance(self.configuration, dict) or not self.configuration or any((not isinstance(key, str) or not key or (not isinstance(value, dict)) or (value.get('kind') != 'hmmer_api') or set(value) - {'kind', 'service'} or (value.get('service', 'ebi_hmmer') != 'ebi_hmmer') for key, value in self.configuration.items())):
            raise ValueError('explicit_api_resources_required')
        if tool_registry.store is not store or not callable(getattr(tool_registry, 'publish_hmmer_result', None)):
            raise ValueError('actual_tool_registry_required_for_api_execution')
        self.tools, self.clients = (tool_registry, tool_registry.clients)
        self.handoff_unit, self.acquired_record_unit = (handoff_unit, acquired_record_unit)
        store.db.executescript('\n            CREATE TABLE IF NOT EXISTS api_execution_episodes (\n                run_id TEXT NOT NULL, episode_id TEXT NOT NULL, assignment TEXT NOT NULL,\n                scope TEXT NOT NULL, PRIMARY KEY(run_id,episode_id));\n            CREATE TABLE IF NOT EXISTS api_execution_preparations (\n                run_id TEXT NOT NULL, episode_id TEXT NOT NULL, request TEXT NOT NULL,\n                fasta_ref TEXT NOT NULL, PRIMARY KEY(run_id,episode_id));\n            CREATE TABLE IF NOT EXISTS api_execution_actions (\n                operation_key TEXT PRIMARY KEY, run_id TEXT NOT NULL, episode_id TEXT NOT NULL,\n                name TEXT NOT NULL, arguments TEXT NOT NULL, intent TEXT NOT NULL,\n                snapshot TEXT, result TEXT);\n            CREATE TABLE IF NOT EXISTS api_execution_observations (\n                operation_key TEXT PRIMARY KEY, target TEXT NOT NULL, observation TEXT);\n        ')

    def _constraints(self, assignment):
        constraints = assignment['constraints']
        for key, value in constraints.items():
            if key == 'allowed_resource_ids':
                if not isinstance(value, list) or assignment['resource_id'] not in value:
                    raise ValueError('api_resource_constraint_conflict')
            elif key == 'allowed_kinds':
                if not isinstance(value, list) or 'api' not in value:
                    raise ValueError('api_kind_constraint_conflict')
            elif key == 'kind':
                if value not in {'api', 'hmmer_api'}:
                    raise ValueError('api_kind_constraint_conflict')
            elif key in {'service', 'resource_id', 'subject_ref', 'algorithm', 'database', 'parameters', 'page_size'}:
                if value != assignment[key]:
                    raise ValueError('api_request_constraint_conflict')
            else:
                raise ValueError('unsupported_api_execution_constraint:' + key)

    def _assignment(self, context):
        if context.run_id != self.run_id:
            raise ValueError('api_execution_run_conflict')
        if context.role == 'results':
            raw = plain(context.assignment)
            if set(raw) != {'version', 'handoff_ref', 'selector'} or raw['version'] != 'execution_results_assignment_v1' or (not isinstance(raw['selector'], dict)):
                raise ValueError('invalid_api_results_assignment')
            selector = raw['selector']
            if set(selector) - {'page', 'page_size'} or 'page' not in selector or any((type(value) is not int or value <= 0 for value in selector.values())):
                raise ValueError('invalid_api_results_selector')
            assignment = self.read_target(raw['handoff_ref'], context.scope)['assignment']
            if 'page_size' in assignment['constraints'] and selector.get('page_size', assignment['page_size']) != assignment['constraints']['page_size']:
                raise ValueError('api_result_page_size_constraint_conflict')
            return assignment
        if context.role != 'launch_api':
            raise ValueError('api_execution_role_required')
        assignment = validate_api_assignment(plain(context.assignment))
        self._constraints(assignment)
        if assignment['resource_id'] not in self.configuration:
            raise ValueError('api_resource_not_bound')
        self.tools._check_sequence_operand(assignment['subject_ref'], plain(context.scope))
        return assignment

    def initialize(self, context):
        self._assignment(context)
        assignment, scope = (canonical(context.assignment), canonical(context.scope))
        with self.store.transaction():
            row = self.store.db.execute('SELECT assignment,scope FROM api_execution_episodes WHERE run_id=? AND episode_id=?', (self.run_id, context.episode_id)).fetchone()
            if row is not None:
                if row['assignment'] != assignment or row['scope'] != scope:
                    raise ValueError('api_original_assignment_conflict')
            else:
                self.store.db.execute('INSERT INTO api_execution_episodes VALUES(?,?,?,?)', (self.run_id, context.episode_id, assignment, scope))
        return {'assignment': plain(context.assignment), 'scope': plain(context.scope)}

    def _load_snapshot(self, saved):
        fields = json.loads(saved)
        fields['content'] = self.store.get_artifact(fields.pop('content_ref'))
        return SourceSnapshot(**fields)

    def _selected(self, context, name, arguments, key):
        prefix = f'{self.run_id}:{context.episode_id}:'
        suffix = key.removeprefix(prefix)
        if not key.startswith(prefix) or not suffix.isdecimal() or str(int(suffix)) != suffix:
            raise ValueError('api_selected_action_identity_required')
        try:
            row = self.store.db.execute('SELECT action,result FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?', (self.run_id, context.episode_id, int(suffix))).fetchone()
        except Exception as error:
            raise ValueError('api_selected_action_missing') from error
        if row is None:
            raise ValueError('api_selected_action_missing')
        action = json.loads(row['action'])
        if action.get('kind') != 'tool' or action.get('tool') != name or canonical(action.get('arguments')) != canonical(arguments):
            raise ValueError('api_selected_action_conflict')
        return row

    def _job(self, episode_id):
        rows = self.store.db.execute("SELECT * FROM provider_jobs WHERE operation_key IN (SELECT operation_key FROM api_execution_actions WHERE run_id=? AND episode_id=? AND name='api.hmmer.submit')", (self.run_id, episode_id)).fetchall()
        if len(rows) != 1:
            raise ValueError('api_original_submission_missing' if not rows else 'api_submission_identity_conflict')
        return dict(rows[0])

    def _artifact_json(self, reference):
        raw, record = (self.store.get_artifact(reference), self.store.get(reference))
        value = json.loads(raw)
        sha = hashlib.sha256(raw).hexdigest()
        if raw != canonical(value).encode('utf-8') or record.get('sha256') != sha or reference != 'artifact_' + sha or (record.get('size') != len(raw)):
            raise ValueError('api_handoff_artifact_identity_conflict')
        return value

    def _read_handoff(self, reference, scope):
        source = self.store.get(reference)
        if source.get('provider') != PROVIDER or source.get('record_type') != 'source' or source.get('origin') != 'tool':
            raise ValueError('not_an_api_execution_handoff')
        body = self._artifact_json(source['artifact_ref'])
        assignment = validate_api_assignment(body['assignment'])
        self._constraints(assignment)
        if body['version'] != HANDOFF_VERSION or body['run_id'] != self.run_id or body['assignment_sha256'] != digest(assignment) or (assignment['resource_id'] not in self.configuration):
            raise ValueError('api_handoff_assignment_identity_conflict')
        self.store.validate_scope(plain(scope))
        self.store.validate_scope(body['scope'], parent_scope=plain(scope))
        manifest = self.store.db.execute('SELECT assignment,scope FROM api_execution_episodes WHERE run_id=? AND episode_id=?', (self.run_id, body['episode_id'])).fetchone()
        if manifest is None or manifest['assignment'] != canonical(assignment) or manifest['scope'] != canonical(body['scope']):
            raise ValueError('api_handoff_original_assignment_conflict')
        if self.store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='runtime_episodes'").fetchone():
            episode = self.store.db.execute('SELECT path,request FROM runtime_episodes WHERE run_id=? AND episode_id=?', (self.run_id, body['episode_id'])).fetchone()
            if episode is None:
                raise ValueError('api_handoff_original_episode_missing')
            message = json.loads(episode['request']).get('message', {})
            original = message.get('episode_assignment', message.get('assignment'))
            path = json.loads(episode['path'])
            if canonical(original) != canonical(assignment) or canonical(message.get('scope')) != canonical(body['scope']) or (not path) or (path[-1][0] != 'launch_api'):
                raise ValueError('api_handoff_original_episode_conflict')
        receipt = body['receipt']
        if receipt['version'] != 'api_execution_receipt_v1' or receipt['run_id'] != self.run_id or receipt['episode_id'] != body['episode_id'] or (receipt['assignment_sha256'] != digest(assignment)) or (receipt['tool_name'] != 'api.hmmer.check_handoff') or (receipt['arguments'] != {}) or (receipt['validation_keys'] != ['usable_handoff']) or (receipt['state'] not in {'submitted', 'running', 'completed'}) or (receipt['job_ref'] != body['job_ref']) or (receipt['execution_id'] != body['execution_id']):
            raise ValueError('api_handoff_receipt_identity_conflict')
        original = self.store.db.execute('SELECT * FROM api_execution_actions WHERE operation_key=?', (receipt['operation_key'],)).fetchone()
        if original is None or original['run_id'] != self.run_id or original['episode_id'] != body['episode_id'] or (original['name'] != receipt['tool_name']) or (original['arguments'] != canonical(receipt['arguments'])) or (original['snapshot'] != canonical(receipt['status_snapshot'])):
            raise ValueError('api_handoff_selected_receipt_conflict')
        from gene_annotation_episode.episodic_workflow.root.a110.episode_bindings import BindingContext
        context = BindingContext(self.run_id, body['episode_id'], 'launch_api', (('launch_api', 'original'),), body['scope'], assignment, {})
        selected = self._selected(context, receipt['tool_name'], receipt['arguments'], receipt['operation_key'])
        if original['result'] is not None:
            result = json.loads(original['result'])
            if result['status'] != 'completed' or reference not in result['record_refs'] or canonical(result['result'].get('receipt')) != canonical(receipt):
                raise ValueError('api_handoff_saved_outcome_conflict')
        if selected['result'] is not None:
            result = json.loads(selected['result'])
            if result.get('status') != 'completed' or reference not in result.get('record_refs', []) or canonical(result.get('result', {}).get('receipt')) != canonical(receipt):
                raise ValueError('api_handoff_runtime_outcome_conflict')
        job = self._job(body['episode_id'])
        prepared = self.store.db.execute('SELECT request,fasta_ref FROM api_execution_preparations WHERE run_id=? AND episode_id=?', (self.run_id, body['episode_id'])).fetchone()
        if job['id'] != body['job_ref'] or job['remote_id'] != body['execution_id'] or job['request'] != canonical(body['request']) or (prepared is None) or (prepared['request'] != canonical(body['request'])):
            raise ValueError('api_handoff_physical_identity_conflict')
        request = body['request']
        from gene_annotation_episode.episodic_workflow.root.a110.episode_input_versions import pin_commission_inputs
        identities = pin_commission_inputs(self.store, [assignment['subject_ref']], resource_input_versions=[{'reference': assignment['subject_ref'], 'version': None, 'content_sha256': None}])
        if identities != request['input_identities']:
            raise ValueError('api_handoff_original_input_identity_conflict')
        fasta = self.store.get_artifact(prepared['fasta_ref'])
        from gene_annotation_episode.episodic_workflow.root.a110.domain import parse_sequences
        parsed = parse_sequences(fasta.decode('utf-8'), format='fasta', molecule='protein')
        if len(parsed) != 1 or hashlib.sha256(fasta).hexdigest() != request['query_sha256'] or hashlib.sha256(parsed[0].sequence.encode('ascii')).hexdigest() != request['sequence_sha256'] or (len(parsed[0].sequence) != request['query_length']) or any((request[key] != assignment[key] for key in ('subject_ref', 'algorithm', 'database', 'parameters', 'page_size', 'resource_id'))) or (request['assignment_sha256'] != digest(assignment)):
            raise ValueError('api_handoff_query_identity_conflict')
        snapshot = self._load_snapshot(canonical(receipt['status_snapshot']))
        _native, _status, state = _native_status(snapshot, request, body['execution_id'])
        if state != receipt['state']:
            raise ValueError('api_handoff_validation_conflict')
        expected = {'provider': PROVIDER, 'accession': 'api_handoff_' + digest([self.run_id, body['episode_id'], receipt['operation_key']]), 'uri': None, 'artifact_ref': source['artifact_ref'], 'text_ref': source['artifact_ref'], 'request_ref': source['request_ref'], 'version': HANDOFF_VERSION, 'retrieved_at': receipt['finished_at']}
        payload = {key: value for key, value in source.items() if key not in {'id', 'record_type', 'origin'}}
        if canonical(payload) != canonical(expected) or reference != identity('source', {'origin': 'tool', 'record': expected}) or self._artifact_json(source['request_ref']) != {'assignment': assignment, 'scope': body['scope'], 'request': request}:
            raise ValueError('api_handoff_source_identity_conflict')
        return body

    def scope(self, handoff_ref):
        source = self.store.get(handoff_ref)
        body = self._artifact_json(source['artifact_ref'])
        self._read_handoff(handoff_ref, body['scope'])
        return body['scope']

    def read_target(self, handoff_ref, scope):
        body = self._read_handoff(handoff_ref, scope)
        return validate_target({'version': 'execution_target_v1', 'handle': handoff_ref, 'run_id': self.run_id, 'resource_id': body['assignment']['resource_id'], 'resource_kind': 'api', 'execution_id': body['execution_id'], 'request_sha256': digest(body['assignment']), 'origin_episode_id': body['episode_id'], 'assignment': body['assignment'], 'scope': body['scope']})

    def _own_results(self, context):
        return [json.loads(row['result']) for row in self.store.db.execute('SELECT result FROM api_execution_actions WHERE run_id=? AND episode_id=? AND result IS NOT NULL ORDER BY rowid', (self.run_id, context.episode_id))]

    def facts(self, context, completion_snapshot):
        self.initialize(context)
        handoffs, results = ([], [])
        for outcome in self._own_results(context):
            if outcome['status'] not in {'completed', 'partial'}:
                continue
            for reference in outcome['record_refs']:
                record = self.store.get(reference)
                if record.get('provider') == PROVIDER:
                    self.read_target(reference, context.scope)
                    handoffs.append(reference)
                elif context.role == 'results':
                    results.append(reference)
        return {'execution_handoff_refs': list(dict.fromkeys(handoffs)), 'execution_result_refs': list(dict.fromkeys(results)), 'execution_completed': self._completion(context) is not None}

    def read_result(self, reference, scope):
        """Qualify actual acquired records for their receiving parent, without I/O."""
        self.store.get(reference)
        rows = self.store.db.execute("SELECT action.* FROM api_execution_actions action, json_each(action.result,'$.record_refs') returned WHERE action.run_id=? AND action.name='api.hmmer.result' AND returned.value=? ORDER BY action.rowid", (self.run_id, reference)).fetchall()
        for row in rows:
            outcome = json.loads(row['result'])
            if outcome['status'] not in {'completed', 'partial'}:
                continue
            manifest = self.store.db.execute('SELECT assignment,scope FROM api_execution_episodes WHERE run_id=? AND episode_id=?', (self.run_id, row['episode_id'])).fetchone()
            assignment, original_scope = (json.loads(manifest['assignment']), json.loads(manifest['scope']))
            self.store.validate_scope(original_scope, parent_scope=plain(scope))
            if assignment.get('version') != 'execution_results_assignment_v1':
                raise ValueError('api_result_original_assignment_conflict')
            target = self.read_target(assignment['handoff_ref'], original_scope)
            selector = assignment['selector']
            from gene_annotation_episode.episodic_workflow.root.a110.episode_bindings import BindingContext
            original_context = BindingContext(self.run_id, row['episode_id'], 'results', (('results', 'original'),), original_scope, assignment, {})
            selected = self._selected(original_context, row['name'], json.loads(row['arguments']), row['operation_key'])
            if selected['result'] is not None:
                actual = json.loads(selected['result'])
                if actual.get('status') != outcome['status'] or actual.get('record_refs') != outcome['record_refs'] or canonical(actual.get('result')) != canonical(outcome.get('result')):
                    raise ValueError('api_result_runtime_outcome_conflict')
            episode = self.store.db.execute('SELECT request FROM runtime_episodes WHERE run_id=? AND episode_id=?', (self.run_id, row['episode_id'])).fetchone()
            message = json.loads(episode['request']).get('message', {}) if episode is not None else {}
            if canonical(message.get('episode_assignment', message.get('assignment'))) != canonical(assignment) or canonical(message.get('scope')) != canonical(original_scope):
                raise ValueError('api_result_original_episode_conflict')
            publication = self.store.db.execute('SELECT * FROM tool_operations WHERE operation_key=?', (row['operation_key'] + ':publication',)).fetchone()
            if publication is None or publication['name'] != 'internal.hmmer.result_publication':
                raise ValueError('api_result_original_publication_missing')
            published = json.loads(publication['result'])
            if published['record_refs'] != outcome['record_refs'] or published['status'] != outcome['status'] or publication['scope'] != canonical(original_scope):
                raise ValueError('api_result_original_publication_conflict')
            source_ref = published['result']['source_ref']
            source = self.store.get(source_ref)
            request = self._artifact_json(source['request_ref'])['request']
            snapshot = self._load_snapshot(row['snapshot'])
            body = self._read_handoff(target['handle'], original_scope)
            if self.store.get_artifact(source['artifact_ref']) != snapshot.content or request != {**body['request'], 'job_id': target['execution_id'], 'page': selector['page'], 'page_size': selector.get('page_size', target['assignment']['page_size'])}:
                raise ValueError('api_result_original_request_conflict')
            validate_remote_identity(json.loads(snapshot.content), body['request'], target['execution_id'], result=True)
            return {'version': 'api_acquired_result_information_v1', 'reference': reference, 'run_id': self.run_id, 'episode_id': row['episode_id'], 'scope': original_scope, 'assignment': assignment, 'target': target, 'source_ref': source_ref, 'record_refs': list(outcome['record_refs']), 'status': outcome['status']}
        raise ValueError('not_an_api_acquired_result')

    def _completion(self, context):
        if context.run_id != self.run_id:
            raise ValueError('api_completion_run_identity_conflict')
        if context.role == 'results':
            return self._results_completion(context)
        if context.role != 'launch_api':
            return None
        for outcome in reversed(self._own_results(context)):
            receipt = (outcome.get('result') or {}).get('receipt')
            if outcome['status'] == 'completed' and receipt is not None:
                reference = outcome['result']['handoff_ref']
                self.read_target(reference, context.scope)
                return {'version': 'practical_completion_v1', 'run_id': self.run_id, 'episode_id': context.episode_id, 'assignment_sha256': digest(context.assignment), 'endpoint': 'usable_handoff', 'operation_key': receipt['operation_key'], 'receipt_sha256': digest(receipt), 'validation_keys': ['usable_handoff']}
        return None

    def _results_completion(self, context):
        assignment = plain(context.assignment)
        if assignment.get('version') != 'execution_results_assignment_v1':
            return None
        target = self.read_target(assignment['handoff_ref'], context.scope)
        for row in self.store.db.execute("SELECT * FROM api_execution_actions WHERE run_id=? AND episode_id=? AND name='api.hmmer.result' AND result IS NOT NULL ORDER BY rowid DESC", (self.run_id, context.episode_id)):
            outcome = json.loads(row['result'])
            if outcome['status'] != 'completed':
                continue
            receipt = (outcome.get('result') or {}).get('acquisition_receipt')
            if receipt is None:
                continue
            if receipt['version'] != 'api_result_acquisition_receipt_v1' or receipt['run_id'] != self.run_id or receipt['episode_id'] != context.episode_id or (receipt['tool_name'] != 'api.hmmer.result') or (receipt['arguments'] != {}) or (receipt['validation_keys'] != ['requested_result_page']) or (receipt['assignment_sha256'] != digest(assignment)) or (receipt['selector'] != assignment['selector']) or (receipt['selector_sha256'] != digest(assignment['selector'])) or (receipt['handoff_ref'] != target['handle']) or (receipt['operation_key'] != row['operation_key']) or (receipt['record_refs'] != outcome['record_refs']) or (receipt['source_ref'] != outcome['result']['source_ref']):
                raise ValueError('api_result_completion_identity_conflict')
            selected = self._selected(context, row['name'], json.loads(row['arguments']), row['operation_key'])
            if selected['result'] is not None:
                actual = json.loads(selected['result'])
                if actual.get('status') != 'completed' or actual.get('record_refs') != outcome['record_refs'] or canonical(actual.get('result')) != canonical(outcome.get('result')):
                    raise ValueError('api_result_completion_runtime_outcome_conflict')
            original = self._load_snapshot(row['snapshot'])
            if original.sha256 != receipt['snapshot_sha256']:
                raise ValueError('api_result_completion_source_conflict')
            source = self.store.get(receipt['source_ref'])
            request = self._artifact_json(source['request_ref'])['request']
            selector = assignment['selector']
            if self.store.get_artifact(source['artifact_ref']) != original.content or request['job_id'] != target['execution_id'] or request['page'] != selector['page'] or (request['page_size'] != selector.get('page_size', target['assignment']['page_size'])):
                raise ValueError('api_result_completion_requested_page_conflict')
            return {'version': 'practical_completion_v1', 'run_id': self.run_id, 'episode_id': context.episode_id, 'assignment_sha256': digest(assignment), 'endpoint': 'usable_handoff', 'operation_key': row['operation_key'], 'receipt_sha256': digest(receipt), 'validation_keys': ['requested_result_page']}
        return None
