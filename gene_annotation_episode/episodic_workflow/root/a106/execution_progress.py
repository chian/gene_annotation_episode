"""Scoped observations of original A106 AppService executions, separate from launch.

This is a read-only resource adapter for the existing recursive monitor. It
retains observation custody, never an episode loop, retry, or continuation rule.
"""
from __future__ import annotations

import base64
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from .communication import plain
from .domain import ContractError
from .episode_bindings import native_observation_options
from .execution_contracts import canonical, digest, validate_target
from .progress_records import resource_status, validate_resource_observation


VERSION = 'execution_progress_provider_v1'
_FIELDS = ('execution_status', 'measurements', 'log_windows',
           'committed_record_refs', 'dependencies', 'result_available')
_APPSERVICE_OBSERVATION_SCHEMA = {
    'type': 'object', 'additionalProperties': False,
    'properties': {'native_operation': {'type': 'string',
        'enum': ['query_tasks', 'stdout', 'stderr']}},
    'required': ['native_operation'],
}


def _appservice_target(target):
    assignment = target['assignment']
    if target['resource_kind'] != 'api' or assignment.get('service') != 'bvbrc_appservice':
        return False
    request = assignment.get('request', {})
    if (assignment.get('version') != 'api_service_assignment_v1'
            or request.get('version') != 'bvbrc_appservice_request_v1'
            or request.get('effect_contract') != 'selected_api_effects_v1'):
        raise ContractError('bvbrc_appservice_execution_contract_required')
    return True


def _validate_native_observation(target, native_operation):
    if _appservice_target(target):
        if native_operation is None:
            raise ContractError('bvbrc_appservice_native_operation_required')
        if native_operation not in ('query_tasks', 'stdout', 'stderr'):
            raise ContractError('bvbrc_appservice_native_operation_invalid')
    elif native_operation is not None:
        raise ContractError('progress_native_operation_not_supported')


def _now():
    return datetime.now(timezone.utc).isoformat()


def _without_read_times(value):
    if isinstance(value, dict):
        return {key: _without_read_times(item) for key, item in value.items()
                if key not in {'observed_at', 'retrieved_at'}}
    if isinstance(value, list):
        return [_without_read_times(item) for item in value]
    return value


def describe_execution_target(target):
    assignment = target['assignment']
    request = assignment['request']
    return {'resource_kind': 'api', 'service_or_program': assignment['service'],
        'operation': request['required_application_id'],
        'required_application_id': request['required_application_id'],
        'request_version': request['version'], 'output_format': None,
        'submitted_parameters': deepcopy(request['parameters']),
        'submitted_start_parameters': deepcopy(request['start_parameters']),
        'selected_observation_schema': deepcopy(_APPSERVICE_OBSERVATION_SCHEMA)}


