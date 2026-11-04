"""Pure checks of supplied GenomeAlignment receipt representations.

These checks establish relationships *within supplied data*. Only the AppService
host can authenticate receipt possession, producing actions, resource ownership
and the underlying Store. This module never reads the Store or an input path.
"""
from copy import deepcopy
import hashlib
import json
import math

from .bvbrc_analysis_protocol import decode_rpc_response, parse_task_records, parse_workspace_records
from .bvbrc_appservice_contracts import (
    ContractValidationError, _at, _same, validate_contract, validate_request,
)
from .bvbrc_appservice_readers import decode_task_info


PREFIX = 'bvbrc_genome_alignment_'
RETAINED_RECORD_ERRORS = frozenset(PREFIX + code for code in (
    'content_missing', 'content_digest_conflict', 'metadata_record_unverified',
    'metadata_task_conflict',
))
_CONTRACTS = ('TaskHandoff', 'TaskInfoReceipt', 'AcquisitionReceipt', 'WorkspaceReceipt')
_VERSION = 'bvbrc_appservice_retained_receipt_v1'
_OPERATIONS = {name: 'api.bvbrc_appservice.' + suffix for name, suffix in (
    ('TaskHandoff', 'submit'), ('TaskInfoReceipt', 'task_info'),
    ('AcquisitionReceipt', 'download'), ('WorkspaceReceipt', 'workspace_metadata'))}


def _require(condition, code='metadata_record_unverified'):
    if not condition:
        raise ValueError(PREFIX + code)


def _canonical(value):
    # This is the Store's existing execution_contracts.canonical JSON encoding.
    # Inputs here have already passed the existing plain finite JSON validator.
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode('utf-8')


def _digest(value):
    return hashlib.sha256(_canonical(value)).hexdigest()


def _json(raw):
    """Unique-key finite JSON; no duplicate member silently wins."""
    def pairs(rows):
        result = {}
        for key, value in rows:
            _require(key not in result)
            result[key] = value
        return result

    def number(token):
        value = float(token)
        _require(math.isfinite(value))
        # Do not permit a nonzero JSON measurement to underflow to zero.
        _require(value != 0 or not any(c in '123456789' for c in token.lower().split('e')[0]))
        return value

    def constant(_):
        raise ValueError(PREFIX + 'metadata_record_unverified')

    try:
        return json.loads(raw.decode('utf-8'), object_pairs_hook=pairs,
                          parse_float=number, parse_constant=constant)
    except (ValueError, UnicodeError, RecursionError) as error:
        raise ValueError(PREFIX + 'metadata_record_unverified') from error


def supplied_content(binding, supplied_bytes):
    """Check an already shape-validated ContentBinding against supplied bytes."""
    raw = supplied_bytes.get(binding['artifact_ref'])
    _require(raw is not None, 'content_missing')
    _require(len(raw) == binding['byte_count'] and
             hashlib.sha256(raw).hexdigest() == binding['sha256'], 'content_digest_conflict')
    return raw


def supplied_evidence(evidence, supplied_bytes):
    """Resolve an actual JSON pointer, never a path or a basename join."""
    raw = supplied_content(evidence['content'], supplied_bytes)
    try:
        return _at(_json(raw), evidence['pointer'])
    except ContractValidationError as error:
        raise ValueError(PREFIX + 'metadata_record_unverified') from error


def validate_retained_record_arguments(original_task: dict, *, retained_records: tuple,
                                      supplied_bytes: dict[str, bytes]) -> None:
    """Whole-argument preflight for both C callers, before local recovery.

    Return None. The existing schemas (including their internal relationships)
    are required; this preflight does not admit any receipt's scientific facts.
    """
    _require(type(retained_records) is tuple and type(supplied_bytes) is dict,
             'argument_invalid')
    _require(all(type(k) is str and k and type(v) is bytes
                 for k, v in supplied_bytes.items()), 'argument_invalid')
    try:
        validate_contract('OriginalTask', original_task)
    except ContractValidationError as error:
        raise ValueError(PREFIX + 'original_task_invalid') from error
    for row in retained_records:
        _require(type(row) is dict and set(row) == {'receipt_content', 'record'},
                 'argument_invalid')
        record = row['record']
        _require(type(record) is dict and set(record) == {'source_ref', 'contract', 'value'},
                 'argument_invalid')
        _require(type(record['source_ref']) is str and bool(record['source_ref']) and
                 type(record['contract']) is str and record['contract'] in _CONTRACTS,
                 'argument_invalid')
        try:
            validate_contract('ContentBinding', row['receipt_content'])
            validate_contract(record['contract'], record['value'])
        except ContractValidationError as error:
            raise ValueError(PREFIX + 'argument_invalid') from error


