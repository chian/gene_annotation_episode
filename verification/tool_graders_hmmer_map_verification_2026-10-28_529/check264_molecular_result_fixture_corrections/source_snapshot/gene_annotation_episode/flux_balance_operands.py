"""Selected received FBA inputs and detached frozen witness records.

These helpers validate metadata and existing receipt authority, not source
interpretation or scientific bytes. A frozen receipt must itself arrive through
the host's authenticated immutable control artifact; self-consistent JSON alone
does not authenticate a historical Store record. No helper writes or grants it.
"""
from __future__ import annotations

import json
import re

from method_loop.identities import EpisodeRef

from .communication import plain
from .domain import ContractError
from .episode_bindings import BindingContext
from .episode_receipts import EpisodeReceipts
from .episode_return_records import EpisodeReturnRecords
from .execution_contracts import canonical, digest
from .flux_balance_contracts import validate_flux_balance_record
from .native_file_capture import NativeFileCaptureError, _metadata
from .native_flux_balance_contracts import validate_flux_balance_requested_job


_SOURCE_FIELDS = ('artifact_ref', 'text_ref', 'request_ref', 'stdout_ref', 'stderr_ref')
_BASELINE_ROLES = {'launch', 'launch_local', 'launch_api', 'launch_hpc', 'results'}
_SHA = re.compile(r'[0-9a-f]{64}')
_BINDING_KEYS = {'version', 'run_id', 'episode_id', 'request_sha256', 'assignment_sha256',
                 'scope', 'inheritance_manifest', 'input_versions', 'model', 'prior_sources'}


def _require(condition, code, pointer=''):
    if not condition:
        raise ValueError('flux_balance_input_' + code + (':' + pointer if pointer else ''))


def _detached(value, code='invalid_binding'):
    try:
        return json.loads(canonical(value))
    except (TypeError, ValueError, OverflowError, RecursionError) as error:
        raise ValueError('flux_balance_input_' + code) from error


def _versions(value):
    _require(type(value) is list, 'invalid_versions')
    seen = {}
    for index, row in enumerate(value):
        pointer = '/input_versions/' + str(index)
        _require(type(row) is dict and set(row) == {'reference', 'version', 'content_sha256'},
                 'invalid_versions', pointer)
        _require(type(row['reference']) is str and row['reference']
                 and (row['version'] is None or type(row['version']) is str and bool(row['version']))
                 and (row['content_sha256'] is None or type(row['content_sha256']) is str
                      and _SHA.fullmatch(row['content_sha256']) is not None), 'invalid_versions', pointer)
        previous = seen.setdefault(row['reference'], row)
        _require(previous == row, 'version_conflict', pointer)
    return _detached(value, 'invalid_versions')


def _authority_records(store, context):
    _require(isinstance(context, BindingContext), 'invalid_context')
    authority = EpisodeReturnRecords(store, context.run_id, failure_prefix='flux_balance_input_')
    authority.authenticate(context, allow_unsaved=True)
    saved = store.db.execute('SELECT 1 FROM runtime_episodes WHERE run_id=? AND episode_id=?',
                            (context.run_id, context.episode_id)).fetchone()
    if saved is None:
        for table in ('runtime_actions', 'runtime_forms', 'runtime_model_calls', 'runtime_observations'):
            _require(store.db.execute(f'SELECT 1 FROM {table} WHERE run_id=? AND episode_id=? LIMIT 1',
                                     (context.run_id, context.episode_id)).fetchone() is None, 'invalid_context')
    # Read existing primitives only: construction must not create receipt tables
    # or publish a transaction owned by the selected action.
    receipts = EpisodeReceipts.__new__(EpisodeReceipts)
    receipts.store, receipts.db, receipts.run_id = store, store.db, context.run_id
    current, seen = context, set()
    while True:
        _require(current.episode_id not in seen, 'invalid_context')
        seen.add(current.episode_id)
        manifest = receipts.manifest(current.episode_id)
        parent_id = EpisodeRef(context.run_id, current.path[:-1]).episode_id if len(current.path) > 1 else None
        _require(manifest.get('parent_episode_id') == parent_id
                 and 'received_report_prefix' in manifest
                 and authority._equal(current.request.get('message', {}).get('knowledge_inheritance'), manifest),
                 'invalid_context')
        through = manifest['through_receipt_index']
        _require(through is None if parent_id is None else type(through) is int and through >= 0,
                 'invalid_context')
        if parent_id is None:
            break
        parent = authority.context(parent_id)
        _require(parent.path == current.path[:-1], 'invalid_context')
        store.validate_scope(plain(current.scope), parent_scope=plain(parent.scope))
        current = parent
    scope = store.validate_scope(plain(context.scope))
    known = set(receipts.known(context.episode_id, baseline=context.role in _BASELINE_ROLES))
    return scope, receipts.manifest(context.episode_id), known


