from __future__ import annotations
from copy import deepcopy
from datetime import datetime
import hashlib
import re
from gene_annotation_episode.episodic_workflow.root.a110.acquisition import SourceSnapshot
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_analysis_protocol import parse_workspace_records
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_appservice_contracts import ContractValidationError, _Validator, _finite_json, _same, contract_schema, download_request, validate_contract

def _diagnostic(code, path='', *, phase='native_decode', severity='error', refs=()):
    return {'code': code, 'phase': phase, 'path': path, 'severity': severity, 'evidence_refs': list(dict.fromkeys(refs))}

def _check_json(value):
    try:
        _finite_json(value)
    except RecursionError as error:
        raise ContractValidationError('json_nesting_too_deep') from error
    return deepcopy(value)

def _status(diagnostics, *, valid=False):
    return 'ok' if not any((d['severity'] == 'error' for d in diagnostics)) else 'partial' if valid else 'invalid'

def _capability(value):
    """Validate the exact inline CapabilityReceipt.entries member contract."""
    value = _check_json(value)
    parent = contract_schema('CapabilityReceipt')
    entry_schema = parent['$defs']['CapabilityReceipt']['properties']['entries']['items']
    schema = {**entry_schema, '$defs': parent['$defs']}
    if not _Validator(schema).is_valid(value):
        raise ContractValidationError('capability_entry_invalid')
    validate_contract('WorkspaceObject', value['object'])
    validate_contract('TaskAssociation', value['task_association'])
    association = value['task_association']
    for field, associated in (('path', 'output_path'), ('uuid', 'output_uuid')):
        if association[associated] is not None and value['object'][field] != association[associated]:
            raise ContractValidationError('output_association_' + field + '_conflict')
    if (value['expires_at'] is None) != (value['expiry_evidence'] is None):
        raise ContractValidationError('capability_expiry_evidence_conflict')
    return value

def _object_binding(value):
    if type(value) is not dict or set(value) != {'object', 'metadata'}:
        raise ContractValidationError('download_object_binding_invalid')
    obj = validate_contract('WorkspaceObject', value['object'])
    metadata = value['metadata']
    if metadata is None:
        return (obj, None)
    metadata = validate_contract('WorkspaceRow', metadata)
    if not metadata['valid']:
        raise ContractValidationError('download_metadata_invalid')
    for key in ('path', 'uuid', 'type'):
        if metadata[key] != obj[key]:
            raise ContractValidationError('download_metadata_identity_conflict')
    raw = metadata['native_row']
    operation = 'get' if type(raw) is list and len(raw) in (1, 2) and (type(raw[0]) is list) else 'create'
    parsed = parse_workspace_records([raw], operation=operation, requested_paths=[obj['path']])
    if parsed['status'] != 'ok' or len(parsed['records']) != 1:
        raise ContractValidationError('download_metadata_native_invalid')
    row = parsed['records'][0]
    for field, native_field in (('path', 'object_path'), ('uuid', 'object_id'), ('type', 'type'), ('size', 'size'), ('shock_url', 'shock_url'), ('creation_time', 'creation_time'), ('error', 'error')):
        actual = row[native_field]
        if field == 'shock_url' and actual == '':
            actual = None
        if not _same(metadata[field], actual):
            raise ContractValidationError('download_metadata_native_conflict')
    return (obj, metadata)

def _headers(transport, diagnostics):
    headers = transport.get('headers')
    if type(headers) is not dict or any((type(k) is not str or type(v) is not str for k, v in headers.items())):
        raise ContractValidationError('download_headers_invalid')
    lowered = {key.lower(): value for key, value in headers.items()}
    if 'header_items' in transport:
        items = transport['header_items']
        if type(items) is not list or any((type(x) is not list or len(x) != 2 or any((type(y) is not str for y in x)) for x in items)):
            raise ContractValidationError('download_header_items_invalid')
        seen = {}
        for key, value in items:
            key = key.lower()
            if key in seen and seen[key] != value and (key in {'content-length', 'content-range', 'content-encoding', 'transfer-encoding'}):
                diagnostics.append(_diagnostic('conflicting_http_header', '/transport/header_items', phase='transport'))
            seen[key] = value
        for key, value in seen.items():
            if lowered.get(key) != value:
                diagnostics.append(_diagnostic('http_header_projection_conflict', '/transport/headers', phase='transport'))
    return lowered

