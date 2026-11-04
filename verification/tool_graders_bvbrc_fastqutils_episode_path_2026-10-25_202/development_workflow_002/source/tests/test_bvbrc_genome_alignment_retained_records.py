"""Synthetic custody only; real current receipt schemas and canonical bytes.

No fixture is an authenticated host record or evidence of a BV-BRC execution.
The tests exercise the public pure checks against exact retained byte inputs.
"""
from copy import deepcopy
import hashlib
import json

import pytest

from gene_annotation_episode.bvbrc_appservice_contracts import validate_contract
from gene_annotation_episode.bvbrc_appservice_records import _encode
from gene_annotation_episode.bvbrc_genome_alignment_inputs import validate_genome_alignment_retained_records
from gene_annotation_episode.bvbrc_genome_alignment_retained_records import (
    PREFIX, RETAINED_RECORD_ERRORS, validate_retained_record_arguments,
)
from gene_annotation_episode.execution_contracts import canonical, digest


LABEL = 'SYNTHETIC task and custody; no host authentication or live scientific run'


def content(raw, name):
    return {'source_ref': 'synthetic:source:' + name, 'artifact_field': 'artifact_ref',
            'artifact_ref': 'artifact_' + hashlib.sha256(raw).hexdigest(),
            'sha256': hashlib.sha256(raw).hexdigest(), 'byte_count': len(raw)}


def wrap(contract, value, data):
    """Encode with the actual Store self-reference removal, without Store I/O."""
    validate_contract(contract, value)
    reference = (value['artifact']['transfer']['receipt_ref'] if contract == 'AcquisitionReceipt'
                 else value['receipt']['receipt_ref'])
    raw = canonical({'version': 'bvbrc_appservice_retained_receipt_v1',
                     'contract': contract, 'value': _encode(contract, value)}).encode()
    c = {**content(raw, 'envelope'), 'source_ref': reference}
    data[c['artifact_ref']] = raw
    return {'receipt_content': c, 'record': {'source_ref': reference,
                                            'contract': contract, 'value': deepcopy(value)}}


def rewrap(row, data):
    return wrap(row['record']['contract'], row['record']['value'], data)


def inline(binding_id, pointer, value, *, kind='inline_parameter'):
    return {'binding_id': binding_id, 'parameter_pointer': pointer, 'kind': kind,
        'content': None, 'workspace_path': None, 'inline_value': deepcopy(value),
        'link_evidence': None if kind == 'inline_parameter' else {
            'content': content(b'"123.1"', 'link'), 'pointer': ''}, 'members': []}


def selected(request, suffix, args, call, selector=None):
    return {'operation': 'api.bvbrc_appservice.' + suffix, 'request_sha256': digest(request),
        'arguments_sha256': digest(args), 'native_operands': {'request': deepcopy(request),
            'arguments': deepcopy(args), 'selector': deepcopy(selector), 'call': deepcopy(call),
            'local_failure': None}}


def snapshot(raw, name, operands, *, complete=True):
    c = content(raw, name)
    return {'source_ref': c['source_ref'], 'content': c, 'retrieved_at': '2026-10-25T00:00:00Z',
        'media_type': 'text/plain', 'transport': {'status': 200, 'body_complete': complete,
        'received_body_bytes': len(raw)}, 'selected_operands': deepcopy(operands)}


def common(name, snap, purpose='support', *, complete=True):
    op = snap['selected_operands']
    return {'version': 'bvbrc_appservice_support_receipt_v1',
        'receipt_ref': 'synthetic:source:' + name, 'purpose': purpose,
        'origin': {'run_id': 'synthetic_run', 'episode_id': 'synthetic_episode',
            'operation_key': 'synthetic:operation:' + name, 'name': op['operation'],
            'arguments_sha256': op['arguments_sha256'], 'assignment_sha256': 'a'*64,
            'scope_sha256': 'b'*64}, 'snapshot': snap, 'effect_receipt_refs': [],
        'status': 'ok' if complete else 'partial', 'diagnostics': []}


