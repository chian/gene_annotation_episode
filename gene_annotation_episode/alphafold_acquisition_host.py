"""Authenticate one advertised AlphaFold download through existing custody.

Root dispatch authenticates the selected current RuntimeAction. This host binds
its received metadata to an actual original prediction operation, and retains
only a small selection witness in addition to the original HTTP representations.
"""
from copy import deepcopy
import hashlib
import json

from . import alphafold_acquisition as af
from .acquisition import SourceSnapshot
from .communication import plain
from .domain import ContractError, canonical, identity
from .episode_return_records import EpisodeReturnRecords
from .waiting import validate_pending


PREDICTION_TOOL = 'public.alphafold.prediction'
FILE_TOOL = 'public.alphafold.file'
SELECTION_VERSION = 'alphafold_file_selection_v1'
FILE_EVIDENCE_VERSION = 'alphafold_file_receipt_evidence_v1'


def _require(condition, code='alphafold_file_custody_conflict'):
    if not condition:
        raise ContractError(code)


def _same(left, right):
    return canonical(left) == canonical(right)


def _artifact_metadata(store, reference):
    value = store.get(reference)
    _require(value.get('record_type') == 'artifact' and value.get('id') == reference
        and reference == 'artifact_' + value.get('sha256', '')
        and type(value.get('size')) is int and value['size'] >= 0,
        'alphafold_file_artifact_identity_conflict')
    return value


def _control(store, reference):
    metadata = _artifact_metadata(store, reference)
    raw = store.get_artifact(reference)
    _require(len(raw) == metadata['size'] and hashlib.sha256(raw).hexdigest() == metadata['sha256'],
        'alphafold_file_artifact_identity_conflict')
    try:
        value = json.loads(raw)
        _require(raw == canonical(value).encode(), 'alphafold_file_control_invalid')
    except (ValueError, UnicodeError, TypeError, OverflowError) as error:
        raise ContractError('alphafold_file_control_invalid') from error
    return value


def _source(store, reference):
    value = store.get(reference)
    _require(value.get('record_type') == 'source' and value.get('origin') == 'external'
        and value.get('provider') == af.SERVICE and value.get('version') is None,
        'alphafold_file_source_invalid')
    payload = {key: child for key, child in value.items() if key not in {'id', 'record_type', 'origin'}}
    _require(value.get('id') == reference
        and identity('source', {'origin': value['origin'], 'record': payload}) == reference,
        'alphafold_file_source_identity_conflict')
    return value


def _authority(registry, authority):
    _require(type(authority) is tuple and len(authority) == 2 and callable(authority[1]),
        'alphafold_file_received_input_authority_required')
    context, reader = authority
    EpisodeReturnRecords(registry.store, context.run_id, failure_prefix='alphafold_file_').authenticate(context)
    return context, reader


def _without_pending(value):
    value = deepcopy(value)
    if 'pending_work_after_action' in value:
        validate_pending(value.pop('pending_work_after_action'))
    return value


def _saved_response(transport, retained_bytes):
    """Copy qualified transport fields using metadata, without entity reads."""
    headers = transport.get('headers')
    content_type = headers.get('content-type') if type(headers) is dict else None
    status, complete = transport.get('status'), transport.get('body_complete')
    counts = {key: transport.get(key) if type(transport.get(key)) is int and transport[key] >= 0 else None
        for key in ('observed_body_bytes', 'declared_body_bytes')}
    return {'http_status': status if type(status) is int and 100 <= status <= 599 else None,
        'content_type': content_type if type(content_type) is str else None,
        'body_complete': complete if type(complete) is bool else None,
        'retained_bytes': retained_bytes, **counts}