def _bounded_capture(request, transport, byte_count, headers):
    """Check local cap evidence without inferring an unseen body or object."""
    complete, diagnostics = (transport['body_complete'], [])
    if 'max_bytes' not in request:
        return (complete, diagnostics)
    limit = request['max_bytes']
    conflicts = []
    observed = transport.get('observed_body_bytes')
    if type(transport.get('response_byte_limit')) is not int or transport['response_byte_limit'] != limit:
        conflicts.append('response_byte_limit')
    if type(transport.get('retained_body_bytes')) is not int or transport['retained_body_bytes'] != byte_count:
        conflicts.append('retained_body_bytes')
    if type(transport.get('received_body_bytes')) is not int or transport['received_body_bytes'] != byte_count:
        conflicts.append('received_body_bytes')
    if type(observed) is not int or observed < 0 or byte_count != min(observed, limit):
        conflicts.append('observed_body_bytes')
    declared = None
    text = headers.get('content-length')
    if type(text) is str and re.fullmatch('[0-9]+', text) and (headers.get('transfer-encoding') is None):
        declared = int(text)
    supplied = transport.get('declared_body_bytes')
    if supplied is not None and type(supplied) is not int or not _same(supplied, declared):
        conflicts.append('declared_body_bytes')
    failure = transport.get('body_capture_failure')
    if failure is not None and type(failure) is not str:
        conflicts.append('body_capture_failure')
    if complete and (observed != byte_count or failure is not None):
        conflicts.append('body_complete')
    exceeded = byte_count > limit or (type(observed) is int and observed > limit) or failure == 'provider_response_byte_limit'
    if exceeded:
        diagnostics.append(_diagnostic('download_byte_limit_exceeded', phase='transport'))
    diagnostics.extend((_diagnostic('download_capture_limit_conflict', '/transport/' + key, phase='transport') for key in conflicts))
    return (complete and (not exceeded) and (not conflicts), diagnostics)