class ExecutionTargetReader:
    def __init__(self, store, *, run_id, directory, resources, api_execution):
        if not isinstance(run_id, str) or not run_id:
            raise ValueError('execution_progress_run_identity_required')
        self.store, self.run_id, self.directory = store, run_id, Path(directory)
        self.resources = json.loads(canonical(resources))
        self.api_execution = api_execution

    def _original_scope(self, handle):
        source = self.store.get(handle)
        if source.get('provider') == 'episode.bvbrc_appservice_receipt':
            if self.api_execution is None:
                raise ValueError('execution_target_unavailable')
            return self.store.validate_scope(self.api_execution.scope(handle))
        for field in ('request_ref', 'artifact_ref'):
            reference = source.get(field)
            if reference is None:
                continue
            try:
                body = json.loads(self.store.get_artifact(reference))
                scope = body.get('scope')
                if scope is None and isinstance(body.get('target'), dict):
                    scope = body['target'].get('scope')
                if scope is not None:
                    return self.store.validate_scope(scope)
            except (ValueError, TypeError, AttributeError):
                continue
        raise ValueError('execution_target_original_scope_unavailable')

    def scope(self, handle):
        try:
            return self.read_target(handle, self._original_scope(handle))['scope']
        except (ValueError, KeyError, OSError) as error:
            raise ContractError('execution_target_unavailable_or_outside_scope',
                detail={'reason': str(error)}) from error

    def read_target(self, handle, scope, *, include_native_receipt=False):
        return self._read_target(handle, scope, include_native_receipt=include_native_receipt)

    def _read_target(self, handle, scope, *, include_native_receipt=False, _receipt_reads=None):
        try:
            if type(include_native_receipt) is not bool:
                raise ValueError('execution_target_receipt_selection_invalid')
            if self.api_execution is None:
                raise ValueError('execution_target_unavailable')
            target = validate_target(self.api_execution.read_target(handle, scope))
            configuration = self.resources.get(target['resource_id'])
            if (target['handle'] != handle or target['run_id'] != self.run_id
                    or target['resource_kind'] != 'api' or configuration is None
                    or configuration['kind'] != 'api'
                    or target['assignment'].get('service') != configuration.get('service')):
                raise ValueError('api_execution_target_resource_conflict')
            if (_appservice_target(target)
                    and configuration.get('execution_contract') != 'bvbrc_appservice_execution_v1'):
                raise ValueError('bvbrc_appservice_execution_contract_required')
            return (target, None) if include_native_receipt else target
        except (ValueError, KeyError, OSError) as error:
            raise ContractError('execution_target_unavailable_or_outside_scope',
                detail={'reason': str(error)}) from error

    def describe_target(self, handle, scope, *, selector=None):
        target = self.read_target(handle, scope)
        value = describe_execution_target(target)
        body = self.api_execution._read_handoff(handle, scope)
        receipt = body.get('receipt', {})
        called = receipt.get('tool_name', receipt.get('name'))
        if not isinstance(called, str) or not called:
            raise ContractError('execution_called_operation_unavailable')
        value.update(called_operation=called, status_operations=[], acquisition_operations=[], extractors=[])
        services = self.api_execution.services
        if target['resource_id'] not in services:
            raise ContractError('bvbrc_appservice_service_not_bound')
        return self._describe_appservice(value, target, body, services[target['resource_id']], selector)

    def _describe_appservice(self, value, target, body, service, selector):
        """Describe exact saved task operands and installed support readers."""
        from .api_bvbrc_appservice import _NATIVE_STATES, _RAW_STATES
        prefix = 'api.bvbrc_appservice.'
        handoff = body['task_handoff']
        original = handoff['original_task']
        implementation = type(service).__module__+'.'+type(service).__qualname__
        available = [row['name'] for row in service.result_capabilities()]
        acquisition = ([] if selector is None else
            [row['name'] for row in service.result_catalog(target['assignment']['request'], selector)])
        value.update(native_application_id=original['native_application_id'],
            definition_evidence=deepcopy(handoff['definition_evidence']),
            submitted_parameters=deepcopy(original['submitted_parameters']),
            submitted_start_parameters=deepcopy(original['submitted_start_parameters']),
            native_observation_methods={
                'query_tasks': {'operation': prefix+'status', 'method': 'AppService.query_tasks'},
                'stdout': {'operation': prefix+'task_info', 'method': 'GET task_info/{task_id}/stdout'},
                'stderr': {'operation': prefix+'task_info', 'method': 'GET task_info/{task_id}/stderr'}},
            status_operations=[name for name in (prefix+'status', prefix+'task_info') if name in available],
            acquisition_operations=acquisition,
            available_result_operations=available,
            native_states={'query_tasks_field': 'status',
                'query_tasks_mapping': deepcopy(_NATIVE_STATES),
                'submission_field': 'state_code', 'submission_mapping': deepcopy(_RAW_STATES),
                'unrecognized_state': 'unknown', 'log_observation_state': 'unknown'},
            progress_measurements={'native_timing_fields': [
                'submit_time', 'start_time', 'completed_time', 'elapsed_time'],
                'native_timing_representation': 'unconverted_native_strings',
                'elapsed_time_format': 'SQL_TIMEDIFF', 'timezone': None,
                'derived_duration_seconds': [], 'derived_log_throughput': None},
            log_format={'representation': 'signature_redacted_http_bytes',
                'offset_basis': 'retained_response_bytes', 'state_observed': False},
            output_association={'task_info_fields': ['job_result_id', 'job_result_folder'],
                'manifest': 'job_result', 'member_selection': 'explicit_output_files_ordinal',
                'immutable_producer_bytes_established_by_path_or_uuid': False},
            configured_scientific_adapters=deepcopy(
                self.resources[target['resource_id']].get('scientific_adapters', [])))
        common = ['monitoring_progress_refs', 'monitoring_execution_state', 'monitoring_result_available']
        value['extractors'] = [{
            'operation': 'progress.observe', 'native_operation': native_operation,
            'implementation': implementation+'.decode',
            'parser': ('gene_annotation_episode.episodic_workflow.root.a106.bvbrc_analysis_protocol.parse_task_records'
                if native_operation == 'query_tasks' else
                'gene_annotation_episode.episodic_workflow.root.a106.bvbrc_appservice_readers.decode_task_info'),
            'parser_signature': ('parse_task_records(value, *, operation, requested_task_ids=None)'
                if native_operation == 'query_tasks' else
                'decode_task_info(content, *, task_id, file)'),
            'return_fields': ['state', 'native_handle', 'result_available', 'facts', 'failure_code'],
            'return_fact_sources': list(common),
        } for native_operation in ('query_tasks', 'stdout', 'stderr')]
        # Only download reaches same-action artifact publication. Status,
        # listing and capability acquisition do not publish scientific results.
        for operation in acquisition:
            download = operation == prefix+'download'
            value['extractors'].append({'operation': operation,
                'implementation': implementation+('.publish' if download else '.decode'),
                'purpose': 'selected_artifact_publication' if download else 'support',
                'return_fact_sources': ['execution_result_refs'] if download else [],
                'return_fields': ['source_ref', 'records'] if download else
                    ['state', 'native_handle', 'result_available', 'facts', 'failure_code'],
                **({'parser': 'gene_annotation_episode.episodic_workflow.root.a106.bvbrc_appservice_readers.qualify_download',
                    'parser_signature': 'qualify_download(snapshot, *, capability, object_binding)',
                    'scientific_parser': None,
                    'scientific_publication_requires_explicit_bound_adapter': True} if download else {})})
        return value

    def _qualified(self, target):
        target = validate_target(target)
        original = self.read_target(target['handle'], target['scope'])
        if canonical(target) != canonical(original):
            raise ContractError('execution_target_identity_conflict')
        return target

    @classmethod
    def _handoff_values(cls, target, body):
        return True, True

    def _handoff_reader(self):
        """Return a detached metadata reader whose reuse ends with its caller."""
        receipts, targets = {}, {}
        def read(handle, scope):
            try:
                key = (self.run_id, handle, canonical(plain(scope)))
            except (ValueError, TypeError, OverflowError, RecursionError):
                target, body = self._read_target(handle, scope, include_native_receipt=True)
                return deepcopy((target, *self._handoff_values(target, body)))
            if key not in targets:
                candidate_receipts = dict(receipts)
                target, body = self._read_target(handle, scope, include_native_receipt=True,
                    _receipt_reads=candidate_receipts)
                usable, returnable = self._handoff_values(target, body)
                receipts.update(candidate_receipts)
                targets[key] = (deepcopy(target), usable, returnable)
            return deepcopy(targets[key])
        return read

    def usable_handoff(self, target):
        self._qualified(target)
        return True

    def returnable_handoff(self, target):
        return self.usable_handoff(target)

    def observe_target(self, target, *, operation_key, native_operation=None,
                       observation_context=None):
        target = self._qualified(target)
        if not isinstance(operation_key, str) or not operation_key:
            raise ContractError('execution_progress_operation_key_required')
        _validate_native_observation(target, native_operation)
        native_options = native_observation_options(native_operation, observation_context)
        try:
            observation = self.api_execution.observe_target(target, operation_key=operation_key,
                **native_options)
        except (ValueError, OSError) as error:
            raise ContractError('execution_target_observation_failed', detail={'reason': str(error)}) from error
        return validate_resource_observation(observation)