def fixture(genomes=('123.1', '456.2'), *, recipe='progressiveMauve', bindings=None, parameters=None):
    params = {'genome_ids': list(genomes), 'output_path': '/synthetic', 'output_file': 'run'}
    if recipe is not ...:
        params['recipe'] = recipe
    params.update(parameters or {})
    request = {'version': 'bvbrc_appservice_request_v1', 'effect_contract': 'selected_api_effects_v1',
        'required_application_id': 'GenomeAlignment', 'parameters': params, 'start_parameters': {},
        'definition_inputs': [], 'input_bindings': deepcopy(bindings or []), 'workspace_targets': []}
    args = {'preparation_receipt_ref': 'synthetic:preparation', 'input_evidence_refs': []}
    rpc = {'version': '1.1', 'id': 'synthetic_rpc_1', 'method': 'AppService.start_app2',
           'params': ['GenomeAlignment', deepcopy(params), {}]}
    native = {'id': '900001', 'application_id': 'GenomeAlignment', 'state_code': 'Q',
              'params': canonical(params)}
    raw = canonical({'version': '1.1', 'id': rpc['id'], 'result': [native]}).encode()
    snap = snapshot(raw, 'submission-native', selected(request, 'submit', args, {'rpc_request': rpc}))
    receipt = common('submission', snap, 'handoff')
    receipt['effect_receipt_refs'] = ['synthetic:submit-effect']
    task = {'resource_id': 'synthetic:api', 'task_id': native['id'],
        'required_application_id': 'GenomeAlignment', 'native_application_id': 'GenomeAlignment',
        'submitted_parameters': deepcopy(params), 'submitted_start_parameters': {},
        'scheduler_returned_parameters': {'value': deepcopy(params),
            'evidence': {'content': deepcopy(snap['content']), 'pointer': '/result/0/params'}},
        'effective_parameters': None, 'submission_receipt_ref': receipt['receipt_ref'],
        'submission_operation_key': receipt['origin']['operation_key'],
        'submission_source_ref': snap['source_ref']}
    value = {'version': 'bvbrc_appservice_task_handoff_v1', 'receipt': receipt,
        'original_job_owner': {'run_id': 'synthetic_run', 'launch_episode_id': 'synthetic_launch',
            'parent_commission_operation_key': 'synthetic:commission',
            'original_launch_assignment_sha256': 'c'*64}, 'original_task': deepcopy(task),
        'native_submission_record': native,
        'definition_evidence': {'content': content(b'{}', 'definition'), 'pointer': ''},
        'input_evidence_refs': [], 'effect_receipt_ref': 'synthetic:submit-effect',
        'state': 'submitted', 'usable_handoff': True}
    data = {snap['content']['artifact_ref']: raw}
    return task, request, wrap('TaskHandoff', value, data), data


def log_bytes(genomes=('123.1', '456.2'), *, recipe='progressiveMauve', paths=None, options=(), exit_code='0'):
    paths = list(paths) if paths is not None else ['/task/work/' + g + '.fasta' for g in genomes]
    lines = ['Fetching genomes...']
    for genome, path in zip(genomes, paths):
        lines.extend(['Fetching genome: ' + genome, 'Writing ' + path + '...'])
    lines.extend(['Running Mauve...', 'Running ' + recipe + ' with params:  --output=/task/work/alignment.xmfa'])
    for path in paths:
        lines.append(path)
        if recipe == 'mauveAligner':
            lines.append(path + '.sml')
    lines.extend(options)
    lines.append('Sequence loaded successfully.')
    if exit_code is not None:
        lines.append('child process exited with code ' + exit_code)
    return ('\n'.join(lines) + '\n').encode()


def log_record(task, request, data, *, raw=None, name='stdout', file='stdout', complete=True, window=None):
    raw = log_bytes(task['submitted_parameters']['genome_ids']) if raw is None else raw
    args = {'handoff_ref': task['submission_receipt_ref'], 'file': file}
    snap = snapshot(raw, name + ':native', selected(request, 'task_info', args,
        {'task_id': task['task_id'], 'file': file}), complete=complete)
    value = {'receipt': common(name, snap, 'observation', complete=complete),
        'original_handoff_ref': task['submission_receipt_ref'], 'task_id': task['task_id'],
        'file': file, 'reported_object_uuid': None,
        'returned_representation': 'signature_redacted_http_bytes', 'body_complete': complete,
        'local_window': window}
    if file.startswith('job_result') and complete:
        value['reported_object_uuid'] = raw.decode().strip()
    data[snap['content']['artifact_ref']] = raw
    return wrap('TaskInfoReceipt', value, data)


