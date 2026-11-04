"""One selected HMMER status observation and immutable semantic delivery.

Provider operation receipts own HTTP custody. This provider retains the exact
receipt supporting a delivered snapshot, while equal information reuses its
original delivery. It does not submit work, acquire results, infer durations or
assign monitoring credit.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import TYPE_CHECKING

from method_loop.durable import content_digest, validate_commission

from .communication import plain
from .domain import ContractError, canonical, obj, parse_sequences, validate_schema
from .progress_records import external_job_status
from .provider_jobs import build_search_request, provider_job_reference
from .resource_records import SELECTION_SCHEMA

if TYPE_CHECKING:
    from .public_search_operations import PublicSearchPorts


VERSION = 'hmmer_progress_provider_v1'
_FIELDS = ('execution_status', 'measurements', 'log_windows',
           'committed_record_refs', 'dependencies', 'result_available')
_TEXT = {'type': 'string', 'minLength': 1}
_REGISTRY_SCHEMA = obj({'version': {'const': 'public_search_registry_v1'},
    'registry_ref': _TEXT, 'resource_id': _TEXT, 'provider': {'const': 'hmmer'},
    'client_binding_sha256': {'type': 'string', 'pattern': '^[a-f0-9]{64}$'}})


class HmmerProgressProvider:
    def __init__(self, store, *, run_id, ports: PublicSearchPorts):
        if not isinstance(run_id, str) or not run_id:
            raise ValueError('hmmer_progress_run_identity_required')
        registry = json.loads(canonical(plain(ports.registry)))
        validate_schema(registry, _REGISTRY_SCHEMA)
        if any(not callable(getattr(ports.operations, name, None)) for name in
               ('inspect', 'open_scope', 'read_operation', 'read_snapshot', 'status_once')):
            raise TypeError('public_search_operations_required')
        if not callable(getattr(ports, 'sequence_symbols', None)):
            raise TypeError('public_search_sequence_reader_required')
        self.store, self.run_id, self.ports = store, run_id, ports
        self._registry = registry
        with store.transaction():
            store.db.execute('''CREATE TABLE IF NOT EXISTS runtime_hmmer_progress_snapshots (
                run_id TEXT NOT NULL, registry_ref TEXT NOT NULL, target_handle TEXT NOT NULL,
                scope TEXT NOT NULL, signature TEXT NOT NULL,
                progress_ref TEXT NOT NULL REFERENCES records(id), snapshot TEXT NOT NULL,
                PRIMARY KEY(run_id,registry_ref,target_handle,scope,signature))''')
            store.db.execute('''CREATE TABLE IF NOT EXISTS runtime_hmmer_progress_operations (
                run_id TEXT NOT NULL, operation_key TEXT NOT NULL, signature TEXT NOT NULL,
                status_receipt_ref TEXT NOT NULL, result TEXT NOT NULL,
                PRIMARY KEY(run_id,operation_key))''')
            store.db.execute('''CREATE TABLE IF NOT EXISTS runtime_hmmer_progress_dependencies (
                run_id TEXT NOT NULL, registry_ref TEXT NOT NULL, signature TEXT NOT NULL,
                source_ref TEXT NOT NULL REFERENCES records(id), observed_at TEXT NOT NULL,
                PRIMARY KEY(run_id,registry_ref,signature))''')
            store.db.execute('''CREATE TABLE IF NOT EXISTS runtime_hmmer_progress_dependency_operations (
                run_id TEXT NOT NULL, operation_key TEXT NOT NULL, signature TEXT NOT NULL,
                result TEXT NOT NULL, PRIMARY KEY(run_id,operation_key))''')

    def as_record(self):
        return {'version': VERSION, 'registry': deepcopy(self._registry),
            'implementation_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}

    def _registered(self, handle):
        if not isinstance(handle, str) or not handle:
            raise ContractError('hmmer_progress_target_handle_required')
        if canonical(plain(self.ports.registry)) != canonical(self._registry):
            raise ContractError('hmmer_progress_registry_configuration_changed')
        saved = self.ports.operations.inspect(handle)
        order, request = saved['order'], saved['request']
        if (order['version'] != 'public_search_order_v1'
                or order['registry_ref'] != self._registry['registry_ref']
                or order['job_ref'] != handle
                or request.get('provider', 'hmmer') != 'hmmer'
                or order['request_sha256'] != content_digest(request)
                or self.store.get_artifact(order['request_ref']) != canonical(request).encode()):
            raise ContractError('hmmer_progress_order_identity_conflict')
        fasta = self.store.get_artifact(order['query_fasta_ref']).decode('utf-8')
        rebuilt, sequences = build_search_request(subject_ref=request['subject_ref'],
            query_fasta=fasta, algorithm=request['algorithm'], database=request['database'],
            parameters=request['parameters'], page_size=request['page_size'], provider='hmmer')
        if (canonical(rebuilt) != canonical(request)
                or provider_job_reference(order['order_operation_key'], request) != handle):
            raise ContractError('hmmer_progress_request_identity_conflict')
        scope_record = self.ports.operations.open_scope(handle)
        if (set(scope_record) != {'version', 'registry_ref', 'job_ref', 'scope', 'scope_sha256'}
                or scope_record['version'] != 'public_search_order_scope_v1'
                or scope_record['registry_ref'] != self._registry['registry_ref']
                or scope_record['job_ref'] != handle
                or scope_record['scope_sha256'] != content_digest(scope_record['scope'])):
            raise ContractError('hmmer_progress_order_scope_identity_conflict')
        target_scope = self.store.validate_scope(plain(scope_record['scope']))
        if canonical(target_scope) != canonical(scope_record['scope']):
            raise ContractError('hmmer_progress_order_scope_identity_conflict')
        symbols = parse_sequences(self.ports.sequence_symbols(request['subject_ref'], scope=target_scope),
                                  format='raw', molecule='protein')
        if len(symbols) != 1 or symbols[0].sequence != sequences[0].sequence:
            raise ContractError('hmmer_progress_query_identity_conflict')
        return saved, target_scope

    def scope(self, handle):
        return self._registered(handle)[1]

    def _target(self, handle, scope, *, exact_scope=False):
        saved, target_scope = self._registered(handle)
        normalized = self.store.validate_scope(plain(scope))
        if not self.store.scope_contains(normalized, target_scope):
            raise ContractError('hmmer_progress_target_outside_scope')
        if exact_scope and canonical(normalized) != canonical(target_scope):
            raise ContractError('hmmer_progress_assignment_scope_conflict')
        return saved, normalized

    def direct_dependencies(self, handle, scope):
        self._target(handle, scope)
        return []

    def dependency(self, spec, *, operation_key):
        """Expose only the original assigned relationship, without status HTTP."""
        if not isinstance(operation_key, str) or not operation_key:
            raise ContractError('hmmer_progress_operation_key_required')
        spec = validate_commission(plain(spec))
        if spec['run_id'] != self.run_id:
            raise ContractError('hmmer_progress_commission_outside_run')
        signature = content_digest({'provider': self.as_record(), 'commission': spec})
        with self.store.transaction():
            old = self.store.db.execute('SELECT signature,result FROM '
                'runtime_hmmer_progress_dependency_operations WHERE run_id=? AND operation_key=?',
                (self.run_id, operation_key)).fetchone()
            if old is not None:
                if old['signature'] != signature:
                    raise ContractError('hmmer_progress_operation_identity_conflict')
                return json.loads(old['result'])
            assignment = spec['child']['request']['message'].get('episode_assignment', {})
            if not isinstance(assignment, dict):
                raise ContractError('hmmer_progress_assignment_invalid')
            selected = assignment.get('resource_selection')
            if selected is None:
                handoff = assignment.get('handoff', {})
                if not isinstance(handoff, dict):
                    raise ContractError('hmmer_progress_assignment_invalid')
                selected = handoff.get('resource_selection')
            result = None
            if isinstance(selected, dict) and selected.get('resource_id') == self._registry['resource_id']:
                validate_schema(selected, SELECTION_SCHEMA)
                if (selected.get('kind') != 'api'
                        or selected.get('capability_binding_ref') != self._registry['registry_ref']
                        or canonical(spec['resource_selection']) != canonical(selected)):
                    raise ContractError('hmmer_progress_assignment_registry_conflict')
                order = assignment.get('adapter_assignment')
                if not isinstance(order, dict) or not isinstance(order.get('job_ref'), str):
                    raise ContractError('hmmer_progress_assignment_invalid')
                actual = self.ports.operations.open_order(order['job_ref'])
                if canonical(actual) != canonical(order):
                    raise ContractError('hmmer_progress_assignment_identity_conflict')
                saved, _ = self._target(order['job_ref'], spec['child']['scope'], exact_scope=True)
                body = {'version': 'api_job_dependency_v1', 'run_id': self.run_id,
                    'owner_handle': spec['handle'], 'owner_episode_id': spec['child']['episode_id'],
                    'commission_sha256': content_digest(spec), 'registry_ref': self._registry['registry_ref'],
                    'job_ref': order['job_ref'], 'request_sha256': order['request_sha256'],
                    'order_operation_key': order['order_operation_key']}
                relation_signature = content_digest(body)
                old = self.store.db.execute('SELECT source_ref,observed_at FROM '
                    'runtime_hmmer_progress_dependencies WHERE run_id=? AND registry_ref=? AND signature=?',
                    (self.run_id, self._registry['registry_ref'], relation_signature)).fetchone()
                if old is None:
                    captured = datetime.now(timezone.utc).isoformat()
                    source = self._source('hmmer.progress.assignment', body,
                        subject_ref=saved['request']['subject_ref'], observed_at=captured)
                    reference = source['id']
                    self.store.db.execute('INSERT INTO runtime_hmmer_progress_dependencies VALUES(?,?,?,?,?)',
                        (self.run_id, self._registry['registry_ref'], relation_signature, reference, captured))
                else:
                    reference, captured = old['source_ref'], old['observed_at']
                result = {'handle': order['job_ref'], 'kind': 'job', 'relation_ref': reference,
                          'observed_at': captured, 'state': 'pending'}
            self.store.db.execute('INSERT INTO runtime_hmmer_progress_dependency_operations VALUES(?,?,?,?)',
                (self.run_id, operation_key, signature, canonical(result)))
        return result

    def _operation(self, operation_key, signature):
        row = self.store.db.execute('SELECT signature,result FROM runtime_hmmer_progress_operations '
            'WHERE run_id=? AND operation_key=?', (self.run_id, operation_key)).fetchone()
        if row is None:
            return None
        if row['signature'] != signature:
            raise ContractError('hmmer_progress_operation_identity_conflict')
        return json.loads(row['result'])

    def _capture_identities(self, handle, receipt, request_sha256):
        """Read only captures that this original receipt actually knew about."""
        wanted = set(receipt['result_snapshot_refs'])
        if not wanted:
            return []
        captures, found = set(), set()
        for reference in self.ports.operations.inspect(handle)['result_receipt_refs']:
            result = self.ports.operations.read_operation(reference)
            if result['snapshot_ref'] not in wanted:
                continue
            if (result['operation'] != 'result' or result['outcome'] != 'completed'
                    or result['failure'] is not None or result['job_ref'] != handle
                    or result['registry_ref'] != self._registry['registry_ref']
                    or result['provider'] != 'hmmer' or result['request_sha256'] != request_sha256):
                raise ContractError('hmmer_progress_result_capture_identity_conflict')
            snapshot = self.ports.operations.read_snapshot(reference)
            page, size = snapshot.request.get('page'), snapshot.request.get('page_size')
            if type(page) is not int or page < 1 or type(size) is not int or size < 1:
                raise ContractError('hmmer_progress_result_capture_selector_invalid')
            captures.add((handle, request_sha256, page, size, snapshot.sha256))
            found.add(result['snapshot_ref'])
        if found != wanted:
            raise ContractError('hmmer_progress_result_capture_unavailable')
        return [list(row) for row in sorted(captures)]

    def _source(self, provider, body, *, subject_ref, observed_at,
                content=None, media_type='application/json', uri=None, parents=()):
        metadata = self.store.artifact(canonical(body), 'application/json')
        artifact = metadata if content is None else self.store.artifact(content, media_type)
        return self.store.put('source', {'provider': provider, 'accession': None, 'uri': uri,
            'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': metadata,
            'version': VERSION, 'retrieved_at': observed_at, 'operand_refs': [subject_ref],
            'parent_source_refs': list(parents)}, origin='tool')

    async def observe(self, handle, requested_fields, scope, *, operation_key=None):
        fields = plain(requested_fields)
        if (not isinstance(fields, list) or any(field not in _FIELDS for field in fields)
                or len(fields) != len(set(fields))):
            raise ContractError('hmmer_progress_requested_fields_invalid')
        if not isinstance(operation_key, str) or not operation_key:
            raise ContractError('hmmer_progress_operation_key_required')
        normalized = self.store.validate_scope(plain(scope))
        selection = {'provider': self.as_record(), 'handle': handle,
            'requested_fields': fields, 'scope': normalized}
        operation_signature = content_digest(selection)
        replay = self._operation(operation_key, operation_signature)
        if replay is not None:
            return replay
        if self.store.db.in_transaction:
            raise ContractError('progress_observation_requires_committed_transaction')
        saved, normalized = self._target(handle, normalized)
        # The provider commits custody independently. No Store transaction or
        # read snapshot remains open across the awaited one-request operation.
        receipt = await self.ports.operations.status_once(handle, operation_key=operation_key)
        if receipt['outcome'] != 'completed':
            raise ContractError('external_progress_observation_failed', detail={
                'receipt_ref': receipt['receipt_ref'], 'failure': plain(receipt['failure'])})
        order, request = saved['order'], saved['request']
        if (receipt['registry_ref'] != self._registry['registry_ref']
                or receipt['request_sha256'] != order['request_sha256']
                or receipt['operation_key'] != operation_key):
            raise ContractError('hmmer_progress_status_identity_conflict')
        status = external_job_status(handle, receipt)
        capture_identities = self._capture_identities(handle, receipt, order['request_sha256'])
        # A receipt/source representation and its time prove custody; they are
        # not themselves new semantic information about this execution.
        semantics = {key: value for key, value in status.items() if key not in {
            'observed_at', 'status_receipt_ref', 'status_snapshot_ref', 'result_snapshot_refs'}}
        semantics['result_captures'] = capture_identities
        signature = content_digest({'requested_fields': sorted(fields), 'status': semantics})
        with self.store.transaction():
            replay = self._operation(operation_key, operation_signature)
            if replay is not None:
                return replay
            previous = self.store.db.execute('SELECT snapshot FROM runtime_hmmer_progress_snapshots '
                'WHERE run_id=? AND registry_ref=? AND target_handle=? AND scope=? AND signature=?',
                (self.run_id, self._registry['registry_ref'], handle, canonical(normalized), signature)).fetchone()
            if previous is not None:
                value = json.loads(previous['snapshot'])
            else:
                raw = self.ports.operations.read_snapshot(receipt['receipt_ref'])
                body = {'version': 'hmmer_progress_status_information_v1', 'run_id': self.run_id,
                    'registry': self._registry, 'order': order, 'request': request,
                    'receipt': receipt, 'snapshot': {'service': raw.service, 'url': raw.url,
                        'request': raw.request, 'retrieved_at': raw.retrieved_at,
                        'media_type': raw.media_type, 'transport': raw.transport,
                        'content_sha256': raw.sha256}, 'result_captures': capture_identities}
                source = self._source('hmmer.progress.status', body,
                    subject_ref=request['subject_ref'], observed_at=receipt['observed_at'],
                    content=raw.content, media_type=raw.media_type, uri=raw.url)
                value = {'version': 'progress_snapshot_v1', 'target_handle': handle,
                    'observed_at': receipt['observed_at'], 'execution_status': status,
                    'provenance_refs': [source['id']], 'measurements': [], 'log_windows': [],
                    'committed_record_refs': [], 'dependencies': [],
                    'result_available': status['result_available']}
                snapshot_source = self._source('hmmer.progress.snapshot', value,
                    subject_ref=request['subject_ref'], observed_at=receipt['observed_at'],
                    parents=value['provenance_refs'])
                value['progress_ref'] = snapshot_source['id']
                self.store.db.execute('INSERT INTO runtime_hmmer_progress_snapshots VALUES(?,?,?,?,?,?,?)',
                    (self.run_id, self._registry['registry_ref'], handle, canonical(normalized),
                     signature, value['progress_ref'], canonical(value)))
            self.store.db.execute('INSERT INTO runtime_hmmer_progress_operations VALUES(?,?,?,?,?)',
                (self.run_id, operation_key, operation_signature, receipt['receipt_ref'], canonical(value)))
        return value


__all__ = ['HmmerProgressProvider', 'VERSION']