def qualify_download(snapshot, *, capability: dict, object_binding: dict) -> dict:
    """Qualify one already-acquired body; no requests, assembly, or truncation.

    capability is one exact CapabilityReceipt.entries member. object_binding is
    {object: WorkspaceObject, metadata: WorkspaceRow | None}. Null metadata does
    not supply a size. Request range comes only from snapshot.request. A 200 body
    without a declared length or supplied object size has unknown object
    completeness, including the source proxy's premature-success case.
    """
    capability = _capability(capability)
    obj, metadata = _object_binding(object_binding)
    if not _same(capability['object'], obj):
        raise ContractValidationError('capability_object_conflict')
    if not isinstance(snapshot, SourceSnapshot) or type(snapshot.content) is not bytes:
        raise ContractValidationError('download_snapshot_invalid')
    request, transport = (_check_json(snapshot.request), _check_json(snapshot.transport))
    if type(request) is not dict or request.get('kind') != 'download' or 'requested_byte_range' not in request:
        raise ContractValidationError('download_request_invalid')
    call = {'url': request.get('url'), 'byte_range': request['requested_byte_range']}
    if 'max_bytes' in request:
        call['max_bytes'] = request['max_bytes']
    if not _same(request, download_request(call)):
        raise ContractValidationError('download_request_invalid')
    selected_range = request['requested_byte_range']
    if selected_range is not None:
        selected_range = validate_contract('Range', selected_range)
    diagnostics = []
    if capability['url'] is None:
        diagnostics.append(_diagnostic('capability_unavailable', phase='association'))
    if request.get('url') != capability['url'] or snapshot.url != capability['url']:
        diagnostics.append(_diagnostic('capability_url_conflict', phase='association'))
    if type(transport) is not dict or type(transport.get('body_complete')) is not bool:
        raise ContractValidationError('download_transport_invalid')
    http_status = transport.get('status')
    if type(http_status) is not int or not 100 <= http_status <= 599:
        raise ContractValidationError('download_http_status_invalid')
    if transport.get('effective_url') != snapshot.url or transport.get('automatic_redirects') is not False:
        diagnostics.append(_diagnostic('download_transport_identity_conflict', phase='transport'))
    if 'request' in transport and (type(transport['request']) is not dict or transport['request'].get('method') != 'GET' or transport['request'].get('url') != snapshot.url):
        diagnostics.append(_diagnostic('download_transport_request_conflict', phase='transport'))
    byte_count = len(snapshot.content)
    if type(transport.get('received_body_bytes')) is not int or transport['received_body_bytes'] != byte_count:
        diagnostics.append(_diagnostic('download_body_count_conflict', phase='transport'))
    headers = _headers(transport, diagnostics)
    body_complete, capture_diagnostics = _bounded_capture(request, transport, byte_count, headers)
    diagnostics.extend(capture_diagnostics)
    content_length = None
    if 'content-length' in headers:
        if re.fullmatch('[0-9]+', headers['content-length'].strip()) is None:
            diagnostics.append(_diagnostic('content_length_invalid', '/transport/headers/content-length', phase='transport'))
        else:
            content_length = int(headers['content-length'].strip())
            if content_length != byte_count:
                body_complete = False
                diagnostics.append(_diagnostic('download_incomplete' if byte_count < content_length else 'object_size_conflict', '/transport/headers/content-length', phase='transport'))
    if headers.get('transfer-encoding') and content_length is not None:
        diagnostics.append(_diagnostic('conflicting_http_framing', '/transport/headers', phase='transport'))
    observed = None
    content_range = headers.get('content-range')
    if http_status == 206:
        match = re.fullmatch('bytes ([0-9]+)-([0-9]+)/(\\*|[0-9]+)', content_range or '')
        if match is None:
            diagnostics.append(_diagnostic('range_conflict', '/transport/headers/content-range', phase='transport'))
        else:
            candidate = {'start': int(match[1]), 'end_inclusive': int(match[2]), 'total_size': None if match[3] == '*' else int(match[3])}
            try:
                observed = validate_contract('ObservedRange', candidate)
            except ContractValidationError:
                diagnostics.append(_diagnostic('range_conflict', '/transport/headers/content-range', phase='transport'))
    elif http_status == 200:
        if content_range is not None:
            diagnostics.append(_diagnostic('range_conflict', '/transport/headers/content-range', phase='transport'))
        if selected_range is not None:
            diagnostics.append(_diagnostic('range_ignored', '/request/requested_byte_range', phase='transport', severity='qualification'))
    else:
        diagnostics.append(_diagnostic('capability_http_error', '/transport/status', phase='transport'))
    metadata_size = metadata['size'] if metadata is not None and obj['type'] != 'folder' else None
    total_size = observed['total_size'] if observed is not None else content_length if http_status == 200 else None
    if metadata_size is not None:
        if total_size is not None and metadata_size != total_size:
            diagnostics.append(_diagnostic('object_size_conflict', phase='association'))
        if total_size is None:
            total_size = metadata_size
    if observed is not None:
        width = observed['end_inclusive'] - observed['start'] + 1
        if byte_count != width:
            body_complete = False
            diagnostics.append(_diagnostic('download_incomplete' if byte_count < width else 'range_conflict', phase='transport'))
        if total_size is not None and observed['end_inclusive'] >= total_size:
            diagnostics.append(_diagnostic('object_size_conflict', phase='association'))
        if selected_range is not None:
            start, end = selected_range
            expected_end = min(end, total_size - 1) if end is not None and total_size is not None else end if end is not None else total_size - 1 if total_size is not None else None
            if observed['start'] != start or (expected_end is not None and observed['end_inclusive'] != expected_end):
                diagnostics.append(_diagnostic('range_conflict', '/request/requested_byte_range', phase='transport'))
    elif http_status == 200 and total_size is not None and (byte_count != total_size):
        diagnostics.append(_diagnostic('object_size_conflict', phase='association'))
    if not body_complete and (not any((d['code'] == 'download_incomplete' for d in diagnostics))):
        diagnostics.append(_diagnostic('download_incomplete', phase='transport'))
    encoded = headers.get('content-encoding', 'identity').lower() != 'identity'
    if encoded:
        diagnostics.append(_diagnostic('content_encoding_uninterpreted', '/transport/headers/content-encoding', phase='transport', severity='qualification'))
    if capability['expires_at'] is not None:
        try:
            expires, retrieved = (datetime.fromisoformat(x.replace('Z', '+00:00')) for x in (capability['expires_at'], snapshot.retrieved_at))
            if expires.tzinfo is None or retrieved.tzinfo is None:
                raise ValueError('unqualified_time')
            if retrieved >= expires:
                diagnostics.append(_diagnostic('capability_expired_at_retrieval', phase='association', severity='qualification'))
        except (TypeError, ValueError):
            diagnostics.append(_diagnostic('capability_expiry_time_uninterpretable', phase='association', severity='qualification'))
    errors = any((d['severity'] == 'error' for d in diagnostics))
    if not body_complete:
        object_complete = 'no'
    elif errors or encoded or total_size is None:
        object_complete = 'unknown'
    elif observed is not None:
        object_complete = 'yes' if observed['start'] == 0 and observed['end_inclusive'] + 1 == total_size else 'no'
    else:
        object_complete = 'yes' if http_status == 200 and byte_count == total_size else 'unknown'
    if object_complete == 'unknown':
        diagnostics.append(_diagnostic('object_completeness_unproven', phase='association', severity='qualification'))
    received_range = None
    if observed is not None and byte_count and (byte_count <= observed['end_inclusive'] - observed['start'] + 1):
        received_range = {'start': observed['start'], 'end_inclusive': observed['start'] + byte_count - 1, 'total_size': total_size}
    value = {'body_complete': body_complete, 'requested_range': deepcopy(selected_range), 'observed_range': observed, 'received_range': received_range, 'total_size': total_size, 'metadata_size': metadata_size, 'object_complete': object_complete, 'byte_count': byte_count, 'sha256': hashlib.sha256(snapshot.content).hexdigest()}
    parsed_status = 'failed' if http_status not in (200, 206) else _status(diagnostics, valid=bool(snapshot.content))
    return {'status': parsed_status, 'native': {'request': request, 'transport': transport}, 'value': value, 'diagnostics': diagnostics}

def validate_bundle(value: dict) -> dict:
    """Check a supplied bundle's shape/relationships, without resolving custody."""
    return validate_contract('ArtifactBundle', value)