def _operation(registry, source_ref, tool_name, *, expected=None, without_source=None):
    if source_ref is None:
        _require(type(without_source) is dict, 'alphafold_file_original_operation_conflict')
        rows = registry.store.db.execute("SELECT * FROM tool_operations WHERE name=? AND id=?",
            (tool_name, without_source.get('operation_ref'))).fetchall()
    else:
        rows = registry.store.db.execute("SELECT * FROM tool_operations WHERE name=? "
            "AND json_extract(result,'$.result.source_ref')=?", (tool_name, source_ref)).fetchall()
    _require(len(rows) == 1, 'alphafold_file_original_operation_conflict')
    row = rows[0]
    arguments, outcome = json.loads(row['arguments']), json.loads(row['result'])
    _require(type(outcome) is dict and row['id'] == identity('operation', {'key': row['operation_key'], 'name': tool_name,
        'arguments': arguments}) and outcome.get('operation_ref') == row['id']
        and outcome.get('status') in ({'completed', 'partial', 'failed'} if source_ref is not None else
            {'completed', 'partial', 'failed', 'invalid', 'unavailable'})
        and type(outcome.get('record_refs')) is list and all(type(ref) is str for ref in outcome['record_refs'])
        and (source_ref in outcome['record_refs'] if source_ref is not None else
            not outcome['record_refs'] and _same(outcome, without_source)),
        'alphafold_file_original_operation_conflict')
    operation = {'operation_key': row['operation_key'], 'operation_ref': row['id']}
    _require(expected is None or _same(operation, expected), 'alphafold_file_original_operation_conflict')
    tables = {value[0] for value in registry.store.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    actions = ([] if 'runtime_actions' not in tables else registry.store.db.execute(
        "SELECT * FROM runtime_actions WHERE ?=run_id||':'||episode_id||':'||decision_index",
        (row['operation_key'],)).fetchall())
    _require(len(actions) <= 1, 'alphafold_file_original_action_conflict')
    if actions:
        action = actions[0]
        producer = EpisodeReturnRecords(registry.store, action['run_id'],
            failure_prefix='alphafold_file_').context(action['episode_id'])
        _require(row['scope'] == canonical(plain(producer.scope))
            and _same(json.loads(action['action']), {'kind': 'tool', 'tool': tool_name, 'arguments': arguments}),
            'alphafold_file_original_action_conflict')
        if action['result'] is not None:
            _require(_same(_without_pending(json.loads(action['result'])), outcome),
                'alphafold_file_original_action_conflict')
        else:
            _require(tool_name == FILE_TOOL, 'alphafold_file_original_action_incomplete')
    return operation, arguments, outcome


def _metadata(registry, source_ref, *, expected=None):
    source = _source(registry.store, source_ref)
    operation, arguments, outcome = _operation(registry, source_ref, PREDICTION_TOOL, expected=expected)
    _require(outcome['status'] in {'completed', 'partial'}, 'alphafold_file_metadata_not_acquired')
    arguments = af.validate_alphafold_prediction_arguments(arguments)
    if type(outcome['result']) is dict and 'acquired' in outcome['result']:
        receipt = af.validate_alphafold_receipt(outcome['result'])
        _require(receipt['acquired'] and receipt['source_ref'] == source_ref
            and receipt['data_ref'] == source['artifact_ref']
            and outcome['record_refs'] == [source_ref, source['artifact_ref']],
            'alphafold_file_metadata_not_acquired')
        auxiliary = source.get('auxiliary_artifact_refs')
        _require(type(auxiliary) is list and len(auxiliary) == 1,
            'alphafold_file_metadata_value_conflict')
        value = af.validate_alphafold_prediction_value(_control(registry.store, auxiliary[0]))
        metadata = _artifact_metadata(registry.store, source['artifact_ref'])
        retained = _control(registry.store, source['request_ref'])
        _require(type(retained) is dict and set(retained) == {'request', 'transport'}
            and _same(retained['request'], arguments), 'alphafold_file_metadata_request_conflict')
        transport = retained['transport']
        _require(type(transport) is dict and type(transport.get('request')) is dict
            and transport['request'].get('method') == 'GET'
            and transport['request'].get('url') == source['uri'],
            'alphafold_file_metadata_request_conflict')
        response, issues = af._response_metadata(transport, metadata['size'], arguments['max_bytes'])
        _require(value['raw_artifact_ref'] == source['artifact_ref']
            and _same(value['requested'], arguments) and _same(value['response'], response)
            and _same([row for row in value['issues'] if row['code'] != 'invalid_native_json'], issues)
            and _same(af.alphafold_prediction_receipt(value, source_ref=source_ref), receipt),
            'alphafold_file_metadata_value_conflict')
        result = af.alphafold_prediction_result_from_value(value, source_ref=source_ref)
    else:
        result = af.validate_alphafold_prediction_result(outcome['result'])
    _require(_same(result['requested'], arguments) and result['source_ref'] == source_ref
        and result['raw_artifact_ref'] == source['artifact_ref']
        and source['uri'] == af.alphafold_prediction_url(arguments['identifier'])
        and source['accession'] == arguments['identifier'], 'alphafold_file_metadata_identity_conflict')
    return source, operation, arguments, result


def _selection(registry, value, arguments):
    arguments = af.validate_alphafold_file_arguments(arguments)
    _require(type(value) is dict and set(value) == {'version', 'arguments', 'association', 'metadata_operation'}
        and value['version'] == SELECTION_VERSION and _same(value['arguments'], arguments),
        'alphafold_file_selection_conflict')
    association = af.validate_alphafold_file_association(value['association'], arguments=arguments)
    _require(type(value['metadata_operation']) is dict
        and set(value['metadata_operation']) == {'operation_key', 'operation_ref'}, 'alphafold_file_selection_conflict')
    source, operation, _, result = _metadata(registry, arguments['metadata_source_ref'], expected=value['metadata_operation'])
    _require(association['metadata_artifact_ref'] == source['artifact_ref']
        and af.alphafold_advertised_file_url(result['native_json'], arguments=arguments) == association['advertised_url'],
        'alphafold_file_selection_conflict')
    return deepcopy(value), source, result


def prepare_alphafold_file(registry, arguments, *, authority):
    arguments = af.validate_alphafold_file_arguments(arguments)
    context, reader = _authority(registry, authority)
    received = reader(context, arguments['metadata_source_ref'], 'source', source_metadata_only=True)
    _require(received['failure'] is None and received['input'] is not None,
        'alphafold_file_metadata_not_received')
    source, operation, original_arguments, result = _metadata(registry, arguments['metadata_source_ref'])
    _require(_same(received['input']['witness']['record'], source), 'alphafold_file_source_identity_conflict')
    received_file, path = reader(context, source['id'], 'source', file_format='text')
    _require(received_file['failure'] is None and path is not None
        and received_file['input']['byte_verification'] == 'verified', 'alphafold_file_metadata_bytes_not_received')
    file = received_file['input']['file']
    raw = path.read_bytes()
    _require(file['artifact_ref'] == source['artifact_ref']
        and 'artifact_' + hashlib.sha256(raw).hexdigest() == source['artifact_ref']
        and len(raw) == file['size_bytes'], 'alphafold_file_artifact_identity_conflict')
    retained = _control(registry.store, source['request_ref'])
    _require(type(retained) is dict and set(retained) == {'request', 'transport'}
        and _same(retained['request'], original_arguments), 'alphafold_file_metadata_request_conflict')
    snapshot = SourceSnapshot(af.SERVICE, source['uri'], retained['request'], source['retrieved_at'], raw,
        registry.store.get(source['artifact_ref'])['media_type'], retained['transport'])
    actual = af.alphafold_prediction_result(snapshot, arguments=original_arguments,
        source_ref=source['id'], artifact_ref=source['artifact_ref'])
    _require(_same(actual, result), 'alphafold_file_metadata_result_conflict')
    selected = af.resolve_alphafold_file_selection(raw, arguments=arguments)
    selection = {'version': SELECTION_VERSION, 'arguments': arguments,
        'association': selected['association'], 'metadata_operation': operation}
    return _selection(registry, selection, arguments)[0]


def publish_alphafold_file(registry, arguments, snapshot, *, selection):
    selection, source, _ = _selection(registry, selection, arguments)
    arguments, association = selection['arguments'], selection['association']
    _require(isinstance(snapshot, SourceSnapshot) and snapshot.service == af.SERVICE
        and snapshot.url == association['advertised_url'] and _same(snapshot.request, arguments)
        and type(snapshot.content) is bytes and len(snapshot.content) <= arguments['max_bytes'],
        'alphafold_file_snapshot_conflict')
    # Validate the transport/selected-request join before publishing custody;
    # unknown response metadata is still retained as qualified unknown values.
    af._response(snapshot, arguments, association['advertised_url'], af.validate_alphafold_file_arguments)
    witness = registry.store.artifact(canonical(selection), 'application/json')
    acquired = registry._source(af.SERVICE, None, snapshot=snapshot, accession=None, software_version=None,
        parent_source_refs=[source['id']], auxiliary_artifact_refs=[witness])
    _require(acquired['version'] is None and acquired['accession'] is None, 'alphafold_file_source_invalid')
    result = af.alphafold_file_result(snapshot, arguments=arguments, association=association,
        source_ref=acquired['id'], artifact_ref=acquired['artifact_ref'])
    return result, [acquired['id'], acquired['artifact_ref']]


def publish_alphafold_prediction_receipt(registry, arguments, snapshot):
    """Retain native JSON and its source-free witness before publishing Source."""
    arguments = af.validate_alphafold_prediction_arguments(arguments)
    _require(isinstance(snapshot, SourceSnapshot) and type(snapshot.content) is bytes,
        'alphafold_snapshot_required')
    try:
        value = af.alphafold_prediction_value(snapshot, arguments=arguments,
            artifact_ref='artifact_' + hashlib.sha256(snapshot.content).hexdigest())
    except ValueError:
        value = None
    auxiliary = ([] if value is None else
        [registry.store.artifact(canonical(value), 'application/json')])
    source = registry._source(af.SERVICE, None, snapshot=snapshot,
        accession=arguments['identifier'] if value is not None else None,
        software_version=None, auxiliary_artifact_refs=auxiliary)
    receipt = (af.failed_alphafold_receipt('alphafold_request_conflict', source_ref=source['id'])
        if value is None else af.alphafold_prediction_receipt(value, source_ref=source['id']))
    return receipt, [source['id'], *([source['artifact_ref']] if receipt['acquired'] else [])]


def _file_receipt_from_controls(arguments, association, *, source_ref, file, uri, request, transport, service):
    """Confirm a captured transfer using metadata; never parse coordinate bytes."""
    if (service != af.SERVICE or uri != association['advertised_url'] or not _same(request, arguments)
            or file['byte_length'] > arguments['max_bytes'] or type(transport) is not dict
            or type(transport.get('request')) is not dict
            or transport['request'].get('method') != 'GET'
            or transport['request'].get('url') != association['advertised_url']):
        return af.failed_alphafold_receipt('alphafold_request_conflict', source_ref=source_ref)
    response, issues = af._response_metadata(transport, file['byte_length'], arguments['max_bytes'])
    result = af.validate_alphafold_file_result(dict(version='alphafold_file_result_v1',
        source_ref=source_ref, file=file, requested=arguments, response=response,
        association=association, observed_identity=dict(native_model_id=None, state='not_parsed'), issues=issues))
    return af.alphafold_file_receipt(result)


def publish_alphafold_file_receipt(registry, arguments, snapshot, *, selection):
    selection, metadata_source, _ = _selection(registry, selection, arguments)
    arguments, association = selection['arguments'], selection['association']
    _require(isinstance(snapshot, SourceSnapshot) and type(snapshot.content) is bytes
        and type(snapshot.service) is str, 'alphafold_snapshot_required')
    # Expected selection and observed service are separate retained facts. URI,
    # request and transport are retained literally by the ordinary Source owner.
    evidence = {'version': FILE_EVIDENCE_VERSION, 'selection': selection,
        'observed_snapshot_service': snapshot.service}
    witness = registry.store.artifact(canonical(evidence), 'application/json')
    source = registry._source(af.SERVICE, None, snapshot=snapshot, accession=None, software_version=None,
        parent_source_refs=[metadata_source['id']], auxiliary_artifact_refs=[witness])
    file = dict(artifact_ref=source['artifact_ref'], sha256=hashlib.sha256(snapshot.content).hexdigest(),
        byte_length=len(snapshot.content), format=arguments['file_format'])
    receipt = _file_receipt_from_controls(arguments, association, source_ref=source['id'], file=file,
        uri=snapshot.url, request=snapshot.request, transport=snapshot.transport, service=snapshot.service)
    return receipt, [source['id'], *([source['artifact_ref']] if receipt['acquired'] else [])]


def authenticate_saved_alphafold_file(registry, arguments, *, authority, outcome):
    arguments = af.validate_alphafold_file_arguments(arguments)
    context, reader = _authority(registry, authority)
    if type(outcome.get('result')) is dict and 'acquired' in outcome['result']:
        return _authenticate_saved_file_receipt(registry, arguments, context=context,
            reader=reader, outcome=outcome)
    result = af.validate_alphafold_file_result(outcome['result'])
    source = _source(registry.store, result['source_ref'])
    _, selected_arguments, original = _operation(registry, source['id'], FILE_TOOL)
    _require(_same(original, outcome) and _same(selected_arguments, arguments)
        and _same(result['requested'], arguments), 'alphafold_file_saved_outcome_conflict')
    received = reader(context, arguments['metadata_source_ref'], 'source', source_metadata_only=True)
    _require(received['failure'] is None and received['input'] is not None, 'alphafold_file_metadata_not_received')
    _require(source['accession'] is None and source['parent_source_refs'] == [arguments['metadata_source_ref']]
        and type(source.get('auxiliary_artifact_refs')) is list and len(source['auxiliary_artifact_refs']) == 1,
        'alphafold_file_saved_source_conflict')
    # Only genuine operation-owned Source controls are opened. In particular,
    # this path never reads the original metadata or coordinate entity bytes.
    selection = _control(registry.store, source['auxiliary_artifact_refs'][0])
    selection, _, _ = _selection(registry, selection, arguments)
    _require(_same(selection['association'], result['association'])
        and source['uri'] == selection['association']['advertised_url'], 'alphafold_file_saved_source_conflict')
    retained = _control(registry.store, source['request_ref'])
    _require(type(retained) is dict and set(retained) == {'request', 'transport'}
        and _same(retained['request'], arguments), 'alphafold_file_saved_request_conflict')
    transport = retained['transport']
    _require(type(transport) is dict and type(transport.get('request')) is dict
        and transport['request'].get('method') == 'GET' and transport['request'].get('url') == source['uri'],
        'alphafold_file_saved_request_conflict')
    file = result['file']
    metadata = _artifact_metadata(registry.store, source['artifact_ref'])
    _require(file['artifact_ref'] == source['artifact_ref'] and file['sha256'] == metadata['sha256']
        and file['byte_length'] == metadata['size'], 'alphafold_file_artifact_identity_conflict')
    _require(_same(result['response'], _saved_response(transport, metadata['size'])),
        'alphafold_file_saved_response_conflict')


def _authenticate_saved_file_receipt(registry, arguments, *, context, reader, outcome):
    receipt = af.validate_alphafold_receipt(outcome['result'])
    received = reader(context, arguments['metadata_source_ref'], 'source', source_metadata_only=True)
    _require(received['failure'] is None and received['input'] is not None,
        'alphafold_file_metadata_not_received')
    reference = receipt['source_ref']
    _, selected_arguments, original = _operation(registry, reference, FILE_TOOL, without_source=outcome)
    _require(_same(original, outcome) and _same(selected_arguments, arguments),
        'alphafold_file_saved_outcome_conflict')
    if reference is None:
        _require(not receipt['acquired'] and outcome['status'] in {'invalid', 'unavailable', 'failed'},
            'alphafold_file_saved_outcome_conflict')
        return
    source = _source(registry.store, reference)
    _require(source['accession'] is None and source['parent_source_refs'] == [arguments['metadata_source_ref']]
        and type(source.get('auxiliary_artifact_refs')) is list and len(source['auxiliary_artifact_refs']) == 1,
        'alphafold_file_saved_source_conflict')
    evidence = _control(registry.store, source['auxiliary_artifact_refs'][0])
    _require(type(evidence) is dict
        and set(evidence) == {'version', 'selection', 'observed_snapshot_service'}
        and evidence['version'] == FILE_EVIDENCE_VERSION
        and type(evidence['observed_snapshot_service']) is str, 'alphafold_file_saved_source_conflict')
    selection, _, _ = _selection(registry, evidence['selection'], arguments)
    retained = _control(registry.store, source['request_ref'])
    _require(type(retained) is dict and set(retained) == {'request', 'transport'},
        'alphafold_file_saved_request_conflict')
    metadata = _artifact_metadata(registry.store, source['artifact_ref'])
    file = dict(artifact_ref=source['artifact_ref'], sha256=metadata['sha256'],
        byte_length=metadata['size'], format=arguments['file_format'])
    actual = _file_receipt_from_controls(arguments, selection['association'], source_ref=reference, file=file,
        uri=source['uri'], request=retained['request'], transport=retained['transport'],
        service=evidence['observed_snapshot_service'])
    _require(_same(actual, receipt)
        and outcome['record_refs'] == [reference, *([source['artifact_ref']] if receipt['acquired'] else [])],
        'alphafold_file_saved_outcome_conflict')


__all__ = ['prepare_alphafold_file', 'publish_alphafold_file', 'authenticate_saved_alphafold_file',
    'publish_alphafold_prediction_receipt', 'publish_alphafold_file_receipt']