def _selected(snapshot, origin, contract, original_task):
    selected = snapshot['selected_operands']
    _require(set(selected) == {'operation', 'request_sha256', 'arguments_sha256', 'native_operands'})
    native = selected['native_operands']
    _require(type(native) is dict and set(native) ==
             {'request', 'arguments', 'selector', 'call', 'local_failure'})
    try:
        request = validate_request(native['request'])
        validate_contract('OperationSelection',
                          {'name': selected['operation'], 'arguments': native['arguments']})
        if native['selector'] is not None:
            validate_contract('ResultSelector', native['selector'])
    except ContractValidationError as error:
        raise ValueError(PREFIX + 'metadata_record_unverified') from error
    _require(selected['operation'] == origin['name'] == _OPERATIONS[contract],
             'metadata_task_conflict')
    _require(selected['request_sha256'] == _digest(request) and
             selected['arguments_sha256'] == origin['arguments_sha256'] == _digest(native['arguments']),
             'metadata_task_conflict')
    _require(request['required_application_id'] == original_task['required_application_id'] and
             _same(request['parameters'], original_task['submitted_parameters']) and
             _same(request['start_parameters'], original_task['submitted_start_parameters']),
             'metadata_task_conflict')
    _require(native['local_failure'] is None and type(native['call']) is dict)
    return native


def _handoff(value, original_task, native, raw):
    common, snapshot = value['receipt'], value['receipt']['snapshot']
    _require(_same(value['original_task'], original_task) and
             common['receipt_ref'] == original_task['submission_receipt_ref'] and
             common['origin']['operation_key'] == original_task['submission_operation_key'] and
             snapshot['source_ref'] == original_task['submission_source_ref'] and
             value['original_job_owner']['run_id'] == common['origin']['run_id'],
             'metadata_task_conflict')
    _require(common['purpose'] == 'handoff' and common['status'] == 'ok' and
             native['selector'] is None and value['effect_receipt_ref'] in common['effect_receipt_refs'] and
             value['input_evidence_refs'] == native['arguments']['input_evidence_refs'])
    call = native['call']
    _require(set(call) == {'rpc_request'} and type(call['rpc_request']) is dict)
    rpc = call['rpc_request']
    _require(set(rpc) == {'version', 'method', 'params', 'id'} and rpc['version'] == '1.1')
    _require(rpc['method'] == 'AppService.start_app2' and _same(rpc['params'], [
        original_task['native_application_id'], original_task['submitted_parameters'],
        original_task['submitted_start_parameters']]), 'metadata_task_conflict')
    _require(snapshot['transport']['body_complete'])
    decoded = decode_rpc_response(raw, method=rpc['method'], request_id=rpc['id'],
                                  http_status=snapshot['transport']['status'])
    _require(decoded['status'] == 'ok' and _same(decoded['value'], value['native_submission_record']))
    parsed = parse_task_records(decoded['value'], operation='start_app2')
    _require(parsed['status'] == 'ok' and len(parsed['records']) == 1)
    task = parsed['records'][0]
    _require(str(task['task_id']) == original_task['task_id'] and
             task['application_id'] in (None, original_task['native_application_id']),
             'metadata_task_conflict')
    native_task = value['native_submission_record']
    for field in ('application_id', 'app'):
        _require(native_task.get(field) in (None, original_task['native_application_id']),
                 'metadata_task_conflict')
    for field in ('params', 'parameters', 'start_parameters'):
        echoed = native_task.get(field)
        if echoed is None:
            continue
        if field == 'params':
            _require(type(echoed) is str, 'metadata_task_conflict')
            echoed = _json(echoed.encode('utf-8'))
        expected = original_task['submitted_start_parameters' if field == 'start_parameters' else 'submitted_parameters']
        _require(type(echoed) is dict and all(k in echoed and _same(echoed[k], v)
                 for k, v in expected.items()), 'metadata_task_conflict')
    _require(task['native_state'] not in ('F', 'D', 'T'))
    for name in ('scheduler_returned_parameters', 'effective_parameters'):
        recorded = original_task[name]
        if recorded is not None and recorded['evidence']['content'] == snapshot['content']:
            observed = supplied_evidence(recorded['evidence'], {snapshot['content']['artifact_ref']: raw})
            # Native start_app2's params is a JSON string; the existing handoff
            # records its decoded object and the original string's pointer.
            if recorded['evidence']['pointer'] == '/result/0/params' and type(observed) is str:
                observed = _json(observed.encode('utf-8'))
            _require(_same(observed, recorded['value']), 'metadata_task_conflict')