def acquisition_record(task, request, data, *, raw=b'>native candidate\nACGT\n', name='acquired', complete=True):
    fmt = {'format': 'fasta', 'version': None, 'mode': None,
           'producer_source_ref': None, 'transformation_evidence': []}
    obj = {'kind': 'manifest_member', 'manifest_receipt_ref': 'synthetic:manifest', 'output_index': 0}
    cap = {'kind': 'acquired', 'receipt_ref': 'synthetic:capability', 'input_index': 0}
    args = {'object': obj, 'capability': cap, 'byte_range': None, 'requirement_ids': ['synthetic:output'],
            'role': 'genome_alignment_staged_input', 'declared_format': fmt}
    selector = {'version': 'bvbrc_appservice_result_selector_v1', 'endpoint': 'requested_artifacts',
        'requirements': [{'requirement_id': 'synthetic:output', 'role': args['role'], 'required': True,
            'declared_format': fmt, 'producer_rule_evidence': None, 'exact_object': obj}],
        'adapter': None, 'requested_schema': {'type': 'object', 'additionalProperties': False,
        'properties': {}, 'required': []}, 'supplied_metadata': [], 'supplied_contents': [], 'supplied_capabilities': []}
    snap = snapshot(raw, name + ':native', selected(request, 'download', args,
        {'url': 'https://synthetic.invalid/selected', 'byte_range': None}, selector), complete=complete)
    receipt = common(name, snap, 'acquisition', complete=complete)
    c = snap['content']
    artifact = {'role': args['role'], 'source_ref': c['source_ref'], 'raw_artifact_ref': c['artifact_ref'],
        'sha256': c['sha256'], 'byte_count': c['byte_count'], 'workspace_object': {
            'path': '/synthetic/candidate.fasta', 'uuid': '11111111-1111-1111-1111-111111111111',
            'type': 'txt', 'metadata_receipt_ref': None}, 'task_association': {
            'kind': 'task_result_manifest', 'evidence_ref': 'synthetic:manifest-source',
            'pointer': '/output_files/0', 'task_id': task['task_id'],
            'output_path': '/synthetic/candidate.fasta', 'output_uuid': '11111111-1111-1111-1111-111111111111',
            'byte_version_status': 'unknown', 'version_evidence': []},
        'transfer': {'receipt_ref': receipt['receipt_ref'], 'body_complete': complete,
            'requested_range': None, 'observed_range': None, 'total_size': len(raw) if complete else None,
            'object_complete': 'yes' if complete else 'no'}, 'declared_format': fmt}
    value = {'version': 'bvbrc_appservice_acquisition_v1', 'origin': receipt['origin'],
        'original_handoff_ref': task['submission_receipt_ref'], 'selector_sha256': digest(selector),
        'snapshot': snap, 'capability_selection': cap, 'object_selection': obj,
        'artifact': artifact, 'requirement_ids': args['requirement_ids'],
        'publication_inputs_sha256': 'd'*64, 'publication_ref': None,
        'valid_record_refs': [c['source_ref']], 'status': 'ok' if complete else 'partial', 'failure': None}
    data[c['artifact_ref']] = raw
    return wrap('AcquisitionReceipt', value, data)


def check(task, records, data):
    return validate_genome_alignment_retained_records(task, retained_records=records, supplied_bytes=data)


def test_actual_complete_receipt_contracts_and_envelopes_are_detached():
    task, request, handoff, data = fixture()
    log = log_record(task, request, data)
    acquisition = acquisition_record(task, request, data)
    records = (handoff, log, acquisition)
    before = deepcopy((task, records, data))
    checked = check(task, records, data)
    assert checked == records
    checked[0]['record']['value']['original_task']['task_id'] = 'changed'
    assert (task, records, data) == before
    assert validate_retained_record_arguments(task, retained_records=records, supplied_bytes=data) is None


@pytest.mark.parametrize('contract', ['handoff', 'log', 'acquisition'])
@pytest.mark.parametrize('field', ['envelope_missing', 'envelope_digest', 'snapshot_missing', 'snapshot_digest'])
def test_each_required_representation_has_exact_byte_identity(contract, field):
    task, request, handoff, data = fixture()
    rows = {'handoff': handoff, 'log': log_record(task, request, data),
            'acquisition': acquisition_record(task, request, data)}
    row = rows[contract]
    value = row['record']['value']
    snap = value['snapshot'] if contract == 'acquisition' else value['receipt']['snapshot']
    binding = row['receipt_content'] if field.startswith('envelope') else snap['content']
    if field.endswith('missing'):
        del data[binding['artifact_ref']]
        code = 'content_missing'
    else:
        data[binding['artifact_ref']] += b'changed'
        code = 'content_digest_conflict'
    with pytest.raises(ValueError, match='^' + PREFIX + code + '$'):
        check(task, (row,), data)


