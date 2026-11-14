"""Caller-bound operational credit for information actually received.

The reader qualifies immutable resource proofs and this episode's own saved
extraction publications. This projection reads only that port and the supplied
receipt selection. It neither executes work nor searches a global job history.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass, field
import hashlib
import json
import math
from typing import Protocol

from .communication import plain
from .episode_bindings import BindingContext


_ROLES = {'launch', 'launch_api', 'launch_local', 'launch_hpc', 'results'}
_KINDS = {'launch_api': 'api', 'launch_local': 'local', 'launch_hpc': 'hpc'}
_ALLOCATION = {'cpu', 'memory_bytes', 'scratch_bytes'}
_CONSTRAINTS = _ALLOCATION | {'allowed_resource_ids', 'allowed_kinds', 'resource_id', 'kind'}
_JOB_OPERANDS = {'query_ref', 'cpu', 'search_mode', 'existing_job_ref'}


class ResourceInformationReader(Protocol):
    def as_record(self) -> dict: ...
    def read_handoff_source(self, reference, *, scope) -> dict | None: ...
    def own_result_rows(self, context: BindingContext) -> list[dict]: ...


def _json(value, code):
    try:
        return json.loads(json.dumps(plain(value), allow_nan=False))
    except (ValueError, TypeError, OverflowError) as error:
        raise ValueError(code) from error


def _text(value):
    return isinstance(value, str) and bool(value)


def _object(value, code):
    if not isinstance(value, Mapping):
        raise ValueError(code)
    return _json(value, code)


def _references(value):
    if not isinstance(value, list) or any(not _text(ref) for ref in value):
        raise ValueError('resource_credit_requires_explicit_record_references')
    return value


def _selection(value):
    """Check the declared C9 operands without consulting capabilities."""
    value = _object(value, 'invalid_resource_credit_selection')
    if (set(value) != {'resource_id', 'kind', 'allocation', 'capability_binding_ref'}
            or not _text(value['resource_id']) or value['kind'] not in {'api', 'local', 'hpc'}
            or not _text(value['capability_binding_ref'])
            or not isinstance(value['allocation'], dict) or set(value['allocation']) != _ALLOCATION):
        raise ValueError('invalid_resource_credit_selection')
    for key, amount in value['allocation'].items():
        if amount is None:
            continue
        if type(amount) is not int or amount < 1:
            raise ValueError('invalid_resource_credit_allocation')
    return value


def _handoff(value):
    value = _object(value, 'invalid_resource_credit_handoff')
    try:
        selected = _selection(value['resource_selection'])
        if (value['version'] != 'execution_handoff_v1'
                or not _text(value['execution_handle']) or value['state'] != 'usable'
                or value['failure'] is not None or not value['check_record_refs']
                or not isinstance(value['submitted_input_versions'], list)):
            raise ValueError('invalid_resource_credit_handoff')
        _references(value['check_record_refs'])
        for key in ('monitoring', 'results'):
            receiver = value[key]
            if (not isinstance(receiver, dict)
                    or set(receiver) != {'provider_id', 'target_handle', 'contract_ref'}
                    or receiver['provider_id'] != selected['resource_id']
                    or receiver['target_handle'] != value['execution_handle']
                    or not _text(receiver['contract_ref'])):
                raise ValueError('invalid_resource_credit_handoff_receiver')
    except KeyError as error:
        raise ValueError('invalid_resource_credit_handoff') from error
    return value


def _launch_assignment(context):
    assignment = _object(context.assignment, 'invalid_resource_credit_assignment')
    try:
        if assignment['version'] != 'resource_launch_assignment_v1':
            raise ValueError('invalid_resource_credit_assignment')
        job = assignment['job_request']
        constraints = assignment['constraints']
        if (not isinstance(job, dict) or set(job) - _JOB_OPERANDS
                or not job or 'existing_job_ref' not in job and not {'query_ref', 'cpu'} <= job.keys()):
            raise ValueError('unsupported_resource_credit_job_request')
        for key in ('query_ref', 'search_mode', 'existing_job_ref'):
            if key in job and not _text(job[key]):
                raise ValueError('invalid_resource_credit_job_request')
        if 'cpu' in job and (type(job['cpu']) is not int or job['cpu'] < 1):
            raise ValueError('invalid_resource_credit_job_request')
        if not isinstance(constraints, dict) or set(constraints) - _CONSTRAINTS:
            raise ValueError('unsupported_resource_credit_constraints')
        for key in ('allowed_resource_ids', 'allowed_kinds'):
            if key in constraints and (not isinstance(constraints[key], list)
                    or any(not _text(item) for item in constraints[key])):
                raise ValueError('invalid_resource_credit_constraints')
        for key in ('resource_id', 'kind'):
            if key in constraints and not _text(constraints[key]):
                raise ValueError('invalid_resource_credit_constraints')
        for key in _ALLOCATION & constraints.keys():
            amount = constraints[key]
            if amount is not None and (type(amount) is not int or amount < 1):
                raise ValueError('invalid_resource_credit_constraints')
        if not isinstance(assignment['immutable_input_versions'], list):
            raise ValueError('invalid_resource_credit_assignment')
        selected = assignment['resource_selection']
        if selected is not None:
            selected = _selection(selected)
            if context.role in _KINDS and selected['kind'] != _KINDS[context.role]:
                raise ValueError('resource_credit_selection_mismatch')
        elif context.role != 'launch':
            raise ValueError('resource_credit_requires_explicit_selection')
    except KeyError as error:
        raise ValueError('invalid_resource_credit_assignment') from error
    return assignment


def _qualify_launch(context, assignment, proof):
    handoff, job = proof['execution_handoff'], proof['job']
    selected = handoff['resource_selection']
    if handoff['submitted_input_versions'] != assignment['immutable_input_versions']:
        raise ValueError('resource_credit_input_versions_mismatch')
    for key, value in assignment['job_request'].items():
        actual = job['job_ref' if key == 'existing_job_ref' else key]
        if value != actual:
            raise ValueError('resource_credit_job_request_mismatch:' + key)
    if (assignment['resource_selection'] is not None and selected != assignment['resource_selection']
            or context.role in _KINDS and selected['kind'] != _KINDS[context.role]):
        raise ValueError('resource_credit_selection_mismatch')
    constraints = assignment['constraints']
    for key in ('resource_id', 'kind'):
        if key in constraints and selected[key] != constraints[key]:
            raise ValueError('resource_credit_constraint_mismatch:' + key)
    for key, field in (('allowed_resource_ids', 'resource_id'), ('allowed_kinds', 'kind')):
        if key in constraints and selected[field] not in constraints[key]:
            raise ValueError('resource_credit_constraint_mismatch:' + key)
    for key in _ALLOCATION & constraints.keys():
        if constraints[key] != selected['allocation'][key]:
            raise ValueError('resource_credit_constraint_mismatch:' + key)
    adapter = assignment.get('adapter_assignment')
    if adapter is not None:
        if not isinstance(adapter, dict) or any(adapter.get(key) != job[key]
                for key in ('job_ref', 'query_ref', 'cpu')):
            raise ValueError('resource_credit_adapter_assignment_mismatch')
        if 'search_mode' in adapter and adapter['search_mode'] != job['search_mode']:
            raise ValueError('resource_credit_adapter_assignment_mismatch')


@dataclass(frozen=True)
class ResourceOperationalCredit:
    reader: ResourceInformationReader
    handoff_unit: float = field(kw_only=True)
    acquired_record_unit: float = field(kw_only=True)
    _reader_record: dict = field(init=False, repr=False)

    requires_episode_receipts = True

    def __post_init__(self):
        for unit in (self.handoff_unit, self.acquired_record_unit):
            try:
                valid = type(unit) in (int, float) and math.isfinite(unit) and unit > 0
            except OverflowError:
                valid = False
            if not valid:
                raise ValueError('explicit_positive_operational_credit_units_required')
        if any(not callable(getattr(self.reader, name, None)) for name in
                ('as_record', 'read_handoff_source', 'own_result_rows')):
            raise TypeError('explicit_resource_information_reader_required')
        record = _object(self.reader.as_record(), 'finite_resource_information_reader_identity_required')
        if not _text(record.get('version')) or not _text(record.get('registry_ref')):
            raise ValueError('finite_resource_information_reader_identity_required')
        object.__setattr__(self, '_reader_record', record)

    def as_record(self) -> dict:
        return {'version': 'received_resource_operational_credit_v1',
            'reader': deepcopy(self._reader_record),
            'handoff_unit': self.handoff_unit, 'acquired_record_unit': self.acquired_record_unit,
            'launch_contribution': 'distinct_received_usable_physical_handoff_identities',
            'results_contribution': 'distinct_received_canonical_records_in_own_extraction_publication_rows',
            'baseline': 'frozen_initial_record_and_physical_handoff_identities',
            'qualification': 'original_assigned_job_inputs_selection_constraints_and_requested_selector',
            'scientific_credit': False, 'monitoring_credit': False,
            'controller_effect': 'operational_information_only_without_channel_summing'}

    def _proof(self, context, reference):
        proof = self.reader.read_handoff_source(reference, scope=plain(context.scope))
        if proof is None:
            return None
        proof = _object(proof, 'invalid_resource_handoff_information')
        try:
            handoff = _handoff(proof['execution_handoff'])
            job = proof['job']
            if (proof['version'] != 'resource_handoff_information_v1'
                    or proof['run_id'] != context.run_id
                    or proof['registry_ref'] != self._reader_record['registry_ref']
                    or proof['registry_ref'] != handoff['resource_selection']['capability_binding_ref']
                    or not isinstance(job, dict) or set(job) != {'job_ref', 'query_ref', 'cpu', 'search_mode'}
                    or job['job_ref'] != handoff['execution_handle']
                    or not _text(job['query_ref']) or job['query_ref'] != proof['query_ref']
                    or type(job['cpu']) is not int or job['cpu'] < 1
                    or job['cpu'] != handoff['resource_selection']['allocation']['cpu']
                    or not _text(job['search_mode'])):
                raise ValueError('resource_credit_proof_identity_mismatch')
            # Another episode may deliver this proof. Own proofs, however,
            # must retain exactly this episode's original assignment.
            if proof['episode_id'] == context.episode_id:
                encoded = json.dumps(plain(context.assignment), sort_keys=True, separators=(',', ':'),
                    allow_nan=False)
                if proof['assignment_sha256'] != hashlib.sha256(encoded.encode()).hexdigest():
                    raise ValueError('resource_credit_assignment_identity_mismatch')
        except KeyError as error:
            raise ValueError('invalid_resource_handoff_information') from error
        return proof

    def __call__(self, context: BindingContext, receiver_selection: dict) -> dict:
        if not isinstance(context, BindingContext) or context.role not in _ROLES:
            raise ValueError('resource_credit_requires_supported_resource_role')
        selection = _object(receiver_selection, 'resource_credit_requires_receiver_selection')
        if (selection.get('run_id') != context.run_id or selection.get('episode_id') != context.episode_id
                or self._reader_record.get('run_id', context.run_id) != context.run_id):
            raise ValueError('resource_credit_receiver_identity_mismatch')
        if not {'known_record_refs', 'initial_known_record_refs'} <= selection.keys():
            raise ValueError('resource_credit_requires_explicit_record_references')
        known = _references(selection['known_record_refs'])
        initial = set(_references(selection['initial_known_record_refs']))
        if not initial <= set(known):
            raise ValueError('resource_credit_initial_references_must_be_known')
        handoff_count = acquired_count = 0
        if context.role == 'results':
            acquired_count = self._results(context, set(known), initial)
        else:
            assignment = _launch_assignment(context)
            proofs = {ref: self._proof(context, ref) for ref in dict.fromkeys(known)}
            seen = {(proof['registry_ref'], proof['execution_handoff']['execution_handle'])
                for ref in initial if (proof := proofs[ref]) is not None}
            for proof in proofs.values():
                if proof is None:
                    continue
                identity = (proof['registry_ref'], proof['execution_handoff']['execution_handle'])
                if identity in seen:
                    continue
                _qualify_launch(context, assignment, proof)
                seen.add(identity)
                handoff_count += 1
        credit = self.handoff_unit * handoff_count + self.acquired_record_unit * acquired_count
        if not math.isfinite(credit):
            raise ValueError('finite_operational_credit_required')
        return {'credit': credit, 'operational_credit': credit,
            'operational_credit_binding': self.as_record(),
            'new_handoff_count': handoff_count, 'new_acquired_record_count': acquired_count}

    def _results(self, context, known, initial):
        assignment = _object(context.assignment, 'invalid_resource_credit_assignment')
        try:
            if assignment['version'] != 'resource_results_assignment_v1':
                raise ValueError('invalid_resource_credit_assignment')
            handoff = _handoff(assignment['handoff'])
            selector = assignment['requested_data_selector']
            if (not isinstance(selector, dict) or set(selector) - {'offset', 'limit'}
                    or type(selector.get('offset', 0)) is not int or selector.get('offset', 0) < 0
                    or selector.get('limit') is not None
                    and (type(selector['limit']) is not int or selector['limit'] < 0)):
                raise ValueError('invalid_resource_credit_selector')
        except KeyError as error:
            raise ValueError('invalid_resource_credit_assignment') from error
        registry = handoff['resource_selection']['capability_binding_ref']
        if registry != self._reader_record['registry_ref']:
            raise ValueError('resource_credit_results_handoff_mismatch')
        execution = {'job_ref': handoff['execution_handle'], 'registry_ref': registry}
        adapter = assignment.get('adapter_assignment')
        if adapter is not None and (not isinstance(adapter, dict)
                or adapter.get('job_ref') != execution['job_ref']
                or adapter.get('cpu') != handoff['resource_selection']['allocation']['cpu']
                or not _text(adapter.get('query_ref'))):
            raise ValueError('resource_credit_adapter_assignment_mismatch')
        rows = self.reader.own_result_rows(context)
        if not isinstance(rows, list):
            raise ValueError('resource_credit_requires_own_publication_rows')
        seen, count = set(initial), 0
        for original in rows:
            row = _object(original, 'invalid_resource_credit_publication_row')
            try:
                if (set(row) != {'snapshot_ref', 'query_ref', 'execution_context', 'ordinal',
                        'record_ref', 'record_type', 'source_byte_spans'}
                        or not all(_text(row[key]) for key in ('snapshot_ref', 'query_ref', 'record_ref'))
                        or row['record_type'] not in {'reference', 'observation'}
                        or not isinstance(row['source_byte_spans'], list)
                        or type(row['ordinal']) is not int or row['ordinal'] < 1):
                    raise ValueError('invalid_resource_credit_publication_row')
                if row['execution_context'] != execution or adapter is not None and row['query_ref'] != adapter['query_ref']:
                    raise ValueError('resource_credit_publication_assignment_mismatch')
                start, limit = selector.get('offset', 0), selector.get('limit')
                if row['ordinal'] <= start or limit is not None and row['ordinal'] > start + limit:
                    raise ValueError('resource_credit_publication_selector_mismatch')
            except KeyError as error:
                raise ValueError('invalid_resource_credit_publication_row') from error
            reference = row['record_ref']
            if reference in known and reference not in seen:
                seen.add(reference)
                count += 1
        return count


__all__ = ['ResourceOperationalCredit']