def _task_info(value, original_task, native, raw):
    _require(value['original_handoff_ref'] == original_task['submission_receipt_ref'] and
             value['task_id'] == original_task['task_id'] and
             native['arguments'] == {'handoff_ref': original_task['submission_receipt_ref'],
                                     'file': value['file']} and
             native['call'] == {'task_id': original_task['task_id'], 'file': value['file']},
             'metadata_task_conflict')
    _require(value['receipt']['purpose'] == 'observation' and value['body_complete'] is
             value['receipt']['snapshot']['transport']['body_complete'])
    # Task stdout completeness is interpreted by the caller, independently of
    # receipt admission. A window or truncated response remains a real record.
    if value['file'] in ('job_result_id', 'job_result_folder') and value['body_complete']:
        try:
            decoded = decode_task_info(raw, task_id=original_task['task_id'], file=value['file'])
        except ContractValidationError as error:
            raise ValueError(PREFIX + 'metadata_record_unverified') from error
        _require(decoded['value']['reported_object_uuid'] == value['reported_object_uuid'])


def _workspace(value, native, raw):
    """Check the real Workspace.get metadata used by a receipt_row selection."""
    snapshot = value['receipt']['snapshot']
    _require(value['method'] == 'Workspace.get' and snapshot['transport']['body_complete']
        and _same(value['requested_objects'], native['arguments']['objects']))
    call = native['call']
    _require(set(call) == {'rpc_request'} and type(call['rpc_request']) is dict)
    rpc = call['rpc_request']
    _require(set(rpc) == {'version', 'method', 'params', 'id'} and rpc['version'] == '1.1'
        and rpc['method'] == 'Workspace.get' and type(rpc['params']) is list and len(rpc['params']) == 1)
    options = rpc['params'][0]
    _require(type(options) is dict and options.get('metadata_only') == 1
        and type(options.get('objects')) is list
        and len(options['objects']) == len(value['requested_objects']))
    decoded = decode_rpc_response(raw, method=rpc['method'], request_id=rpc['id'],
        http_status=snapshot['transport']['status'])
    _require(decoded['status'] == 'ok' and _same(decoded['value'], value['native_value']))
    parsed = parse_workspace_records(decoded['value'], operation='get', requested_paths=options['objects'])
    _require(len(parsed['records']) == len(value['rows']))
    for row, saved in zip(parsed['records'], value['rows']):
        expected = {'pointer': '/result/0/' + str(row['row_index']), 'native_row': row['native_record'],
            'path': row['object_path'] or None, 'uuid': row['object_id'] or None, 'type': row['type'] or None,
            'shock_url': row['shock_url'] or None, 'creation_time': row['creation_time'],
            'size': row['size'], 'error': row['error']}
        _require(all(_same(saved[k], v) for k, v in expected.items())
            and (not saved['valid'] or row['status'] == 'ok'))
    # The host may additionally mark a parsed row invalid for conflict with an
    # original selected type/UUID. Preserve that failure; never promote it.
    returned = {i for row, saved in zip(parsed['records'], value['rows']) if saved['valid']
        for i in row['request_indices']}
    _require(value['missing_requested_indices'] == [i for i in range(len(value['requested_objects']))
        if i not in returned])