@pytest.mark.parametrize('mutate', ['wrapper_extra', 'wrapper_missing', 'receipt_extra', 'unsupported_contract',
    'bool_count', 'records_list', 'bytes_bytearray', 'bytes_wrong_key', 'task_extra'])
def test_whole_argument_shape_errors_precede_semantic_extraction(mutate):
    task, _, row, data = fixture()
    rows = (row,)
    if mutate == 'wrapper_extra': row['trusted'] = True
    elif mutate == 'wrapper_missing': del row['receipt_content']
    elif mutate == 'receipt_extra': row['record']['value']['deployment_verified'] = True
    elif mutate == 'unsupported_contract': row['record']['contract'] = 'TrustReceipt'
    elif mutate == 'bool_count': row['receipt_content']['byte_count'] = True
    elif mutate == 'records_list': rows = [row]
    elif mutate == 'bytes_bytearray': data['arbitrary'] = bytearray(b'x')
    elif mutate == 'bytes_wrong_key': data[1] = b'x'
    else: task['unrecognized'] = 1
    code = 'original_task_invalid' if mutate == 'task_extra' else 'argument_invalid'
    with pytest.raises(ValueError, match='^' + PREFIX + code + '$'):
        check(task, rows, data)


@pytest.mark.parametrize('mutate', ['noncanonical', 'duplicate_member', 'nan', 'wrong_envelope', 'wrong_self_ref'])
def test_canonical_envelope_is_the_existing_typed_value(mutate):
    task, request, _, data = fixture()
    row = log_record(task, request, data)
    binding = row['receipt_content']
    raw = data[binding['artifact_ref']]
    if mutate == 'noncanonical': raw = json.dumps(json.loads(raw), indent=2).encode()
    elif mutate == 'duplicate_member': raw = raw.replace(b'"version":', b'"version":"wrong","version":', 1)
    elif mutate == 'nan': raw = raw.replace(b'"body_complete":true', b'"body_complete":NaN', 1)
    elif mutate == 'wrong_envelope': raw = raw.replace(b'TaskInfoReceipt', b'TaskHandoff', 1)
    else: row['record']['value']['receipt']['receipt_ref'] = 'another-self-reference'
    binding.update(sha256=hashlib.sha256(raw).hexdigest(), byte_count=len(raw))
    data[binding['artifact_ref']] = raw
    with pytest.raises(ValueError, match='^' + PREFIX + 'metadata_record_unverified$'):
        check(task, (row,), data)


@pytest.mark.parametrize('mutate', ['task', 'handoff', 'request', 'start', 'call', 'origin', 'digest'])
def test_task_info_cannot_detach_selected_call_from_task(mutate):
    task, request, _, data = fixture()
    row = log_record(task, request, data)
    value = row['record']['value']
    selected_value = value['receipt']['snapshot']['selected_operands']
    native = selected_value['native_operands']
    if mutate == 'task': value['task_id'] = 'OTHER'
    elif mutate == 'handoff': value['original_handoff_ref'] = 'other-handoff'
    elif mutate == 'request': native['request']['parameters']['genome_ids'].reverse()
    elif mutate == 'start': native['request']['start_parameters']['base_url'] = 'https://other.invalid'
    elif mutate == 'call': native['call']['file'] = 'stderr'
    elif mutate == 'origin': value['receipt']['origin']['name'] = 'api.bvbrc_appservice.status'
    else: selected_value['request_sha256'] = '0'*64
    row = rewrap(row, data)
    with pytest.raises(ValueError, match='^' + PREFIX + 'metadata_task_conflict$'):
        check(task, (row,), data)


@pytest.mark.parametrize('mutate', ['resource', 'source', 'operation_key', 'native_task', 'rpc_params'])
def test_original_handoff_native_submission_relationship(mutate):
    task, _, row, data = fixture()
    value = row['record']['value']
    if mutate == 'resource': value['original_task']['resource_id'] = 'other-resource'
    elif mutate == 'source': value['original_task']['submission_source_ref'] = 'other-source'
    elif mutate == 'operation_key': value['receipt']['origin']['operation_key'] = 'other-operation'
    elif mutate == 'native_task': value['native_submission_record']['id'] = 'OTHER'
    else: value['receipt']['snapshot']['selected_operands']['native_operands']['call']['rpc_request']['params'][0] = 'Homology'
    row = rewrap(row, data)
    expected = 'metadata_record_unverified' if mutate == 'native_task' else 'metadata_task_conflict'
    with pytest.raises(ValueError, match='^' + PREFIX + expected + '$'):
        check(task, (row,), data)