def _authority(store, context):
    try:
        return _authority_records(store, context)
    except (ValueError, ContractError) as error:
        if str(error).startswith('flux_balance_input_'):
            raise
        raise ValueError('flux_balance_input_invalid_context') from error


def _access(context, reference, namespace, reference_access, pointer):
    _require(callable(reference_access), 'invalid_reference_access', pointer)
    verdict = reference_access(context, reference, namespace)
    _require(verdict is None or type(verdict) is bool, 'invalid_reference_access', pointer)
    _require(verdict is not False, 'protected_reference_denied', pointer)


def _file(store, value, pointer):
    try:
        file = validate_flux_balance_record('File', value)
        metadata = _metadata(store, file['artifact_ref'])
    except (ValueError, NativeFileCaptureError) as error:
        raise ValueError('flux_balance_input_artifact_metadata_mismatch:' + pointer) from error
    _require(file['artifact_ref'] == 'artifact_' + file['sha256']
             and metadata['sha256'] == file['sha256'] and metadata['size'] == file['size_bytes'],
             'artifact_metadata_mismatch', pointer)
    return file, str(store.path / 'artifacts' / file['sha256'][:2] / file['sha256'])


def _selected_files(store, assignment):
    _require(type(assignment) is dict and 'requested_job' in assignment, 'invalid_assignment')
    try:
        requested = validate_flux_balance_requested_job(assignment['requested_job'])
    except (ValueError, KeyError, TypeError) as error:
        raise ValueError('flux_balance_input_invalid_assignment') from error
    job = requested['native_flux_balance']
    selected = job['model_input']
    pointer = '/native_flux_balance/model_input'
    model, path = _file(store, {**{k: selected['file'][k] for k in ('sha256', 'size_bytes')},
                              'artifact_ref': selected['artifact_ref'], 'format': selected['format']}, pointer)
    _require(selected['file']['path'] == path, 'selected_path_mismatch', pointer)
    model_row = {'file': model, 'path': path, 'uses': [{'request_pointer': pointer, 'source_pointer': None}]}
    priors = []

    def add(file, request_pointer, source_pointer):
        validated, actual_path = _file(store, file, request_pointer)
        for previous in [model_row, *priors]:
            if previous['file']['artifact_ref'] == validated['artifact_ref']:
                # One byte identity cannot silently acquire a conflicting format
                # or size through another selected use.
                _require(previous['file'] == validated, 'artifact_identity_conflict', request_pointer)
        row = next((r for r in priors if r['file'] == validated), None)
        if row is None:
            row = {'file': validated, 'path': actual_path, 'uses': []}
            priors.append(row)
        row['uses'].append({'request_pointer': request_pointer, 'source_pointer': source_pointer})

    if selected['acquisition_receipt_file'] is not None:
        add(selected['acquisition_receipt_file'], pointer + '/acquisition_receipt_file', None)
    for index, change in enumerate(job['constraints'] or []):
        for side in ('lower', 'upper'):
            source = change[side]['source']
            # Native role addresses still belong exclusively to the parser.
            if type(source) is dict and 'file' in source:
                add(source['file'], f'/native_flux_balance/constraints/{index}/{side}/source/file', source['pointer'])
    return model_row, priors


def _check_version(store, record, version, pointer):
    _require(record.get('id') == version['reference'], 'record_identity_conflict', pointer)
    _require(version['version'] is None or str(record.get('revision')) == version['version'],
             'version_conflict', pointer)
    if version['content_sha256'] is not None:
        reference = (record['id'] if record['record_type'] == 'artifact'
                     else record.get('sequence_ref', record.get('artifact_ref')))
        try:
            actual = _metadata(store, reference)
        except NativeFileCaptureError as error:
            raise ValueError('flux_balance_input_version_conflict:' + pointer) from error
        _require(actual['sha256'] == version['content_sha256'], 'version_conflict', pointer)


