"""Read-only native homology progress with durable, bounded source custody.

This adapter observes already registered work. It does not establish execution,
extract scientific results, publish episode returns or assign information credit.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path

from method_loop.durable import content_digest, validate_commission

from .communication import plain
from .domain import ContractError, canonical
from .homology_jobs import HomologyJobs, OUTPUTS, normalize_query_fasta
from .progress_records import job_status


VERSION = 'homology_progress_provider_v1'
_FIELDS = ('execution_status', 'measurements', 'log_windows',
           'committed_record_refs', 'dependencies', 'result_available')
_LOG_ROLES = ('native_text', 'native_stderr')


def _now():
    return datetime.now(timezone.utc).isoformat()


class HomologyProgressProvider:
    def __init__(self, store, jobs: HomologyJobs, *, run_id,
                 log_window_bytes, log_roles):
        if not isinstance(run_id, str) or not run_id:
            raise ValueError('homology_progress_run_identity_required')
        if type(log_window_bytes) is not int or log_window_bytes <= 0:
            raise ValueError('homology_progress_log_window_bytes_required')
        if (type(log_roles) is not tuple
                or any(type(role) is not str or role not in _LOG_ROLES for role in log_roles)
                or len(set(log_roles)) != len(log_roles)):
            raise ValueError('homology_progress_log_roles_required')
        self.store, self.jobs, self.run_id = store, jobs, run_id
        self.log_window_bytes, self.log_roles = log_window_bytes, log_roles
        self._configuration = deepcopy(jobs.config)
        self._configuration_sha256 = content_digest(self._configuration)
        with store.transaction():
            store.db.execute('''CREATE TABLE IF NOT EXISTS runtime_homology_progress_custody (
                run_id TEXT NOT NULL, registry_ref TEXT NOT NULL, target_handle TEXT NOT NULL,
                kind TEXT NOT NULL, signature TEXT NOT NULL,
                source_ref TEXT NOT NULL REFERENCES records(id), observed_at TEXT NOT NULL,
                PRIMARY KEY(run_id,registry_ref,target_handle,kind,signature))''')
            store.db.execute('''CREATE TABLE IF NOT EXISTS runtime_homology_progress_snapshots (
                run_id TEXT NOT NULL, registry_ref TEXT NOT NULL, target_handle TEXT NOT NULL,
                scope TEXT NOT NULL, signature TEXT NOT NULL,
                progress_ref TEXT NOT NULL REFERENCES records(id), snapshot TEXT NOT NULL,
                PRIMARY KEY(run_id,registry_ref,target_handle,scope,signature))''')
            store.db.execute('''CREATE TABLE IF NOT EXISTS runtime_homology_progress_operations (
                run_id TEXT NOT NULL, operation_key TEXT NOT NULL, signature TEXT NOT NULL,
                result TEXT NOT NULL, PRIMARY KEY(run_id,operation_key))''')

    def as_record(self):
        return {'version': VERSION,
            'implementation_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'registry_ref': self._configuration['registry_ref'],
            'registry_configuration_sha256': self._configuration_sha256,
            'configuration': {'log_window_bytes': self.log_window_bytes,
                              'log_roles': list(self.log_roles)}}

    def _order(self, handle):
        if not isinstance(handle, str) or not handle:
            raise ContractError('homology_progress_target_handle_required')
        if content_digest(self.jobs.config) != self._configuration_sha256:
            raise ContractError('homology_progress_registry_configuration_changed')
        try:
            row = self.jobs._row(handle)
        except ValueError as error:
            raise ContractError('homology_progress_target_unavailable') from error
        return {key: row[key] for key in
                ('job_ref', 'operation_key', 'query_ref', 'query_fasta', 'cpu', 'search_mode')}

    def _query_scope(self, row):
        query = self.store.get(row['query_ref'])
        roots, coverage = self.store.roots(row['query_ref']), self.store.coverage(row['query_ref'])
        if (not roots or not coverage or not query.get('sequence_ref')
                or self.store.subject_unit(row['query_ref']) != 'aa'):
            raise ContractError('homology_progress_query_scope_unavailable')
        symbols = self.store.get_artifact(query['sequence_ref']).decode('ascii')
        if normalize_query_fasta('>query\n' + symbols + '\n') != row['query_fasta']:
            raise ContractError('homology_progress_query_identity_conflict')
        return self.store.validate_scope({'subject_refs': roots, 'segments': coverage})

    def scope(self, handle):
        """Return only the registered query's actual original-target geometry."""
        return self._query_scope(self._order(handle))

    def _target(self, handle, scope):
        row = self._order(handle)
        target_scope = self._query_scope(row)
        normalized = self.store.validate_scope(plain(scope))
        if not self.store.scope_contains(normalized, target_scope):
            raise ContractError('homology_progress_target_outside_scope')
        return row, normalized

    def _source(self, provider, body, *, query_ref, observed_at, artifact=None, parents=()):
        metadata = self.store.artifact(canonical(body), 'application/json')
        selected = metadata if artifact is None else artifact
        return self.store.put('source', {'provider': provider, 'accession': None, 'uri': None,
            'artifact_ref': selected, 'text_ref': selected,
            'request_ref': metadata, 'version': VERSION, 'retrieved_at': observed_at,
            'operand_refs': [query_ref], 'parent_source_refs': list(parents)}, origin='tool')

    def _custody(self, handle, kind, signature):
        return self.store.db.execute('SELECT source_ref,observed_at FROM '
            'runtime_homology_progress_custody WHERE run_id=? AND registry_ref=? '
            'AND target_handle=? AND kind=? AND signature=?',
            (self.run_id, self._configuration['registry_ref'], handle, kind, signature)).fetchone()

    def _save_custody(self, handle, kind, signature, source):
        self.store.db.execute('INSERT INTO runtime_homology_progress_custody VALUES(?,?,?,?,?,?,?)',
            (self.run_id, self._configuration['registry_ref'], handle, kind, signature,
             source['id'], source['retrieved_at']))
        return source['id'], source['retrieved_at']

    def _status_source(self, row, status, captured):
        body = {'version': 'homology_progress_native_status_v1', 'native_status': status,
                'order': row, 'registry_configuration': self._configuration,
                'registry_configuration_sha256': self._configuration_sha256}
        signature = content_digest(body)
        old = self._custody(row['job_ref'], 'status', signature)
        if old is not None:
            return old['source_ref'], old['observed_at']
        source = self._source('homology.progress.status', {**body, 'observed_at': captured},
            query_ref=row['query_ref'], observed_at=captured)
        return self._save_custody(row['job_ref'], 'status', signature, source)

    def _read_log(self, row, output, status_source, captured):
        role = output['role']
        path = self.jobs.directory / row['job_ref'] / OUTPUTS[role]
        try:
            with path.open('rb') as stream:
                observed_size = os.fstat(stream.fileno()).st_size
                start = max(0, observed_size - self.log_window_bytes)
                stream.seek(start)
                retained = stream.read(observed_size - start)
        except OSError as error:
            raise ContractError('homology_progress_log_read_failed', detail={
                'job_ref': row['job_ref'], 'role': role,
                'exception_type': type(error).__name__}) from error
        digest = hashlib.sha256(retained).hexdigest()
        # Repeated bytes at the same original interval retain their first
        # timestamp and status provenance. Different intervals remain distinct.
        signature = content_digest({'role': role, 'content_sha256': digest,
            'original_start_byte': start, 'original_end_byte': start + len(retained)})
        old = self._custody(row['job_ref'], 'log:' + role, signature)
        if old is None:
            artifact = self.store.artifact(retained)
            body = {'version': 'homology_progress_log_window_v1', 'job_ref': row['job_ref'],
                'registry_ref': self._configuration['registry_ref'], 'order': row,
                'registry_configuration_sha256': self._configuration_sha256,
                'status_source_ref': status_source, 'role': role, 'path': str(path),
                'original_start_byte': start, 'original_end_byte': start + len(retained),
                'observed_file_size': observed_size, 'status_output_bytes': output['bytes'],
                'retained_bytes': len(retained), 'content_sha256': digest,
                'observed_at': captured, 'whole_file_atomic_snapshot': False}
            source = self._source('homology.progress.log', body, query_ref=row['query_ref'],
                observed_at=captured, artifact=artifact, parents=[status_source])
            reference, captured = self._save_custody(row['job_ref'], 'log:' + role, signature, source)
        else:
            reference, captured = old['source_ref'], old['observed_at']
            artifact = self.store.get(reference)['artifact_ref']
        return {'source_ref': reference, 'artifact_ref': artifact, 'start_byte': 0,
                'end_byte': len(retained), 'observed_at': captured, 'content_sha256': digest}

    def _operation(self, operation_key, selection):
        if operation_key is not None and (not isinstance(operation_key, str) or not operation_key):
            raise ContractError('homology_progress_operation_key_required')
        signature = content_digest({**selection, 'provider': self.as_record()})
        old = None if operation_key is None else self.store.db.execute(
            'SELECT signature,result FROM runtime_homology_progress_operations '
            'WHERE run_id=? AND operation_key=?', (self.run_id, operation_key)).fetchone()
        if old is not None and old['signature'] != signature:
            raise ContractError('homology_progress_operation_identity_conflict')
        return signature, old

    def _save_operation(self, operation_key, signature, result):
        if operation_key is not None:
            self.store.db.execute('INSERT INTO runtime_homology_progress_operations VALUES(?,?,?,?)',
                (self.run_id, operation_key, signature, canonical(result)))
        return result

    def observe(self, handle, requested_fields, scope, *, operation_key=None):
        fields = plain(requested_fields)
        if (not isinstance(fields, list) or any(field not in _FIELDS for field in fields)
                or len(fields) != len(set(fields))):
            raise ContractError('homology_progress_requested_fields_invalid')
        normalized = self.store.validate_scope(plain(scope))
        selection = {'operation': 'observe', 'handle': handle, 'requested_fields': fields,
                     'scope': normalized}
        with self.store.transaction():
            operation_signature, old = self._operation(operation_key, selection)
            if old is not None:
                return json.loads(old['result'])
            row, normalized = self._target(handle, normalized)
            captured = _now()
            native = plain(self.jobs.status(handle))
            if native.get('registry_ref') != self._configuration['registry_ref']:
                raise ContractError('homology_progress_status_registry_mismatch')
            status = job_status(handle, native, observed_at=captured)
            status_source, status_time = self._status_source(row, native, captured)
            status['observed_at'] = status_time
            measurements = []
            if 'measurements' in fields:
                measurements = [{'name': 'elapsed_seconds', 'value': native['elapsed_seconds'],
                    'unit': 'seconds', 'measured_at': status_time, 'provenance_ref': status_source}]
                measurements.extend({'name': output['role'] + '_bytes', 'value': output['bytes'],
                    'unit': 'bytes', 'measured_at': status_time, 'provenance_ref': status_source}
                    for output in native['outputs'])
            logs = []
            if 'log_windows' in fields:
                outputs = {output['role']: output for output in native['outputs']}
                for role in self.log_roles:
                    output = outputs.get(role)
                    if output is not None and output['available']:
                        logs.append(self._read_log(row, output, status_source, captured))
            value = {'version': 'progress_snapshot_v1', 'target_handle': handle,
                'observed_at': captured, 'execution_status': status,
                'provenance_refs': list(dict.fromkeys([status_source,
                    *(log['source_ref'] for log in logs)])), 'measurements': measurements,
                'log_windows': logs, 'committed_record_refs': [], 'dependencies': [],
                'result_available': status['result_available']}
            unchanged = deepcopy(value)
            unchanged.pop('observed_at')
            unchanged['execution_status'].pop('observed_at')
            signature = content_digest({'requested_fields': fields, 'snapshot': unchanged})
            old = self.store.db.execute('SELECT snapshot FROM runtime_homology_progress_snapshots '
                'WHERE run_id=? AND registry_ref=? AND target_handle=? AND scope=? AND signature=?',
                (self.run_id, self._configuration['registry_ref'], handle,
                 canonical(normalized), signature)).fetchone()
            if old is not None:
                value = json.loads(old['snapshot'])
            else:
                saved = self._source('homology.progress.snapshot', value,
                    query_ref=row['query_ref'], observed_at=captured, parents=value['provenance_refs'])
                value['progress_ref'] = saved['id']
                self.store.db.execute('INSERT INTO runtime_homology_progress_snapshots VALUES(?,?,?,?,?,?,?)',
                    (self.run_id, self._configuration['registry_ref'], handle, canonical(normalized),
                     signature, value['progress_ref'], canonical(value)))
            return self._save_operation(operation_key, operation_signature, value)

    def direct_dependencies(self, handle, scope):
        self._target(handle, scope)
        return []

    def dependency(self, spec, *, operation_key):
        if not isinstance(operation_key, str) or not operation_key:
            raise ContractError('homology_progress_operation_key_required')
        spec = validate_commission(plain(spec))
        if spec['run_id'] != self.run_id:
            raise ContractError('homology_progress_commission_outside_run')
        with self.store.transaction():
            signature, old = self._operation(operation_key, {'operation': 'dependency', 'spec': spec})
            if old is not None:
                return json.loads(old['result'])
            message = spec['child']['request']['message']
            assignment = message.get('job_assignment')
            episode_assignment = message.get('episode_assignment', {})
            if not isinstance(episode_assignment, dict):
                raise ContractError('homology_progress_assignment_invalid')
            nested = episode_assignment.get('adapter_assignment')
            if assignment is not None and nested is not None and assignment != nested:
                raise ContractError('homology_progress_assignment_conflict')
            assignment = assignment if assignment is not None else nested
            if assignment is None:
                return self._save_operation(operation_key, signature, None)
            if not isinstance(assignment, dict) or not isinstance(assignment.get('job_ref'), str):
                raise ContractError('homology_progress_assignment_invalid')
            if not self.jobs.resolve(assignment['job_ref'], 'homology_job'):
                return self._save_operation(operation_key, signature, None)
            row, scope = self._target(assignment['job_ref'], spec['child']['scope'])
            if (assignment.get('query_ref') != row['query_ref']
                    or type(assignment.get('cpu')) is not int or assignment['cpu'] != row['cpu']
                    or assignment.get('search_mode', 'native_defaults') != row['search_mode']):
                raise ContractError('homology_progress_assignment_identity_conflict')
            handoff = assignment.get('handoff')
            if handoff is not None and (not isinstance(handoff, dict)
                    or handoff.get('job_ref') != row['job_ref']
                    or handoff.get('registry_ref') != self._configuration['registry_ref']):
                raise ContractError('homology_progress_assignment_registry_conflict')
            if ('registry_ref' in assignment
                    and assignment['registry_ref'] != self._configuration['registry_ref']):
                raise ContractError('homology_progress_assignment_registry_conflict')
            captured = _now()
            body = {'version': 'native_job_dependency_v1', 'run_id': self.run_id,
                'owner_handle': spec['handle'], 'owner_episode_id': spec['child']['episode_id'],
                'commission_sha256': content_digest(spec), 'job_ref': row['job_ref'],
                'registry_ref': self._configuration['registry_ref'], 'query_ref': row['query_ref'],
                'cpu': row['cpu'], 'search_mode': row['search_mode'],
                'job_operation_key': row['operation_key']}
            relation_signature = content_digest(body)
            old = self._custody(row['job_ref'], 'dependency', relation_signature)
            if old is None:
                source = self._source('homology.progress.assignment', body,
                    query_ref=row['query_ref'], observed_at=captured)
                reference, captured = self._save_custody(row['job_ref'], 'dependency', relation_signature, source)
            else:
                reference, captured = old['source_ref'], old['observed_at']
            result = {'handle': row['job_ref'], 'kind': 'job', 'relation_ref': reference,
                      'observed_at': captured, 'state': 'pending'}
            return self._save_operation(operation_key, signature, result)


__all__ = ['HomologyProgressProvider', 'VERSION']
