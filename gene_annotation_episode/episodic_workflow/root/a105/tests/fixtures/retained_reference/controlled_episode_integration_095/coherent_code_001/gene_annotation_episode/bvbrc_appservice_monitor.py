"""One authenticated native observation selected by an existing monitor.

The episode owns the choice. This adapter retains its original request/response
and projects recorded facts; it never polls, retries or evaluates science.
"""
from __future__ import annotations

import asyncio
import base64
from copy import deepcopy
from datetime import datetime, timezone
import fcntl
import json

from method_loop.durable import content_digest

from .acquisition import AcquisitionError, SourceSnapshot
from .bvbrc_appservice_contracts import validate_contract
from .bvbrc_appservice_custody import AppServiceCustodyError
from .communication import plain
from .domain import identity, validate_schema
from .episode_bindings import BindingContext
from .episode_monitoring import _ASSIGNMENT, _FIELDS, _SNAPSHOT, _same_observation, read_progress
from .execution_contracts import canonical, digest, validate_target
from .practical_execution_state import _immutable, _read
from .progress_records import validate_resource_observation


VERSION = 'bvbrc_appservice_monitor_observation_v1'
PROVIDER = 'bvbrc_appservice.monitor'
_CHOICES = ('query_tasks', 'stdout', 'stderr')
_PREFIX = 'api.bvbrc_appservice.'


def _now():
    return datetime.now(timezone.utc).isoformat()


def _require(condition, code):
    if not condition:
        raise ValueError('appservice_monitor_' + code)