def _compose(store, context, assignment, versions, reference_access, *, records=None):
    versions = _versions(versions)
    scope, manifest, known = _authority(store, context)
    model, priors = _selected_files(store, assignment)
    selected_records = []
    for index, version in enumerate(versions):
        reference = version['reference']
        # A frozen receipt contains witnesses only. Unrelated selected records
        # are not rediscovered from today's Store during historical validation.
        if records is not None and reference not in records:
            continue
        pointer = '/input_versions/' + str(index)
        _require(reference in known, 'not_received', pointer)
        try:
            record = store.get(reference) if records is None else records[reference]
        except ContractError as error:
            raise ValueError('flux_balance_input_record_unavailable:' + pointer) from error
        _require(type(record) is dict and type(record.get('record_type')) is str,
                 'unsupported_witness', pointer)
        _access(context, reference, record['record_type'], reference_access, pointer)
        if records is not None and record['record_type'] == 'source':
            # Use the existing ownership index and the frozen source record,
            # never a later mutable source row for historical scope projection.
            roots = {r[0] for r in store.db.execute(
                'SELECT target_ref FROM record_roots WHERE record_ref=?', (reference,))}
            in_scope = (roots <= set(scope['subject_refs'])
                and bool(store._scope_filter_record(canonical(record), canonical(scope))))
            _require(in_scope, 'outside_assigned_scope', pointer)
        elif record['record_type'] != 'artifact':
            _require(bool(store.reference_subset([reference], scope)), 'outside_assigned_scope', pointer)
        _check_version(store, record, version, pointer)
        if record['record_type'] in {'source', 'artifact'}:
            selected_records.append((version, record))
    for row in [model, *priors]:
        pointer = row['uses'][0]['request_pointer']
        reference = row['file']['artifact_ref']
        _access(context, reference, 'artifact', reference_access, pointer)
        witnesses = []
        for version, record in selected_records:
            fields = ([None] if record['record_type'] == 'artifact' and record['id'] == reference else
                      [field for field in _SOURCE_FIELDS if record.get(field) == reference]
                      if record['record_type'] == 'source' else [])
            for field in fields:
                witness = {'reference': version['reference'], 'record_sha256': digest(record),
                           'artifact_field': field, 'input_version': version}
                if witness not in witnesses:
                    witnesses.append(witness)
        _require(bool(witnesses), 'selected_witness_required', pointer)
        row['witnesses'] = witnesses
    return _detached({'version': 'flux_balance_input_binding_v1', 'run_id': context.run_id,
        'episode_id': context.episode_id, 'request_sha256': digest(context.request),
        'assignment_sha256': digest(assignment), 'scope': scope, 'inheritance_manifest': manifest,
        'input_versions': versions, 'model': model, 'prior_sources': priors})


def bind_flux_balance_job_inputs(store, context, assignment, *, input_versions, reference_access):
    """Admit only explicitly selected, actually received File witnesses."""
    return _compose(store, context, plain(assignment), input_versions, reference_access)


def validate_flux_balance_input_binding(store, value, *, context, assignment, input_versions, reference_access):
    """Validate an unfrozen binding against the current original selection."""
    value = _detached(value)
    expected = bind_flux_balance_job_inputs(store, context, assignment,
        input_versions=input_versions, reference_access=reference_access)
    _require(EpisodeReturnRecords._equal(value, expected), 'binding_conflict')
    return value