def _acquisition(value, original_task, native):
    artifact, snapshot, args = value['artifact'], value['snapshot'], native['arguments']
    transfer, content = artifact['transfer'], snapshot['content']
    _require(value['original_handoff_ref'] == original_task['submission_receipt_ref'] and
             artifact['task_association']['task_id'] == original_task['task_id'], 'metadata_task_conflict')
    _require(value['publication_ref'] is None and native['selector'] is not None and
             value['selector_sha256'] == _digest(native['selector']))
    _require(value['capability_selection'] == args['capability'] and
             value['object_selection'] == args['object'] and
             value['requirement_ids'] == args['requirement_ids'] and
             artifact['role'] == args['role'] and artifact['declared_format'] == args['declared_format'] and
             transfer['requested_range'] == args['byte_range'])
    _require(artifact['source_ref'] == snapshot['source_ref'] and
             artifact['raw_artifact_ref'] == content['artifact_ref'] and
             artifact['sha256'] == content['sha256'] and artifact['byte_count'] == content['byte_count'],
             'content_digest_conflict')
    _require(transfer['body_complete'] is snapshot['transport']['body_complete'])
    call = native['call']
    _require(set(call) == {'url', 'byte_range'} and type(call['url']) is str and bool(call['url']) and
             call['byte_range'] == args['byte_range'])
    # The real download URL and object/capability dependency were authenticated
    # by the host. Compare transport fields when retained; never invent them.
    transport = snapshot['transport']
    if 'request' in transport:
        _require(type(transport['request']) is dict and
                 transport['request'].get('url') == call['url'] and
                 transport['request'].get('method') == 'GET')
    if 'effective_url' in transport:
        _require(transport['effective_url'] == call['url'])


def validate_genome_alignment_retained_records(original_task: dict, *, retained_records: tuple,
                                              supplied_bytes: dict[str, bytes]) -> tuple[dict, ...]:
    """Return detached validated records, or one finite error; never drop one.

    C callers preflight the complete tuple, then call this with a one-item tuple
    and catch only RETAINED_RECORD_ERRORS. Cross-record conflicts belong to the
    caller so unaffected neighbors survive. This function authenticates no host.
    """
    validate_retained_record_arguments(original_task, retained_records=retained_records,
                                      supplied_bytes=supplied_bytes)
    for row in retained_records:
        record, binding = row['record'], row['receipt_content']
        contract, value, reference = record['contract'], record['value'], record['source_ref']
        raw_envelope = supplied_content(binding, supplied_bytes)
        _require(binding['source_ref'] == reference and binding['artifact_field'] == 'artifact_ref')
        stored = deepcopy(value)
        if contract == 'AcquisitionReceipt':
            _require(stored['artifact']['transfer'].pop('receipt_ref') == reference)
            origin, snapshot = value['origin'], value['snapshot']
        else:
            _require(stored['receipt'].pop('receipt_ref') == reference)
            origin, snapshot = value['receipt']['origin'], value['receipt']['snapshot']
            if contract == 'TaskHandoff':
                _require(stored['original_task'].pop('submission_receipt_ref') == reference,
                         'metadata_task_conflict')
        envelope = {'version': _VERSION, 'contract': contract, 'value': stored}
        try:
            _require(_same(_json(raw_envelope), envelope) and raw_envelope == _canonical(envelope))
        except UnicodeError as error:
            raise ValueError(PREFIX + 'metadata_record_unverified') from error
        _require(snapshot is not None, 'content_missing')
        raw = supplied_content(snapshot['content'], supplied_bytes)
        _require(snapshot['content']['artifact_field'] == 'artifact_ref')
        transport = snapshot['transport']
        _require(type(transport.get('status')) is int and 100 <= transport['status'] <= 599 and
                 type(transport.get('body_complete')) is bool and
                 type(transport.get('received_body_bytes')) is int and
                 transport['received_body_bytes'] == len(raw))
        native = _selected(snapshot, origin, contract, original_task)
        if contract == 'TaskHandoff':
            _handoff(value, original_task, native, raw)
        elif contract == 'TaskInfoReceipt':
            _task_info(value, original_task, native, raw)
        elif contract == 'WorkspaceReceipt':
            _workspace(value, native, raw)
        else:
            _acquisition(value, original_task, native)
    return deepcopy(retained_records)


__all__ = ['validate_genome_alignment_retained_records', 'validate_retained_record_arguments',
           'RETAINED_RECORD_ERRORS']