class AppServiceMonitor:
    def __init__(self, execution):
        self.api, self.store = execution, execution.store
        self.custody = execution.appservice.custody

    def _monitor(self, context, *, allow_unsaved=False):
        _require(isinstance(context, BindingContext) and context.role == 'monitor',
                 'saved_context_required')
        self.custody.authenticate(context, allow_unsaved=allow_unsaved)
        assignment = plain(context.assignment)
        validate_schema(assignment, _ASSIGNMENT)
        # Generic custody authenticates monitor records but deliberately does
        # not interpret their inputs. Explicitly verify their actual commission.
        parent, index = self.custody._commission(context)
        return assignment, parent, index

    def _cutoff(self, child, parent, reference):
        cutoff = self.custody._inheritance(child, parent)
        if cutoff is not None:
            row = self.store.db.execute('SELECT 1 FROM runtime_record_receipts '
                'WHERE run_id=? AND episode_id=? AND record_ref=? AND receipt_index<=?',
                (self.api.run_id, parent.episode_id, reference, cutoff)).fetchone()
            _require(row is not None, 'handoff_not_received_before_commission')

    def _relationship(self, snapshot, target, handoff):
        """Authenticate the particular physical dependency, never its basename."""
        for dependency in snapshot['dependencies']:
            if dependency['handle'] != target['handle'] or dependency['kind'] != 'job':
                continue
            _require(self.custody._table('runtime_execution_progress_dependencies'),
                     'dependency_record_missing')
            source = self.store.get(dependency['relation_ref'])
            payload = {key: value for key, value in source.items()
                       if key not in {'id', 'record_type', 'origin'}}
            _require(source.get('record_type') == 'source' and source.get('origin') == 'tool'
                and source.get('provider') == 'execution.progress.relationship'
                and source.get('artifact_ref') == source.get('request_ref')
                and source['id'] == identity('source', {'origin': 'tool', 'record': payload}),
                'dependency_source_conflict')
            value = self.api._artifact_json(source['artifact_ref'])
            expected = {'version': 'execution_resource_dependency_v1', 'run_id': self.api.run_id,
                'owner_episode_id': target['origin_episode_id'],
                'operation_key': handoff['original_task']['submission_operation_key'], 'target': target}
            _require(canonical(value) == canonical(expected), 'dependency_submission_conflict')
            physical = digest({key: target[key] for key in ('run_id', 'origin_episode_id',
                'resource_id', 'resource_kind', 'execution_id', 'request_sha256')})
            row = self.store.db.execute('SELECT target_handle,relationship FROM '
                'runtime_execution_progress_dependencies WHERE run_id=? AND physical_identity=?',
                (self.api.run_id, physical)).fetchone()
            _require(row is not None and row['target_handle'] == target['handle']
                and canonical(json.loads(row['relationship'])) == canonical(dependency),
                'dependency_record_conflict')
            return True
        return False

    def _progress_identity(self, snapshot):
        row = self.store.db.execute('SELECT target_handle,scope,signature FROM '
            'runtime_progress_observations WHERE run_id=? AND progress_ref=?',
            (self.api.run_id, snapshot['progress_ref'])).fetchone()
        signature = content_digest(_same_observation(snapshot))
        _require(row is not None and row['target_handle'] == snapshot['target_handle']
            and row['signature'] == signature
            and snapshot['progress_ref'] == 'progress_' + content_digest({
                'run_id': self.api.run_id, 'target_handle': row['target_handle'],
                'scope': json.loads(row['scope']), 'signature': signature}),
            'dependency_observation_identity_conflict')

    def _dependency(self, parent, target, handoff, *, before, visiting=()):
        """An actual received progress result can carry a specific dependency.

        Own progress reads are synchronous completed actions, so their earlier
        selected index supplies the temporal bound. A typed return additionally
        needs the frozen record prefix at its receiving commission.
        """
        _require(parent.episode_id not in visiting, 'cyclic_dependency_custody')
        visiting = (*visiting, parent.episode_id)
        if parent.role == 'monitor':
            self._monitor(parent)
        if not self.custody._table('runtime_progress_observations'):
            return False
        sql = ('SELECT decision_index,action,result FROM runtime_actions WHERE run_id=? '
            'AND episode_id=? AND result IS NOT NULL AND decision_index>=0')
        args = [self.api.run_id, parent.episode_id]
        if before is not None:
            sql += ' AND decision_index<?'
            args.append(before)
        for row in self.store.db.execute(sql, args):
            action, outcome = json.loads(row['action']), json.loads(row['result'])
            if (action.get('kind') != 'tool' or action.get('tool') not in {'progress.observe', 'progress.read'}
                    or outcome.get('status') not in {'completed', 'partial'}):
                continue
            snapshot = outcome.get('result')
            if not isinstance(snapshot, dict) or snapshot.get('progress_ref') not in outcome.get('progress_refs', []):
                continue
            saved = read_progress(self.store, self.api.run_id, snapshot['progress_ref'], parent.scope)
            validate_schema(saved, _SNAPSHOT)
            _require(canonical(snapshot) == canonical(saved), 'dependency_observation_conflict')
            if action['tool'] == 'progress.observe':
                _require(parent.role == 'monitor'
                    and snapshot['target_handle'] == parent.assignment['target_handle']
                    and 'dependencies' in action.get('arguments', {}).get('requested_fields', []),
                    'dependency_selection_conflict')
                key = f'{self.api.run_id}:{parent.episode_id}:{row["decision_index"]}'
                selected = self.store.db.execute('SELECT selection,signature,progress_ref FROM runtime_progress_selections '
                    'WHERE run_id=? AND operation_key=?', (self.api.run_id, key)).fetchone()
                _require(selected is not None and selected['progress_ref'] == snapshot['progress_ref'],
                         'dependency_selection_missing')
                selection = json.loads(selected['selection'])
                _require(selected['signature'] == content_digest(selection)
                    and selection['target_handle'] == snapshot['target_handle']
                    and canonical(selection['requested_fields']) == canonical(action['arguments']['requested_fields'])
                    and canonical(selection['scope']) == canonical(parent.scope), 'dependency_selection_conflict')
            else:
                _require(action.get('arguments') == {'progress_ref': snapshot['progress_ref']},
                         'dependency_selection_conflict')
            if self._relationship(snapshot, target, handoff):
                self._progress_identity(snapshot)
                return True
        # Only the explicitly requested dependency field transfers this fact.
        # A generic reference or broad stored child context is not a return.
        sql = ('SELECT decision_index FROM runtime_report_attempts WHERE run_id=? '
            'AND parent_episode_id=? AND failure IS NULL AND form IS NOT NULL')
        args = [self.api.run_id, parent.episode_id]
        if before is not None:
            sql += ' AND decision_index<?'
            args.append(before)
        for row in self.store.db.execute(sql, args):
            child, form, schema = self.custody._attempt(parent, row['decision_index'])
            names = [name for name, node in schema['properties'].items()
                if node.get('x-source') == 'monitoring_dependency_handles'
                and node.get('items', {}).get('format') == 'reference'
                and node['items'].get('x-reference-namespace') == 'execution_handle']
            if not any(target['handle'] in form[name] for name in names):
                continue
            if self._dependency(child, target, handoff, before=None, visiting=visiting):
                return 'typed_dependency'
        return False

    def _possession(self, context, target, handoff, *, allow_unsaved=False):
        assignment, parent, index = self._monitor(context, allow_unsaved=allow_unsaved)
        _require(assignment['target_handle'] == target['handle'], 'assigned_target_conflict')
        if parent.role == 'monitor':
            self._monitor(parent)
        if parent.role == 'monitor' and parent.assignment.get('target_handle') == target['handle']:
            # Each real commission independently authenticates its immutable
            # assignment. The chain ends in actual original handoff possession.
            return self._possession(parent, target, handoff)
        try:
            self.custody.possession(parent, target['handle'], before=index)
        except AppServiceCustodyError as error:
            if error.code != 'bvbrc_appservice_custody_input_not_possessed':
                raise
            dependency = self._dependency(parent, target, handoff, before=index)
            _require(bool(dependency), 'handoff_not_possessed_before_commission')
            if dependency == 'typed_dependency':
                self._cutoff(context, parent, target['handle'])
        else:
            self._cutoff(context, parent, target['handle'])

    def resolve_target(self, context, reference):
        """Validate an assigned target or an actually received dependency.

        This is the same original handoff and temporal custody proof used for
        native observation. Initial form validation can precede saving the
        child; only its exact saved parent model selection authorizes that
        interval. Dependencies still require a saved receiving monitor.
        """
        _require(isinstance(context, BindingContext) and context.role == 'monitor',
                 'saved_context_required')
        target = self.api.appservice.read_target(reference, context.scope)
        body = self.api.appservice.read_handoff(reference, context.scope)
        if context.assignment.get('target_handle') == reference:
            self._possession(context, target, body['task_handoff'], allow_unsaved=True)
        else:
            self._monitor(context)
            _require(self._dependency(context, target, body['task_handoff'], before=None),
                     'target_not_received_dependency')
        return True

    def _selection(self, target, native_operation, context, operation_key):
        _require(type(native_operation) is str and native_operation in _CHOICES,
                 'native_operation_required')
        assignment, _, _ = self._monitor(context)
        _require(type(operation_key) is str, 'selected_action_identity_required')
        prefix = f'{self.api.run_id}:{context.episode_id}:'
        suffix = operation_key.removeprefix(prefix)
        _require(operation_key.startswith(prefix) and suffix.isdecimal()
            and str(int(suffix)) == suffix, 'selected_action_identity_required')
        row = self.store.db.execute('SELECT action FROM runtime_actions WHERE run_id=? '
            'AND episode_id=? AND decision_index=?', (self.api.run_id, context.episode_id, int(suffix))).fetchone()
        _require(row is not None, 'selected_action_missing')
        action = json.loads(row['action'])
        arguments = action.get('arguments')
        schema = {'type': 'object', 'additionalProperties': False,
            'properties': {'requested_fields': _FIELDS,
                'native_operation': {'type': 'string', 'enum': list(_CHOICES)}},
            'required': ['requested_fields', 'native_operation']}
        validate_schema(arguments, schema)
        _require(action == {'kind': 'tool', 'tool': 'progress.observe', 'arguments': arguments}
            and arguments['native_operation'] == native_operation
            and set(arguments['requested_fields']) <= set(assignment['requested_fields']),
            'selected_action_conflict')
        original = self.api.appservice.read_target(target['handle'], context.scope)
        _require(canonical(target) == canonical(original), 'target_identity_conflict')
        body = self.api.appservice.read_handoff(target['handle'], context.scope)
        self._possession(context, target, body['task_handoff'])
        return arguments, body

    def _prepare(self, target, native_operation, body):
        suffix = 'status' if native_operation == 'query_tasks' else 'task_info'
        arguments = {'handoff_ref': target['handle']}
        if suffix == 'task_info':
            arguments['file'] = native_operation
        handoff = body['task_handoff']
        bound = validate_contract('BoundInputs', {
            'version': 'bvbrc_appservice_bound_inputs_v1',
            'original_job_owner': handoff['original_job_owner'],
            'resource_id': target['resource_id'], 'request_sha256': digest(target['assignment']['request']),
            'selected_argument_sha256': digest(arguments), 'definition': None, 'inputs': [], 'objects': [],
            'support_receipt_refs': [target['handle']], 'original_handoff_ref': target['handle'],
            'capability': None, 'custody_proof_refs': [target['handle']],
            'resolved': {'operation': _PREFIX + suffix, 'original_task': handoff['original_task']}})
        service = self.api.services[target['resource_id']]
        prepared = service.prepare_observation(target['assignment']['request'],
            {'task_id': handoff['original_task']['task_id']}, scope=target['scope'],
            native_operation=native_operation, bound_inputs=bound)
        _require(prepared['purpose'] == 'observation' and not prepared['mutates_remote']
            and not prepared['effects'], 'unexpected_effect')
        return service, prepared

    def _response(self, directory, intent, service, *, fresh):
        path = directory / 'response.json'
        signature = digest(intent)

        def retain(snapshot, failure):
            _require(snapshot is None or isinstance(snapshot, SourceSnapshot), 'snapshot_required')
            value = {'version': VERSION, 'intent_sha256': signature,
                'snapshot': None if snapshot is None else self.api._snapshot(snapshot), 'failure': failure}
            _immutable(path, value)
            return value

        if path.exists():
            value = _read(path)
        elif not fresh:
            issued = directory / 'issued.json'
            if issued.exists():
                _require(_read(issued)['intent_sha256'] == signature, 'issue_identity_conflict')
            value = retain(None, {'code': 'api_observation_response_unknown' if issued.exists()
                else 'api_observation_not_issued', 'phase': 'recovery'})
        else:
            _immutable(directory / 'issued.json', {'version': VERSION,
                'intent_sha256': signature, 'issued_at': _now()})
            try:
                # This public port is synchronous. Store access and transport
                # stay on its owner thread; no SQLite connection enters a worker.
                snapshot = service.invoke(intent['prepared'])
                _require(isinstance(snapshot, SourceSnapshot), 'snapshot_required')
            except AcquisitionError as error:
                value = retain(error.snapshot, {name: deepcopy(getattr(error, name)) for name in
                    ('code', 'phase', 'retry_after', 'submission_outcome', 'job_ref', 'diagnostic', 'operational')})
            except (asyncio.CancelledError, KeyboardInterrupt, SystemExit) as error:
                if getattr(error, 'snapshot', None) is not None:
                    retain(error.snapshot, None)
                raise
            else:
                value = retain(snapshot, None)
        _require(set(value) == {'version', 'intent_sha256', 'snapshot', 'failure'}
            and value['version'] == VERSION and value['intent_sha256'] == signature,
            'response_identity_conflict')
        snapshot = None if value['snapshot'] is None else self.api._load_snapshot(value['snapshot'])
        return snapshot, value

    def _source(self, intent, response, snapshot):
        metadata = self.store.artifact(canonical({'intent': intent, 'response': response}), 'application/json')
        return self.store.put('source', {'provider': PROVIDER,
            'accession': 'monitor_' + digest(intent), 'uri': snapshot.url,
            'artifact_ref': response['snapshot']['content_ref'], 'text_ref': None,
            'request_ref': metadata, 'version': VERSION, 'retrieved_at': snapshot.retrieved_at,
            'parent_source_refs': [intent['target']['handle']]}, origin='external')['id']

    def _project(self, intent, response, snapshot, service):
        target, choice = intent['target'], intent['native_operation']
        failure = response['failure']
        facts, source, event = {}, None, None
        if snapshot is not None:
            source = self._source(intent, response, snapshot)
            event = self.api._event(service.decode(intent['prepared'], snapshot))
            facts = event['facts']
        # A failed observation request is not a failed scientific execution.
        qualified_query = bool(choice == 'query_tasks' and event is not None
            and event['failure_code'] is None and facts.get('native_task_id') == target['execution_id'])
        observed_state = qualified_query and facts.get('native_status') is not None
        native = {'service': 'bvbrc_appservice', 'kind': 'job',
            'handle': {'task_id': target['execution_id']}, 'operation': choice,
            'state_observed': observed_state, 'source_ref': source,
            'qualification_codes': list(facts.get('qualification_codes', []))}
        if not observed_state:
            native['qualification_codes'] = list(dict.fromkeys([
                *native['qualification_codes'], 'execution_state_not_observed']))
        if qualified_query:
            native.update(native_status=facts['native_status'],
                native_timing=deepcopy(facts['native_timing']),
                timing_representation={'timestamp_timezone': None, 'elapsed_time_unit': 'SQL_TIMEDIFF'})
        if event is not None:
            native['parse_status'] = facts.get('parse_status')
            native['diagnostics'] = [{key: row[key] for key in ('code', 'path', 'severity') if key in row}
                for name in ('diagnostics', 'task_diagnostics', 'rpc_diagnostics')
                for row in facts.get(name, [])]
        if failure is not None:
            native['acquisition_failure'] = {key: failure.get(key) for key in ('code', 'phase')}
        outputs, logs = [], []
        if snapshot is not None:
            native['transport'] = {key: deepcopy(snapshot.transport[key]) for key in
                ('status', 'body_complete', 'received_body_bytes', 'duration_measure', 'http_turnaround_seconds')
                if key in snapshot.transport}
            # Full bytes are retained even for malformed/mismatched replies.
            # Only exact selected successful/partial log representations become
            # readable log windows. HTTP error bodies remain response evidence.
            if choice in ('stdout', 'stderr'):
                try:
                    service._snapshot(intent['prepared'], snapshot)
                except (ValueError, KeyError, TypeError):
                    pass
                else:
                    if (200 <= snapshot.transport['status'] < 300
                            and 'log_windows' in intent['arguments']['requested_fields']):
                        raw = snapshot.content
                        outputs = [{'role': choice, 'available': True, 'bytes': len(raw), 'writer_closed': False}]
                        logs = [{'role': choice, 'path': snapshot.url, 'offset': 0,
                            'observed_size': len(raw), 'bytes_base64': base64.b64encode(raw).decode('ascii')}]
                        native['log_representation'] = 'signature_redacted_http_bytes'
                        native['log_offset_basis'] = 'retained_response_bytes'
        return validate_resource_observation({
            'observed_at': snapshot.retrieved_at if snapshot is not None else intent['started_at'],
            'state': event['state'] if observed_state else 'unknown', 'returncode': None,
            'failure_code': (failure['code'] if failure is not None else
                None if event is None else event['failure_code']), 'result_available': False,
            'measurements': [], 'outputs': outputs, 'logs': logs,
            'provenance_refs': [target['handle'], *([] if source is None else [source])], 'native': native})

    def observe(self, target, *, operation_key, native_operation, observation_context):
        target = validate_target(plain(target))
        arguments, body = self._selection(target, native_operation, observation_context, operation_key)
        service, prepared = self._prepare(target, native_operation, body)
        directory = self.api.directory / 'observations' / digest(operation_key)
        directory.mkdir(parents=True, exist_ok=True)
        original = {'version': VERSION, 'operation_key': operation_key, 'target': target,
            'native_operation': native_operation, 'observation_context': observation_context.as_record(),
            'name': 'progress.observe', 'arguments': arguments, 'prepared': prepared,
            'resource_configuration': deepcopy(service.configuration)}
        with (directory / '.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            path = directory / 'intent.json'
            fresh = not path.exists()
            if fresh:
                intent = {**original, 'started_at': _now()}
                _immutable(path, intent)
            else:
                intent = _read(path)
                _require(canonical({k: v for k, v in intent.items() if k != 'started_at'}) == canonical(original),
                         'operation_key_reused_for_different_work')
            outcome = directory / 'observation.json'
            if outcome.exists():
                return validate_resource_observation(_read(outcome))
            snapshot, response = self._response(directory, intent, service, fresh=fresh)
            value = self._project(intent, response, snapshot, service)
            _immutable(outcome, value)
            return value


__all__ = ['AppServiceMonitor', 'VERSION', 'PROVIDER']
