"""Scoped observations of original API/native executions, separate from launch.

This is a read-only resource adapter for the existing recursive monitor. It
owns observation custody, never an episode loop, retry, or continuation rule.
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
from .practical_execution_operations import LocalPracticalOperations
from .terminal_execution import TerminalExecution
from .practical_execution_records import terminal_job_matches
from .practical_receipt_information import PracticalReceiptInformation, PROVIDER
from .progress_records import resource_status, validate_resource_observation


VERSION = 'execution_progress_provider_v1'
_FIELDS = ('execution_status', 'measurements', 'log_windows',
           'committed_record_refs', 'dependencies', 'result_available')
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
    """Describe a validated original target without a fresh status/file read."""
    assignment = target['assignment']
    fba = assignment['requested_job'].get('native_flux_balance')
    if fba is not None:
        return {'resource_kind': target['resource_kind'],
            'service_or_program': fba['operation'], 'operation': fba['operation'],
            'mode': fba['mode'], 'input_format': fba['model_input']['format'],
            'output_format': 'flux_balance_native_manifest_v1'}
    return {'resource_kind': target['resource_kind'],
            'service_or_program': assignment['requested_job']['argv'][0],
            'operation': None, 'output_format': None}


class ExecutionTargetReader:
    """Validate source/run/scope/request first; observe exactly its native ID."""

    def __init__(self, store, *, run_id, directory, resources):
        if not isinstance(run_id, str) or not run_id:
            raise ValueError('execution_progress_run_identity_required')
        self.store, self.run_id, self.directory = store, run_id, Path(directory)
        self.resources = json.loads(canonical(resources))
        self.receipts = PracticalReceiptInformation(store, run_id)
        self.operations = {}
        for resource_id, configuration in self.resources.items():
            kind = configuration.get('kind')
            if kind == 'local':
                self.operations[resource_id] = LocalPracticalOperations({key: value
                    for key, value in configuration.items() if key not in {
                        'launch_prompt_entry', 'launch_prompt_sections', 'scheduler'}})
            elif kind == 'pbs_ssh':
                self.operations[resource_id] = TerminalExecution(configuration)
            else:
                raise ValueError('unsupported_execution_progress_resource')

    def _original_scope(self, handle):
        source = self.store.get(handle)
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

    def _read_native_receipt(self, reference, scope, reads):
        """Reuse only successful immutable receipt reads in one metadata operation."""
        try:
            key = (self.run_id, reference, canonical(plain(scope)))
        except (ValueError, TypeError, OverflowError, RecursionError):
            # Invalid/non-JSON selections retain the original reader’s errors.
            return self.receipts.read(reference, scope)
        if key not in reads:
            reads[key] = deepcopy(self.receipts.read(reference, scope))
        return deepcopy(reads[key])

    def _native(self, handle, scope, *, _seen=(), _receipt_reads=None):
        if handle in _seen:
            raise ValueError('native_flux_balance_receipt_ancestry_cycle')
        reads = {} if _receipt_reads is None else _receipt_reads
        body = self._read_native_receipt(handle, scope, reads)
        source = self.store.get(handle)
        snapshot = json.loads(self.store.get_artifact(source['request_ref']))
        assignment, receipt = snapshot['assignment'], body['receipt']
        job = receipt['outcome'].get('facts', {}).get('requested_job')
        terminal = receipt['tool_name'] == 'exec_command'
        if terminal:
            if not terminal_job_matches(assignment, receipt['outcome']):
                raise ValueError('execution_command_native_job_identity_conflict')
        elif (receipt['tool_name'] not in {'practical.job.start', 'practical.job.status', 'practical.job.collect'}
                or not isinstance(job, dict) or not isinstance(job.get('handoff'), dict)
                or job.get('requested_job_sha256') != digest(assignment['requested_job'])
                or job.get('argv') != assignment['requested_job']['argv']
                or job.get('environment') != assignment['requested_job']['environment']
                or job.get('resource_kind') != assignment['resource_kind']
                or job.get('execution_id') != job['handoff'].get('execution_id')
                or job['handoff'].get('monitor_operation') != 'practical.job.status'
                or job['handoff'].get('results_operation') != 'practical.job.collect'):
            raise ValueError('practical_execution_handoff_identity_conflict')
        resource_id = assignment.get('resource_id')
        if resource_id is None:
            # Legacy assignments predate resource IDs. A single exact bound
            # resource is unambiguous; several candidates are never selected.
            candidates = [key for key, config in self.resources.items()
                if config['kind'] == ('local' if assignment['resource_kind'] == 'local' else 'pbs_ssh')
                and Path(assignment['workspace']).is_relative_to(config['workspace'])]
            if len(candidates) != 1:
                raise ValueError('practical_execution_resource_identity_required')
            resource_id = candidates[0]
        config = self.resources.get(resource_id)
        if (config is None or config['kind'] != ('local' if assignment['resource_kind'] == 'local' else 'pbs_ssh')
                or not Path(assignment['workspace']).is_relative_to(config['workspace'])):
            raise ValueError('practical_execution_resource_identity_conflict')
        origin_episode_id = body['episode_id']
        if terminal:
            self.operations[resource_id].validate_assignment(assignment)
            target = validate_target({'version': 'execution_target_v1', 'handle': handle,
                'run_id': self.run_id, 'resource_id': resource_id,
                'resource_kind': assignment['resource_kind'], 'execution_id': job['execution_id'],
                'request_sha256': digest(assignment['requested_job']),
                'origin_episode_id': origin_episode_id, 'assignment': assignment, 'scope': body['scope']})
            return target, body
        if 'native_flux_balance' in assignment['requested_job']:
            from .flux_balance_contracts import validate_flux_balance_record
            if assignment.get('resource_id') != resource_id or assignment['resource_kind'] != 'local':
                raise ValueError('native_flux_balance_resource_identity_conflict')
            self.operations[resource_id].validate_assignment(assignment)
            detail = receipt['outcome'].get('native_outcome') or {}
            file = validate_flux_balance_record('File', detail.get('native_flux_balance_input_binding_file'))
            if (file['format'] != 'flux_balance_input_binding_receipt_v1'
                    or file['artifact_ref'] != 'artifact_' + file['sha256']):
                raise ValueError('native_flux_balance_original_input_control_conflict')
            reference = receipt['arguments'].get('receipt_ref')
            if reference is not None:
                if receipt['tool_name'] not in {'practical.job.status', 'practical.job.collect'}:
                    raise ValueError('native_flux_balance_receipt_ancestry_conflict')
                original, prior = self._native(reference, body['scope'], _seen=(*_seen, handle), _receipt_reads=reads)
                prior_detail = prior['receipt']['outcome'].get('native_outcome') or {}
                if (original['resource_id'] != resource_id or original['execution_id'] != job['execution_id']
                        or original['assignment']['workspace'] != assignment['workspace']
                        or canonical(original['assignment']['requested_job']) != canonical(assignment['requested_job'])
                        or any(detail.get(key) != prior_detail.get(key) for key in (
                            'attempt_id', 'attempt_operation_key', 'native_flux_balance_input_binding_file'))):
                    raise ValueError('native_flux_balance_receipt_ancestry_conflict')
                assignment = original['assignment']
                origin_episode_id = original['origin_episode_id']
            operation_key = detail.get('attempt_operation_key')
            attempt_id = detail.get('attempt_id')
            prefix = f'{self.run_id}:{origin_episode_id}:'
            index = operation_key.removeprefix(prefix) if isinstance(operation_key, str) else ''
            root = Path(assignment['workspace']) / '.episode-operations' / digest({
                'run': self.run_id, 'episode': origin_episode_id}) / digest(operation_key)
            observed = detail.get('observation', detail)
            if (not isinstance(operation_key, str) or not operation_key.startswith(prefix)
                    or not index.isdecimal() or str(int(index)) != index
                    or attempt_id != digest(operation_key) or job['execution_id'] != str(root / 'native.json')
                    or observed.get('metadata', {}).get('policy') != self.operations[resource_id].policy.to_dict()):
                raise ValueError('native_flux_balance_original_attempt_mismatch')
            # Join frozen original start custody, without opening native controls
            # or re-resolving any current scientific source.
            starts = self.receipts._sources(self.receipts._accession(origin_episode_id, operation_key))
            if len(starts) != 1:
                raise ValueError('native_flux_balance_original_start_receipt_missing')
            start = self._read_native_receipt(starts[0]['id'], body['scope'], reads)
            start_receipt = start['receipt']
            start_job = start_receipt['outcome'].get('facts', {}).get('requested_job', {})
            start_detail = start_receipt['outcome'].get('native_outcome') or {}
            if (start['episode_id'] != origin_episode_id or start['assignment_sha256'] != digest(assignment)
                    or start_receipt['tool_name'] != 'practical.job.start'
                    or start_receipt['operation_key'] != operation_key
                    or start_job.get('execution_id') != job['execution_id']
                    or start_job.get('resource_kind') != 'local'
                    or start_job.get('requested_job_sha256') != digest(assignment['requested_job'])
                    or start_job.get('argv') != assignment['requested_job']['argv']
                    or start_job.get('environment') != assignment['requested_job']['environment']
                    or any(start_detail.get(key) != detail.get(key) for key in (
                        'attempt_id', 'attempt_operation_key', 'native_flux_balance_input_binding_file'))):
                raise ValueError('native_flux_balance_original_start_receipt_conflict')
        if assignment['resource_kind'] == 'hpc':
            original_ref = (receipt['arguments'].get('receipt_ref')
                            or receipt['outcome'].get('recovered_original_handoff_ref'))
            if original_ref:
                original = self.read_target(original_ref, scope)
                if (original['assignment'] != assignment or original['execution_id'] != job['execution_id']
                        or original['resource_id'] != resource_id):
                    raise ValueError('hpc_recovered_original_execution_conflict')
                origin_episode_id = original['origin_episode_id']
            detail = receipt['outcome'].get('native_outcome')
            if (not isinstance(detail, dict) or detail.get('pbs_job_id') != job['execution_id']
                    or not isinstance(detail.get('attempt_id'), str)
                    or len(detail['attempt_id']) != 64
                    or detail.get('account') != config['account']):
                raise ValueError('practical_execution_original_attempt_required')
        target = validate_target({'version': 'execution_target_v1', 'handle': handle,
            'run_id': self.run_id, 'resource_id': resource_id,
            'resource_kind': assignment['resource_kind'], 'execution_id': job['execution_id'],
            'request_sha256': digest(assignment['requested_job']),
            'origin_episode_id': origin_episode_id, 'assignment': assignment, 'scope': body['scope']})
        return target, body

    def read_target(self, handle, scope, *, include_native_receipt=False):
        return self._read_target(handle, scope, include_native_receipt=include_native_receipt)

    def _read_target(self, handle, scope, *, include_native_receipt=False, _receipt_reads=None):
        try:
            if type(include_native_receipt) is not bool:
                raise ValueError('execution_target_receipt_selection_invalid')
            source = self.store.get(handle)
            if source.get('provider') == PROVIDER:
                target, receipt = (self._native(handle, scope) if _receipt_reads is None else
                    self._native(handle, scope, _receipt_reads=_receipt_reads))
                return (target, receipt) if include_native_receipt else target
            raise ValueError('execution_target_unavailable')
        except (ValueError, KeyError, OSError) as error:
            raise ContractError('execution_target_unavailable_or_outside_scope',
                detail={'reason': str(error)}) from error

    def describe_target(self, handle, scope, *, selector=None):
        """Actual called-operation identity and available deterministic readers.

        This is information about already selected work and bound implementations,
        not task instructions, an observation, a parser choice or a new library.
        """
        target = self.read_target(handle, scope)
        value = describe_execution_target(target)
        source = self.store.get(handle)
        body = json.loads(self.store.get_artifact(source['artifact_ref']))
        receipt = body.get('receipt', {})
        called = receipt.get('tool_name', receipt.get('name'))
        if not isinstance(called, str) or not called:
            raise ContractError('execution_called_operation_unavailable')
        value.update(called_operation=called, status_operations=[], acquisition_operations=[], extractors=[])
        implementation = type(self.operations[target['resource_id']])
        value['status_operations'] = ['progress.observe']
        value['acquisition_operations'] = ['execution.results.status', 'execution.results.collect', 'execution.results.read']
        value['extractors'] = [{
            'operation': 'progress.observe',
            'implementation': implementation.__module__+'.'+implementation.__qualname__+'.observe_execution',
            'return_fields': ['state', 'returncode', 'failure_code', 'result_available', 'measurements', 'outputs', 'logs'],
            'return_fact_sources': ['monitoring_progress_refs', 'monitoring_execution_state', 'monitoring_result_available'],
        }, {
            'operation': 'execution.results.read',
            'implementation': implementation.__module__+'.'+implementation.__qualname__+'.read_output',
            'return_fields': ['path', 'offset', 'returned_bytes', 'size_bytes', 'bytes_base64', 'text_utf8'],
            'return_fact_sources': ['execution_result_refs', 'execution_result_origin'],
        }]
        return value

    def _qualified(self, target):
        target = validate_target(target)
        original = self.read_target(target['handle'], target['scope'])
        if canonical(target) != canonical(original):
            raise ContractError('execution_target_identity_conflict')
        return target

    def _native_identity(self, target):
        _, body = self._native(target['handle'], target['scope'])
        receipt = body['receipt']
        detail = receipt['outcome'].get('native_outcome') or {}
        if target['resource_kind'] == 'hpc' and receipt['tool_name'] == 'exec_command':
            return {'run_id': self.run_id, 'origin_episode_id': target['origin_episode_id'],
                'resource_id': target['resource_id'], 'requested_job_sha256': target['request_sha256'],
                'actual_job': deepcopy(detail['actual_job'])}
        value = {'run_id': self.run_id, 'origin_episode_id': target['origin_episode_id'],
            'attempt_id': detail.get('attempt_id'),
            'original_operation_key': detail.get('attempt_operation_key') or (
                receipt['operation_key'] if digest(receipt['operation_key']) == detail.get('attempt_id') else None)}
        if 'native_flux_balance' in target['assignment']['requested_job']:
            value.update(resource_id=target['resource_id'], requested_job_sha256=target['request_sha256'])
        if 'native_flux_balance' in target['assignment']['requested_job']:
            value['native_flux_balance_input_binding_file'] = detail['native_flux_balance_input_binding_file']
        return value

    @staticmethod
    def _failed_handoff_profile(target):
        return (target['resource_kind'] == 'local'
            and 'native_flux_balance' in target['assignment']['requested_job'])

    @classmethod
    def _handoff_values(cls, target, body):
        """Decide only from an already qualified original stored receipt."""
        status = body['receipt']['outcome']['facts']['requested_job']['status']
        usable = status in {'submitted', 'running', 'completed'}
        return usable, usable or status == 'failed' and cls._failed_handoff_profile(target)

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
        """Original endpoint evidence; a later failure cannot rewrite it."""
        target = self._qualified(target)
        _, body = self._native(target['handle'], target['scope'])
        return self._handoff_values(target, body)[0]

    def returnable_handoff(self, target):
        """An authenticated failed native attempt can own qualified partial work."""
        target = self._qualified(target)
        if self.usable_handoff(target):
            return True
        if not self._failed_handoff_profile(target):
            return False
        _, body = self._native(target['handle'], target['scope'])
        return self._handoff_values(target, body)[1]

    def observe_target(self, target, *, operation_key, native_operation=None,
                       observation_context=None):
        target = self._qualified(target)
        if not isinstance(operation_key, str) or not operation_key:
            raise ContractError('execution_progress_operation_key_required')
        if native_operation is not None:
            raise ContractError('progress_native_operation_not_supported')
        native_options = native_observation_options(native_operation, observation_context)
        from .terminal_scientific_evidence import is_terminal_target, terminal_observation
        if is_terminal_target(target):
            _, body = self._native(target['handle'], target['scope'])
            proof = body['receipt']['outcome']['native_outcome']['scientific_command_proof']
            return validate_resource_observation(terminal_observation(target, proof))
        try:
            observation = self.operations[target['resource_id']].observe_execution(
                target['assignment'], target['execution_id'], **self._native_identity(target),
                log_window_bytes=getattr(self, 'log_window_bytes', 8192),
                log_roles=getattr(self, 'log_roles', ('stdout', 'stderr')))
        except (ValueError, OSError) as error:
            raise ContractError('execution_target_observation_failed', detail={'reason': str(error)}) from error
        return validate_resource_observation(observation)

    def read_file(self, target, *, path, offset, limit, operation_key=None):
        target = self._qualified(target)
        from .terminal_scientific_evidence import is_terminal_target, verified_snapshot_path
        if is_terminal_target(target):
            _, body = self._native(target['handle'], target['scope'])
            proof = body['receipt']['outcome']['native_outcome']['scientific_command_proof']
            matches = [row for row in proof['output_snapshots'] if row['path'] == path]
            if not matches:
                matches = [row for row in proof['input_snapshots'] if row['path'] == path]
            if len(matches) != 1 or not matches[0]['available']:
                raise FileNotFoundError(path)
            if type(offset) is not int or offset < 0 or type(limit) is not int or limit < 1:
                raise ValueError('native_output_window_invalid')
            actual = matches[0]
            with verified_snapshot_path(actual).open('rb') as stream:
                stream.seek(offset)
                raw = stream.read(limit)
            import base64
            return {'path': path, 'offset': offset, 'returned_bytes': len(raw),
                'size_bytes': actual['size_bytes'], 'bytes_base64': base64.b64encode(raw).decode('ascii')}
        manifest = target['assignment'].get('scientific_manifest')
        if target['resource_kind'] == 'hpc' and isinstance(manifest, dict) and manifest['path'] == path:
            _, body = self._native(target['handle'], target['scope'])
            detail = body['receipt']['outcome']['native_outcome']
            snapshots = [row for row in detail.get('input_snapshots', []) if row['path'] == path]
            if (len(snapshots) != 1 or not snapshots[0]['available']
                    or not snapshots[0]['source_stable_during_read']
                    or snapshots[0]['sha256'] != manifest['sha256']
                    or snapshots[0]['size_bytes'] != manifest['size_bytes']):
                raise ValueError('native_database_original_manifest_snapshot_unavailable')
            value = self.operations[target['resource_id']].read_output(target['assignment'],
                target['execution_id'], path=snapshots[0]['captured_path'], offset=offset,
                limit=limit, **self._native_identity(target))
            return {**value, 'path': path}
        return self.operations[target['resource_id']].read_output(target['assignment'],
            target['execution_id'], path=path, offset=offset, limit=limit,
            **self._native_identity(target))

class ExecutionProgressProvider:
    """Durable capture and replay for one selected resource observation."""

    def __init__(self, store, *, run_id, directory, resources,
                 log_window_bytes, log_roles):
        if type(log_window_bytes) is not int or log_window_bytes <= 0:
            raise ValueError('execution_progress_log_window_bytes_required')
        allowed_logs = {'stdout', 'stderr'}
        for configuration in resources.values():
            if configuration.get('kind') == 'local' and configuration.get('native_flux_balance'):
                from .native_flux_balance_bindings import validate_flux_balance_bindings
                if validate_flux_balance_bindings(configuration['native_flux_balance']):
                    allowed_logs.add('native_log')
        if (not isinstance(log_roles, (tuple, list))
                or any(role not in allowed_logs for role in log_roles)
                or len(set(log_roles)) != len(log_roles)):
            raise ValueError('execution_progress_log_roles_required')
        self.store, self.run_id = store, run_id
        self.resources = json.loads(canonical(resources))
        self.directory = Path(directory)
        self.log_window_bytes, self.log_roles = log_window_bytes, tuple(log_roles)
        self.targets = ExecutionTargetReader(store, run_id=run_id, directory=directory,
            resources=resources)
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
        if native_operation is not None:
            raise ContractError('progress_native_operation_not_supported')
        selected_key = operation_key or 'unkeyed-observation:'+digest([handle, _now()])
        with self.store.transaction():
            signature, old = self._operation(operation_key, selection)
            if old is not None:
                return json.loads(old['result'])
            # Serialize competing recovery of this selected observation before
            # the sole native read, just as the ordinary progress provider does
            # for immutable selections. The transaction owns no launch state.
            observation = self.targets.observe_target(target, operation_key=selected_key, **native_options)
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
            _, body = self.targets._native(reference, source_context.scope)
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
                # Historical receipt field retains its original hash; it selects no binding.
                'owner_episode_id': source_context.episode_id, 'operation_key': operation_key,
                'target': target}, captured=stamp)
            _, body = self.targets._native(target['handle'], source_context.scope)
            state = {'submitted': 'pending', 'running': 'executing',
                'completed': 'returned', 'failed': 'returned', 'unknown': 'pending'}[
                    body['receipt']['outcome']['facts']['requested_job']['status']]
            result = {'handle': target['handle'], 'kind': 'job', 'relation_ref': source['id'],
                'observed_at': stamp, 'state': state}
            self.store.db.execute('INSERT INTO runtime_execution_progress_dependencies VALUES(?,?,?,?)',
                (self.run_id, physical_identity, target['handle'], canonical(result)))
            return self._save_operation('dependency:'+operation_key, signature, result)


__all__ = ['ExecutionTargetReader', 'ExecutionProgressProvider', 'VERSION', 'describe_execution_target']