class ExecutionProgressProvider:
    """Durable capture and replay for one selected resource observation."""

    def __init__(self, store, *, run_id, directory, resources, api_execution,
                 log_window_bytes, log_roles):
        if type(log_window_bytes) is not int or log_window_bytes <= 0:
            raise ValueError('execution_progress_log_window_bytes_required')
        allowed_logs = {'stdout', 'stderr'}
        if (not isinstance(log_roles, (tuple, list))
                or any(role not in allowed_logs for role in log_roles)
                or len(set(log_roles)) != len(log_roles)):
            raise ValueError('execution_progress_log_roles_required')
        self.store, self.run_id = store, run_id
        self.resources = json.loads(canonical(resources))
        self.directory = Path(directory)
        self.log_window_bytes, self.log_roles = log_window_bytes, tuple(log_roles)
        self.targets = ExecutionTargetReader(store, run_id=run_id, directory=directory,
            resources=resources, api_execution=api_execution)
        self.targets.log_window_bytes, self.targets.log_roles = log_window_bytes, self.log_roles
        with store.transaction():
            store.db.execute('''CREATE TABLE IF NOT EXISTS runtime_execution_progress_operations (
                run_id TEXT NOT NULL, operation_key TEXT NOT NULL, signature TEXT NOT NULL,
                result TEXT NOT NULL, PRIMARY KEY(run_id,operation_key))''')
            store.db.execute('''CREATE TABLE IF NOT EXISTS runtime_execution_progress_custody (
                run_id TEXT NOT NULL, target_handle TEXT NOT NULL, kind TEXT NOT NULL,
                signature TEXT NOT NULL, source_ref TEXT NOT NULL REFERENCES records(id),
                observed_at TEXT NOT NULL, PRIMARY KEY(run_id,target_handle,kind,signature))''')
            store.db.execute('''CREATE TABLE IF NOT EXISTS runtime_execution_progress_snapshots (
                run_id TEXT NOT NULL, target_handle TEXT NOT NULL, scope TEXT NOT NULL,
                signature TEXT NOT NULL, progress_ref TEXT NOT NULL REFERENCES records(id),
                snapshot TEXT NOT NULL, PRIMARY KEY(run_id,target_handle,scope,signature))''')
            store.db.execute('''CREATE TABLE IF NOT EXISTS runtime_execution_progress_dependencies (
                run_id TEXT NOT NULL, physical_identity TEXT NOT NULL,
                target_handle TEXT NOT NULL, relationship TEXT NOT NULL,
                PRIMARY KEY(run_id,physical_identity))''')

    def as_record(self):
        return {'version': VERSION,
            'implementation_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'configuration': {'resources': deepcopy(self.resources),
                'log_window_bytes': self.log_window_bytes, 'log_roles': list(self.log_roles)}}

    def scope(self, handle):
        return self.targets.scope(handle)

    def describe_target(self, handle, scope):
        return self.targets.describe_target(handle, scope)

    def latest_saved_observation(self, handle, scope, *, require_native_state=False):
        """Read saved progress, optionally only an actual native job state."""
        target = self.targets.read_target(handle, scope)
        row = self.store.db.execute(
            "SELECT snapshot FROM runtime_execution_progress_snapshots "
            "WHERE run_id=? AND target_handle=? "
            + ("AND json_extract(snapshot, '$.execution_status.native.native.facts.native_state') "
               "IS NOT NULL " if require_native_state else "") +
            "ORDER BY json_extract(snapshot,'$.observed_at') DESC LIMIT 1",
            (self.run_id, handle)).fetchone()
        if row is None:
            return None
        snapshot = json.loads(row['snapshot'])
        if (snapshot.get('target_handle') != handle
                or snapshot.get('execution_status', {}).get('handle') != handle
                or target['resource_kind'] != 'api'):
            raise ContractError('execution_saved_observation_identity_conflict')
        return snapshot

    def _operation(self, operation_key, selection):
        if operation_key is not None and (not isinstance(operation_key, str) or not operation_key):
            raise ContractError('execution_progress_operation_key_required')
        signature = digest({'selection': selection, 'provider': self.as_record()})
        row = None if operation_key is None else self.store.db.execute(
            'SELECT signature,result FROM runtime_execution_progress_operations '
            'WHERE run_id=? AND operation_key=?', (self.run_id, operation_key)).fetchone()
        if row is not None and row['signature'] != signature:
            raise ContractError('execution_progress_operation_identity_conflict')
        return signature, row

    def _save_operation(self, operation_key, signature, result):
        if operation_key is not None:
            self.store.db.execute('INSERT INTO runtime_execution_progress_operations VALUES(?,?,?,?)',
                (self.run_id, operation_key, signature, canonical(result)))
        return result

    def _source(self, target, kind, body, *, captured, artifact=None, parents=()):
        signature = digest(_without_read_times(body))
        row = self.store.db.execute('SELECT source_ref,observed_at FROM runtime_execution_progress_custody '
            'WHERE run_id=? AND target_handle=? AND kind=? AND signature=?',
            (self.run_id, target['handle'], kind, signature)).fetchone()
        if row is not None:
            return self.store.get(row['source_ref']), row['observed_at']
        metadata = self.store.artifact(canonical(body), 'application/json')
        selected = metadata if artifact is None else artifact
        source = self.store.put('source', {'provider': 'execution.progress.'+kind,
            'accession': None, 'uri': None, 'artifact_ref': selected, 'text_ref': selected,
            'request_ref': metadata, 'version': VERSION, 'retrieved_at': captured,
            'parent_source_refs': [reference for reference in dict.fromkeys([target['handle'], *parents])
                if self.store.get(reference)['record_type'] == 'source']}, origin='tool')
        self.store.db.execute('INSERT INTO runtime_execution_progress_custody VALUES(?,?,?,?,?,?)',
            (self.run_id, target['handle'], kind, signature, source['id'], captured))
        return source, captured

    def observe(self, handle, requested_fields, scope, *, operation_key=None,
                native_operation=None, observation_context=None):
        fields = plain(requested_fields)
        if (not isinstance(fields, list) or any(field not in _FIELDS for field in fields)
                or len(set(fields)) != len(fields)):
            raise ContractError('execution_progress_requested_fields_invalid')
        normalized = self.store.validate_scope(plain(scope))
        selection = {'operation': 'observe', 'handle': handle, 'fields': fields, 'scope': normalized}
        native_options = native_observation_options(native_operation, observation_context)
        if native_options:
            if operation_key is None:
                raise ContractError('execution_progress_operation_key_required')
            selection.update(native_operation=native_operation,
                observation_context=observation_context.as_record())
        # Restore the original selected observation before touching a target,
        # transport, native status, or file. C8 publication may be retried later.
        signature, old = self._operation(operation_key, selection)
        if old is not None:
            return json.loads(old['result'])
        target = self.targets.read_target(handle, normalized)
        _validate_native_observation(target, native_operation)
        selected_key = operation_key or 'unkeyed-observation:'+digest([handle, _now()])
        if _appservice_target(target):
            # The API implementation receives the exact context/native choice, while
            # this layer receives the projection fields. Bind those operands
            # to the same original action before a native observation occurs.
            prefix = f'{self.run_id}:{observation_context.episode_id}:'
            index = selected_key.removeprefix(prefix)
            if (not selected_key.startswith(prefix) or not index.isdecimal()
                    or str(int(index)) != index):
                raise ContractError('execution_progress_selected_action_required')
            selected = self.store.db.execute('SELECT action FROM runtime_actions '
                'WHERE run_id=? AND episode_id=? AND decision_index=?',
                (self.run_id, observation_context.episode_id, int(index))).fetchone()
            expected = {'kind': 'tool', 'tool': 'progress.observe', 'arguments': {
                'requested_fields': fields, 'native_operation': native_operation}}
            if selected is None or canonical(json.loads(selected['action'])) != canonical(expected):
                raise ContractError('execution_progress_selected_fields_conflict')
        # API execution retains durable HTTP intent and response custody. Let its
        # original transaction commit before HTTP, independently of this later
        # projection transaction. Its selected-key replay prevents a second GET.
        observation = self.targets.observe_target(target, operation_key=selected_key, **native_options)
        with self.store.transaction():
            signature, old = self._operation(operation_key, selection)
            if old is not None:
                return json.loads(old['result'])
            captured = observation['observed_at']
            status_source, original_time = self._source(target, 'status', {
                'version': 'execution_progress_observation_v1', 'target': target,
                'observation': observation}, captured=captured)
            provenance = []
            for reference in observation['provenance_refs']:
                recorded = self.store.get(reference)
                if recorded['record_type'] == 'artifact':
                    # A provider's exact HTTP/status artifact has independent
                    # bytes but needs an actual source relationship to cross
                    # Store's ordinary artifact-reference boundary.
                    source, _ = self._source(target, 'provenance', {
                        'version': 'execution_progress_provenance_v1', 'target': target,
                        'original_provenance_ref': reference}, captured=captured,
                        artifact=reference, parents=[status_source['id']])
                    provenance.append(source['id'])
                provenance.append(reference)
            observation['observed_at'] = original_time
            status_observation = observation
            if _appservice_target(target):
                # The full capture already has immutable source custody above.
                # Raw log bytes cross only through requested retained windows,
                # never through resource_status's nested native observation.
                status_observation = deepcopy(observation)
                status_observation['logs'] = []
                if 'log_windows' not in fields:
                    status_observation['outputs'] = [row for row in observation['outputs']
                        if row['role'] not in {'stdout', 'stderr'}]
                if 'measurements' not in fields:
                    status_observation['measurements'] = []
            status = resource_status(target, status_observation)
            measurements = []
            if 'measurements' in fields:
                measurements = [{'name': row['measure'], 'value': row['seconds'], 'unit': 'seconds',
                    'measured_at': original_time, 'provenance_ref': status_source['id']}
                    for row in observation['measurements']]
            windows = []
            if 'log_windows' in fields:
                for row in observation['logs']:
                    if row['role'] not in self.log_roles:
                        continue
                    raw = base64.b64decode(row['bytes_base64'], validate=True)
                    offset = row['offset']
                    if _appservice_target(target):
                        # Native task_info has no remote byte-window contract.
                        # Full response custody is retained by the API implementation;
                        # this caller's existing policy bounds only its window.
                        removed = max(0, len(raw) - self.log_window_bytes)
                        raw, offset = raw[removed:], offset + removed
                    artifact = self.store.artifact(raw)
                    sha = hashlib.sha256(raw).hexdigest()
                    source, stamp = self._source(target, 'log', {
                        'version': 'execution_progress_log_window_v1', 'target': target,
                        'role': row['role'], 'path': row['path'],
                        'original_start_byte': offset,
                        'original_end_byte': offset+len(raw),
                        'observed_file_size': row['observed_size'], 'content_sha256': sha,
                        'whole_file_atomic_snapshot': False}, captured=captured,
                        artifact=artifact, parents=[status_source['id']])
                    windows.append({'source_ref': source['id'], 'artifact_ref': artifact,
                        'start_byte': 0, 'end_byte': len(raw), 'observed_at': stamp,
                        'content_sha256': sha})
            value = {'version': 'progress_snapshot_v1', 'target_handle': handle,
                'observed_at': original_time, 'execution_status': status,
                'measurements': measurements, 'log_windows': windows,
                'committed_record_refs': [], 'dependencies': [],
                'result_available': observation['result_available'],
                'provenance_refs': list(dict.fromkeys([status_source['id'],
                    *provenance, *(row['source_ref'] for row in windows)]))}
            snapshot_signature = digest(_without_read_times(value))
            row = self.store.db.execute('SELECT snapshot FROM runtime_execution_progress_snapshots '
                'WHERE run_id=? AND target_handle=? AND scope=? AND signature=?',
                (self.run_id, handle, canonical(normalized), snapshot_signature)).fetchone()
            if row is not None:
                value = json.loads(row['snapshot'])
            else:
                source, _ = self._source(target, 'snapshot', value, captured=original_time,
                    parents=value['provenance_refs'])
                value['progress_ref'] = source['id']
                self.store.db.execute('INSERT INTO runtime_execution_progress_snapshots VALUES(?,?,?,?,?,?)',
                    (self.run_id, handle, canonical(normalized), snapshot_signature,
                     value['progress_ref'], canonical(value)))
            return self._save_operation(operation_key, signature, value)

    def direct_dependencies(self, handle, scope):
        self.targets.read_target(handle, scope)
        return []

    def dependency_from_outcome(self, source_context, outcome, operation_key):
        """Expose one actual episode→physical relationship after own commit."""
        if source_context.run_id != self.run_id:
            raise ContractError('execution_progress_dependency_outside_run')
        references = list(dict.fromkeys(plain(outcome).get('record_refs', [])))
        eligible = []
        for reference in references:
            try:
                target = self.targets.read_target(reference, source_context.scope)
            except (ValueError, KeyError):
                continue
            if target['origin_episode_id'] != source_context.episode_id:
                continue
            body = self.targets.api_execution._read_handoff(reference, source_context.scope)
            if body['receipt']['operation_key'] != operation_key:
                continue
            # Both resource readers qualify selected facts before publication.
            # A relationship additionally requires the caller's actual own
            # action outcome to have committed, never just its intent/source.
            prefix = f'{self.run_id}:{source_context.episode_id}:'
            index = operation_key.removeprefix(prefix)
            if not operation_key.startswith(prefix) or not index.isdecimal():
                raise ContractError('execution_dependency_selected_action_required')
            selected = self.store.db.execute('SELECT result FROM runtime_actions '
                'WHERE run_id=? AND episode_id=? AND decision_index=?',
                (self.run_id, source_context.episode_id, int(index))).fetchone()
            if (selected is None or selected['result'] is None
                    or reference not in json.loads(selected['result']).get('record_refs', [])):
                raise ContractError('execution_dependency_outcome_not_committed')
            eligible.append(target)
        if not eligible:
            return None
        if len(eligible) != 1:
            raise ContractError('one_execution_dependency_per_selected_outcome_required')
        target = eligible[0]
        with self.store.transaction():
            signature, old = self._operation('dependency:'+operation_key,
                {'operation': 'dependency', 'target': target, 'episode_id': source_context.episode_id})
            if old is not None:
                return json.loads(old['result'])
            physical_identity = digest({key: target[key] for key in (
                'run_id', 'origin_episode_id', 'resource_id', 'resource_kind',
                'execution_id', 'request_sha256')})
            existing = self.store.db.execute('SELECT relationship FROM '
                'runtime_execution_progress_dependencies WHERE run_id=? AND physical_identity=?',
                (self.run_id, physical_identity)).fetchone()
            if existing is not None:
                # Start/status/collect receipts are distinct recorded actions,
                # while their first committed physical relationship retains
                # one original semantic handle, provenance and timestamp.
                return self._save_operation('dependency:'+operation_key, signature,
                    json.loads(existing['relationship']))
            stamp = _now()
            source, stamp = self._source(target, 'relationship', {
                'version': 'execution_resource_dependency_v1', 'run_id': self.run_id,
                'owner_episode_id': source_context.episode_id, 'operation_key': operation_key,
                'target': target}, captured=stamp)
            body = self.targets.api_execution._read_handoff(target['handle'], target['scope'])
            state = {'submitted': 'pending', 'running': 'executing',
                'completed': 'returned'}[body['receipt']['state']]
            result = {'handle': target['handle'], 'kind': 'job', 'relation_ref': source['id'],
                'observed_at': stamp, 'state': state}
            self.store.db.execute('INSERT INTO runtime_execution_progress_dependencies VALUES(?,?,?,?)',
                (self.run_id, physical_identity, target['handle'], canonical(result)))
            return self._save_operation('dependency:'+operation_key, signature, result)


__all__ = ['ExecutionTargetReader', 'ExecutionProgressProvider', 'VERSION', 'describe_execution_target']