@pytest.mark.parametrize('mutate', ['task', 'object_selection', 'capability', 'artifact_bytes', 'selector', 'range', 'publication'])
def test_acquisition_keeps_exact_selected_artifact_relationship(mutate):
    task, request, _, data = fixture()
    row = acquisition_record(task, request, data)
    value = row['record']['value']
    if mutate == 'task': value['artifact']['task_association']['task_id'] = 'OTHER'
    elif mutate == 'object_selection': value['object_selection']['output_index'] = 2
    elif mutate == 'capability': value['capability_selection']['input_index'] = 1
    elif mutate == 'artifact_bytes': value['artifact']['sha256'] = '0'*64
    elif mutate == 'selector': value['selector_sha256'] = '0'*64
    elif mutate == 'range': value['artifact']['transfer']['requested_range'] = [1, None]
    else:
        # Real stored acquisitions never contain a publication self-loop.
        value['publication_ref'] = 'unrelated-publication'
        raw = canonical({'version': 'bvbrc_appservice_retained_receipt_v1', 'contract': 'AcquisitionReceipt',
                         'value': {**value, 'artifact': deepcopy(value['artifact'])}}).encode()
        del value['artifact']['transfer']['receipt_ref']
        value['artifact']['transfer']['receipt_ref'] = row['record']['source_ref']
        # _encode correctly refuses this condition; check it as a supplied
        # shape-valid noncanonical evidence envelope instead.
        data[row['receipt_content']['artifact_ref']] = raw
        row['receipt_content'].update(sha256=hashlib.sha256(raw).hexdigest(), byte_count=len(raw))
    if mutate != 'publication':
        row = rewrap(row, data)
    expected = ('metadata_task_conflict' if mutate == 'task' else 'content_digest_conflict' if
                mutate == 'artifact_bytes' else 'metadata_record_unverified')
    with pytest.raises(ValueError, match='^' + PREFIX + expected + '$'):
        check(task, (row,), data)


def test_partial_windowed_log_receipt_is_retained_for_caller_interpretation():
    task, request, _, data = fixture()
    row = log_record(task, request, data, complete=False, window={'start': 0, 'end_exclusive': 10})
    assert check(task, (row,), data) == (row,)


@pytest.mark.parametrize('wrong_uuid', ['22222222-2222-2222-2222-222222222222', None])
def test_task_info_object_value_must_equal_actual_returned_uuid(wrong_uuid):
    task, request, _, data = fixture()
    row = log_record(task, request, data, raw=b'11111111-1111-1111-1111-111111111111\n', file='job_result_id')
    row['record']['value']['reported_object_uuid'] = wrong_uuid
    row = rewrap(row, data)
    with pytest.raises(ValueError, match='^' + PREFIX + 'metadata_record_unverified$'):
        check(task, (row,), data)


@pytest.mark.parametrize('field', ['params', 'parameters', 'app'])
def test_native_submission_echo_conflict_is_not_hidden_by_missing_scheduler_projection(field):
    task, _, row, data = fixture()
    value = row['record']['value']
    task['scheduler_returned_parameters'] = value['original_task']['scheduler_returned_parameters'] = None
    native = value['native_submission_record']
    if field == 'app':
        native['app'] = 'Homology'
    else:
        changed = deepcopy(task['submitted_parameters'])
        changed['genome_ids'].reverse()
        native[field] = canonical(changed) if field == 'params' else changed
    snap = value['receipt']['snapshot']
    rpc_id = snap['selected_operands']['native_operands']['call']['rpc_request']['id']
    raw = canonical({'version': '1.1', 'id': rpc_id, 'result': [native]}).encode()
    c = content(raw, 'submission-native')
    snap['content'] = c
    snap['transport']['received_body_bytes'] = len(raw)
    data[c['artifact_ref']] = raw
    row = rewrap(row, data)
    with pytest.raises(ValueError, match='^' + PREFIX + 'metadata_task_conflict$'):
        check(task, (row,), data)


def test_known_helper_error_set_is_finite_and_shape_errors_are_not_recoverable():
    assert RETAINED_RECORD_ERRORS == {PREFIX + x for x in ('content_missing', 'content_digest_conflict',
        'metadata_record_unverified', 'metadata_task_conflict')}