def _binding(value):
    value = _detached(value)
    _require(type(value) is dict and set(value) == _BINDING_KEYS
             and value['version'] == 'flux_balance_input_binding_v1', 'invalid_binding')
    _require(all(type(value[k]) is str and value[k] for k in ('run_id', 'episode_id'))
             and all(type(value[k]) is str and _SHA.fullmatch(value[k]) is not None
                     for k in ('request_sha256', 'assignment_sha256'))
             and type(value['scope']) is dict and type(value['inheritance_manifest']) is dict, 'invalid_binding')
    _versions(value['input_versions'])
    _require(type(value['prior_sources']) is list, 'invalid_binding')
    for row in [value['model'], *value['prior_sources']]:
        _require(type(row) is dict and set(row) == {'file', 'path', 'uses', 'witnesses'}
                 and type(row['uses']) is list and row['uses'] and type(row['witnesses']) is list
                 and row['witnesses'], 'invalid_binding')
        for use in row['uses']:
            _require(type(use) is dict and set(use) == {'request_pointer', 'source_pointer'}
                     and type(use['request_pointer']) is str
                     and (use['source_pointer'] is None or type(use['source_pointer']) is str), 'invalid_binding')
        for witness in row['witnesses']:
            _require(type(witness) is dict and set(witness) == {'reference', 'record_sha256', 'artifact_field', 'input_version'}
                     and type(witness['reference']) is str and type(witness['record_sha256']) is str
                     and _SHA.fullmatch(witness['record_sha256']) is not None
                     and witness['artifact_field'] in (None, *_SOURCE_FIELDS), 'invalid_binding')
            _versions([witness['input_version']])
            _require(witness['input_version']['reference'] == witness['reference']
                     and witness['input_version'] in value['input_versions'], 'witness_selection_conflict')
    return value


def freeze_flux_balance_input_binding(store, *, binding):
    """Copy exact current witnesses; the action owner persists this control."""
    binding = _binding(binding)
    records = []
    seen = {}
    for row in [binding['model'], *binding['prior_sources']]:
        _, path = _file(store, row['file'], row['uses'][0]['request_pointer'])
        _require(row['path'] == path, 'selected_path_mismatch')
        for witness in row['witnesses']:
            reference = witness['reference']
            try:
                record = store.get(reference)
            except ContractError as error:
                raise ValueError('flux_balance_input_record_unavailable') from error
            _require(record.get('id') == reference and digest(record) == witness['record_sha256'],
                     'witness_record_conflict')
            _require(witness['input_version'] in binding['input_versions'], 'witness_selection_conflict')
            _require(witness['input_version']['reference'] == reference, 'witness_selection_conflict')
            _check_version(store, record, witness['input_version'], row['uses'][0]['request_pointer'])
            field = witness['artifact_field']
            _require((field is None and record['record_type'] == 'artifact' and reference == row['file']['artifact_ref'])
                     or (field in _SOURCE_FIELDS and record['record_type'] == 'source'
                         and record.get(field) == row['file']['artifact_ref']), 'witness_record_conflict')
            if reference not in seen:
                seen[reference] = record
                records.append({'reference': reference, 'record': record})
    return _detached({'version': 'flux_balance_input_binding_receipt_v1', 'binding': binding,
                      'witness_records': records})


def validate_flux_balance_input_binding_receipt(store, value, *, context, assignment,
                                               input_versions, reference_access):
    """Check a host-authenticated frozen control without rebinding its sources."""
    value = _detached(value, 'invalid_receipt')
    _require(type(value) is dict and set(value) == {'version', 'binding', 'witness_records'}
             and value['version'] == 'flux_balance_input_binding_receipt_v1'
             and type(value['witness_records']) is list, 'invalid_receipt')
    binding = _binding(value['binding'])
    records = {}
    order = []
    for index, item in enumerate(value['witness_records']):
        _require(type(item) is dict and set(item) == {'reference', 'record'}
                 and type(item['reference']) is str and type(item['record']) is dict
                 and item['record'].get('id') == item['reference']
                 and item['reference'] not in records, 'invalid_receipt', '/witness_records/' + str(index))
        records[item['reference']] = item['record']
        order.append(item['reference'])
    expected_order = list(dict.fromkeys(w['reference'] for row in [binding['model'], *binding['prior_sources']]
                                        for w in row['witnesses']))
    _require(order == expected_order, 'witness_record_conflict')
    for row in [binding['model'], *binding['prior_sources']]:
        for witness in row['witnesses']:
            _require(digest(records[witness['reference']]) == witness['record_sha256'], 'witness_record_conflict')
    expected = _compose(store, context, plain(assignment), input_versions, reference_access, records=records)
    _require(EpisodeReturnRecords._equal(binding, expected), 'binding_conflict')
    return value


__all__ = ['bind_flux_balance_job_inputs', 'validate_flux_balance_input_binding',
           'freeze_flux_balance_input_binding', 'validate_flux_balance_input_binding_receipt']
