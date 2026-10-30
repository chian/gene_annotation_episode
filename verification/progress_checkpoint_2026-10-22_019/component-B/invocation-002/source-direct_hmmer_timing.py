"""Opted-in ordinary HMMER protocol using actual selected provider custody.

This is the existing submit/status/first-page protocol, not an episode loop.
Scientific projection remains exclusively in the ordinary ToolRegistry importer.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
from dataclasses import dataclass, replace
import hashlib
import math
from pathlib import Path
import re

from .acquisition import AcquisitionError, SourceSnapshot
from .api_execution_planning import ApiExecutionPlanner
from .api_timing_information import ApiReportedTimingFactReader
from .api_timing_records import timing_disposition
from .communication import plain
from .domain import ContractError, canonical
from .hmmer_request_preparation import prepare_hmmer_request
from .public_search_operations import ProviderOperationInProgress


KEY_VERSION = 'ordinary_hmmer_protocol_key_v1'
DIRECT_BINDING_VERSION = 'ordinary_hmmer_reported_timing_binding_v1'
DIRECT_MODE = {'version': 'ordinary_hmmer_reported_timing_v1',
    'tools': ['public.hmmer.search', 'public.hmmer.collect'],
    'collect': 'registered_only_no_registration', 'page': 'legacy_fresh_get',
    'protocol': 'existing_remote_search_protocol', 'key_version': KEY_VERSION}
_PENDING = frozenset({'PENDING', 'RECEIVED', 'STARTED', 'RETRY'})
_TERMINAL = frozenset({'SUCCESS', 'FAILURE', 'REVOKED'})
_OPERATIONS = frozenset({'submit', 'status', 'result', 'recover_submission'})
_SUFFIX = re.compile(r'(submit|status|result|recover_submission):(0|[1-9][0-9]*):(-|[1-9][0-9]*):(-|[1-9][0-9]*)\Z')


def _text(value):
    return (type(value) is str and bool(value) and value == value.strip()
        and not any(ord(character) < 32 or 127 <= ord(character) <= 159 for character in value))


def direct_operation_key(*, registry_ref: str, job_ref: str,
                         parent_operation_key: str, operation: str,
                         ordinal: int, page: int | None,
                         page_size: int | None) -> str:
    if (not all(_text(value) for value in (registry_ref, job_ref, parent_operation_key))
            or type(operation) is not str or operation not in _OPERATIONS or type(ordinal) is not int or ordinal < 0
            or (operation != 'status' and ordinal != 0)
            or (operation == 'result' and (type(page) is not int or page != 1
                or type(page_size) is not int or page_size < 1))
            or (operation != 'result' and (page is not None or page_size is not None))):
        raise ContractError('direct_hmmer_protocol_arguments_invalid')
    digest = hashlib.sha256(canonical({'version': KEY_VERSION,
        'registry_ref': registry_ref, 'job_ref': job_ref,
        'parent_operation_key': parent_operation_key}).encode('utf-8')).hexdigest()
    return f'ordinary-hmmer-v1:{digest}:{operation}:{ordinal}:{"-" if page is None else page}:{"-" if page_size is None else page_size}'


@dataclass(frozen=True)
class DirectHmmerAcquisition:
    snapshot: SourceSnapshot | None
    failure: AcquisitionError | None
    api_timing_disposition: dict
    api_timing_refs: tuple[str, ...]
    provider_operation_refs: tuple[str, ...]

    def __post_init__(self):
        if ((self.snapshot is None) == (self.failure is None)
                or self.snapshot is not None and type(self.snapshot) is not SourceSnapshot
                or self.failure is not None and not isinstance(self.failure, AcquisitionError)
                or type(self.api_timing_disposition) is not dict
                or any(type(value) is not tuple or any(type(ref) is not str for ref in value)
                    for value in (self.api_timing_refs, self.provider_operation_refs))):
            raise TypeError('typed_direct_hmmer_acquisition_required')
        object.__setattr__(self, 'api_timing_disposition', deepcopy(self.api_timing_disposition))


def _identity_conflict():
    raise ContractError('direct_hmmer_protocol_identity_conflict')


def membership_error(membership, *, job_ref):
    """Map an actual nonregistered classification without a legacy fallback."""
    code = membership['code']
    if code == 'unknown_job':
        raise ContractError('unknown_job')
    raise AcquisitionError(code, job_ref=job_ref, phase='local_preflight')


class DirectHmmerTiming:
    def __init__(self, planner: ApiExecutionPlanner, *, reader: ApiReportedTimingFactReader):
        if type(planner) is not ApiExecutionPlanner or type(reader) is not ApiReportedTimingFactReader:
            raise TypeError('typed_direct_hmmer_timing_owners_required')
        self.planner, self.reader = planner, reader
        self._validate_owners()

    def _validate_owners(self):
        planner, reader = self.planner, self.reader
        planner.validate_registry(planner.ports.result_publisher.tools)
        tools = planner.ports.result_publisher.tools
        interval = tools.remote_searches.poll_interval_seconds
        try:
            valid_interval = type(interval) in (int, float) and math.isfinite(interval) and interval >= 0
        except OverflowError:
            valid_interval = False
        if (reader.ledger is not planner.timing or reader.ports is not planner.ports
                or reader.store is not planner.store
                or tools.clients is not tools.remote_searches.clients or not valid_interval
                or reader.as_record()['ledger'] != planner.timing.as_record()):
            raise ContractError('api_direct_hmmer_timing_identity_conflict')

    def validate_registry(self, tool_registry):
        self._validate_owners()
        self.planner.validate_registry(tool_registry)

    def as_record(self):
        self._validate_owners()
        return {'version': DIRECT_BINDING_VERSION, 'configuration': deepcopy(DIRECT_MODE),
            'planner': self.planner.as_record(), 'reader': self.reader.as_record(),
            'poll_interval_seconds': self.planner.ports.operations.remote_searches.poll_interval_seconds,
            'implementation_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}

    def _key(self, job, parent, operation, *, ordinal=0, page_size=None):
        return direct_operation_key(registry_ref=self.planner.ports.registry['registry_ref'],
            job_ref=job, parent_operation_key=parent, operation=operation, ordinal=ordinal,
            page=1 if operation == 'result' else None, page_size=page_size)

    def _protocol(self, job, parent, *, tool, page_size):
        operations = self.planner.ports.operations
        inspected = operations.inspect(job)
        prefix = self._key(job, parent, 'status').rsplit(':', 4)[0] + ':'
        receipts, statuses, slots = [], {}, {}
        ended = False
        for reference in inspected['latest_operation_refs']:
            receipt = operations.read_operation(reference)
            key = receipt['operation_key']
            if not key.startswith(prefix):
                continue
            match = _SUFFIX.fullmatch(key[len(prefix):])
            if match is None:
                _identity_conflict()
            operation, ordinal, page, size = match.groups()
            ordinal = int(ordinal)
            page, size = (None if item == '-' else int(item) for item in (page, size))
            try:
                expected = direct_operation_key(registry_ref=self.planner.ports.registry['registry_ref'],
                    job_ref=job, parent_operation_key=parent, operation=operation,
                    ordinal=ordinal, page=page, page_size=size)
            except ContractError:
                _identity_conflict()
            if (key != expected or receipt['operation'] != operation
                    or receipt['job_ref'] != job
                    or receipt['registry_ref'] != self.planner.ports.registry['registry_ref']
                    or receipt['request_sha256'] != inspected['order']['request_sha256']
                    or (operation == 'result' and size != page_size)
                    or (tool.endswith('collect') and operation == 'submit')
                    or (tool.endswith('search') and operation == 'recover_submission')
                    or (operation, ordinal) in slots or (ended and operation == 'status')):
                _identity_conflict()
            slots[operation, ordinal] = receipt
            receipts.append(receipt)
            if operation == 'status':
                statuses[ordinal] = receipt
            if (receipt['failure'] is not None or receipt['outcome'] == 'failed'
                    or operation == 'result' or operation == 'status' and receipt['state'] in _TERMINAL):
                ended = True
        if sorted(statuses) != list(range(len(statuses))):
            _identity_conflict()
        terminal = False
        for ordinal in range(len(statuses)):
            receipt = statuses[ordinal]
            if terminal:
                _identity_conflict()
            terminal = receipt['failure'] is not None or receipt['outcome'] == 'failed' or receipt['state'] in _TERMINAL
        return inspected, receipts, statuses, slots

    def _failure(self, job, receipt):
        operations = self.planner.ports.operations
        snapshot = operations.read_snapshot(receipt['receipt_ref']) if receipt['snapshot_ref'] is not None else None
        failure = receipt['failure']
        if failure is not None:
            return AcquisitionError(failure['code'], retry_after=failure['retry_after_seconds'],
                job_ref=job, snapshot=snapshot, phase=failure['phase'],
                submission_outcome=failure['submission_outcome'],
                operational={'cause': deepcopy(failure), 'provider_operation_ref': receipt['receipt_ref']})
        return AcquisitionError('remote_search_failed', job_ref=job, snapshot=snapshot,
            phase='status_response', operational={'provider_operation_ref': receipt['receipt_ref'],
                'state': receipt['state']})

    def _read_result(self, job, receipt, *, request, page_size):
        from .provider_jobs import validate_remote_identity
        operations = self.planner.ports.operations
        snapshot = operations.read_snapshot(receipt['receipt_ref'])
        import json
        native = json.loads(snapshot.content)
        if (receipt['operation'] != 'result' or receipt['outcome'] != 'completed'
                or receipt['failure'] is not None or receipt['state'] != 'SUCCESS'
                or snapshot.request != {**request, 'job_id': receipt['remote_id'], 'page': 1, 'page_size': page_size}
                or snapshot.transport.get('job_ref') != job or native.get('status') != 'SUCCESS'
                or type(native.get('result')) is not dict or type(native['result'].get('hits')) is not list):
            _identity_conflict()
        try:
            validate_remote_identity(native, request, receipt['remote_id'], result=True)
        except AcquisitionError:
            _identity_conflict()
        return snapshot

    def _timing(self, job, receipt, *, scope):
        try:
            value = self.planner.timing.receive_result(self.planner.ports.operations, receipt['receipt_ref'])
        except Exception:
            value = timing_disposition('unavailable', 'timing_custody_unavailable')
        try:
            original = self.planner.ports.operations.open_scope(job)['scope']
            if not self.planner.store.scope_contains(scope, original):
                return timing_disposition('unavailable', 'timing_binding_unavailable'), ()
        except Exception:
            return timing_disposition('unavailable', 'timing_binding_unavailable'), ()
        references = ()
        if value.get('measurement_ref') is not None:
            try:
                reference = self.reader.publish(value['measurement_ref'])
                self.reader.read_source(reference, scope=scope)
                references = (reference,)
                value = {**value, 'source_ref': reference}
            except Exception:
                value = {**value, 'state': 'unavailable', 'code': 'timing_source_publication_unavailable'}
        return value, references

    def _finish(self, job, receipt, *, request, page_size, scope, references):
        snapshot = self._read_result(job, receipt, request=request, page_size=page_size)
        disposition, timing_refs = self._timing(job, receipt, scope=scope)
        snapshot = replace(snapshot, request={**snapshot.request, 'molecule_model': 'protein',
            'molecule_assignment': 'not_performed'})
        return DirectHmmerAcquisition(snapshot, None, disposition, timing_refs,
            tuple(dict.fromkeys(references)))

    def _failed(self, error, references):
        return DirectHmmerAcquisition(None, error,
            timing_disposition('unavailable', 'reported_duration_missing'), (),
            tuple(dict.fromkeys(references)))

    async def acquire(self, tool: str, arguments: dict, *, scope: dict,
                      operation_key: str) -> DirectHmmerAcquisition:
        self._validate_owners()
        if tool not in DIRECT_MODE['tools'] or type(arguments) is not dict or not _text(operation_key):
            raise ContractError('direct_hmmer_protocol_arguments_invalid')
        scope = self.planner.store.validate_scope(plain(scope))
        operations = self.planner.ports.operations
        if tool == 'public.hmmer.search':
            prepared = prepare_hmmer_request(arguments,
                sequence_symbols=self.planner.ports.sequence_symbols, scope=scope)
            order = operations.order(operation_key=operation_key, provider='hmmer',
                query_fasta=prepared.query_fasta, scope=scope, **plain(prepared.normalized_arguments))
            job = order['job_ref']
        else:
            if set(arguments) != {'job_ref'} or not _text(arguments['job_ref']):
                raise ContractError('direct_hmmer_protocol_arguments_invalid')
            job = arguments['job_ref']
        membership = operations.classify_order(job)
        if membership['state'] != 'registered' or membership['code'] is not None:
            membership_error(membership, job_ref=job)
        request = operations.inspect(job)['request']
        page_size = request['page_size']
        inspected, receipts, statuses, slots = self._protocol(job, operation_key, tool=tool, page_size=page_size)
        references = [receipt['receipt_ref'] for receipt in receipts]
        try:
            # This prefix's committed terminal failure wins over another
            # selected operation's later success or cached page.
            for receipt in receipts:
                if (receipt['failure'] is not None or receipt['outcome'] == 'failed'
                        or receipt['operation'] == 'status' and receipt['state'] in {'FAILURE', 'REVOKED'}):
                    return self._failed(self._failure(job, receipt), references)
            if ('result', 0) in slots:
                return self._finish(job, slots['result', 0], request=request,
                    page_size=page_size, scope=scope, references=references)
            if tool.endswith('search'):
                if ('submit', 0) not in slots:
                    receipt = await operations.submit_once(job,
                        operation_key=self._key(job, operation_key, 'submit'), retry_of=None)
                    references.append(receipt['receipt_ref'])
                    if receipt['failure'] is not None or receipt['outcome'] == 'failed':
                        return self._failed(self._failure(job, receipt), references)
            elif inspected['remote_id'] is None:
                receipt = operations.recover_submission(job,
                    operation_key=self._key(job, operation_key, 'recover_submission'))
                references.append(receipt['receipt_ref'])
                if receipt['failure'] is not None or receipt['outcome'] == 'failed':
                    return self._failed(self._failure(job, receipt), references)

            # Validate the actual cached selector through the public ports;
            # result_once then selects this prefix's original cached read.
            cached = False
            for reference in operations.inspect(job)['result_receipt_refs']:
                receipt = operations.read_operation(reference)
                snapshot = operations.read_snapshot(reference)
                if snapshot.request.get('page') == 1 and snapshot.request.get('page_size') == page_size:
                    self._read_result(job, receipt, request=request, page_size=page_size)
                    cached = True
                    break
            ordinal = len(statuses)
            ready = cached or bool(statuses) and statuses[ordinal - 1]['state'] == 'SUCCESS'
            while not ready:
                key = self._key(job, operation_key, 'status', ordinal=ordinal)
                observed = await operations.status_once_with_origin(job, operation_key=key)
                if (type(observed) is not dict or set(observed) != {'version', 'origin', 'receipt'}
                        or observed['version'] != 'public_search_status_read_v1'
                        or observed['origin'] not in {'worker_dispatched', 'capture_reused', 'receipt_reused', 'no_capture'}):
                    _identity_conflict()
                receipt = observed['receipt']
                if (receipt['operation_key'] != key or receipt['operation'] != 'status'
                        or receipt['job_ref'] != job or receipt != operations.read_operation(receipt['receipt_ref'])):
                    _identity_conflict()
                references.append(receipt['receipt_ref'])
                if receipt['failure'] is not None or receipt['outcome'] == 'failed' or receipt['state'] in {'FAILURE', 'REVOKED'}:
                    return self._failed(self._failure(job, receipt), references)
                if receipt['outcome'] != 'completed' or receipt['state'] not in _PENDING | {'SUCCESS'}:
                    _identity_conflict()
                ready = receipt['state'] == 'SUCCESS'
                if not ready:
                    if observed['origin'] == 'no_capture':
                        _identity_conflict()
                    if observed['origin'] == 'worker_dispatched':
                        await asyncio.sleep(operations.remote_searches.poll_interval_seconds)
                    ordinal += 1
            receipt = await operations.result_once(job,
                operation_key=self._key(job, operation_key, 'result', page_size=page_size),
                page=1, page_size=page_size)
            references.append(receipt['receipt_ref'])
            if receipt['failure'] is not None or receipt['outcome'] == 'failed':
                return self._failed(self._failure(job, receipt), references)
            return self._finish(job, receipt, request=request, page_size=page_size,
                scope=scope, references=references)
        except ProviderOperationInProgress as error:
            return self._failed(AcquisitionError('submission_in_progress', job_ref=error.job_ref,
                phase='provider_operation', operational={'operation_key': error.operation_key}), references)


__all__ = ['DirectHmmerTiming', 'DirectHmmerAcquisition', 'DIRECT_MODE',
    'DIRECT_BINDING_VERSION', 'KEY_VERSION', 'direct_operation_key']
