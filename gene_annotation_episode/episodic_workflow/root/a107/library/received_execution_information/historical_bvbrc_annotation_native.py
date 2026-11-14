"""Pure observations from a selected BV-BRC genome-annotation artifact.

The AppService host authenticates the task, response, ContentBinding and actual
bytes before this reader is called. A self-consistent descriptor here is not
custody. The reversible JSON document preserves native members, number tokens,
occurrences and unknown fields. This is not a gene caller or an annotation
confidence model. In particular, GTO features are never recast as Prodigal calls.

GTO locations are ordered [contig, begin, strand, length] tuples. Begin is
one-based and directional; checked intervals below are zero-based half-open.
Native viral producers can serialize begin as a digit string. Split and
multicontig locations remain separate, in their original order. Quality and
analysis-event fields remain native observations with no universal score or
truncation interpretation.
"""
from __future__ import annotations
from copy import deepcopy
import json
import math
import re
from gene_annotation_episode.episodic_workflow.root.a107.ucsc_acquisition import _analyse, _from_document
DOCUMENT_VERSION = 'bvbrc_annotation_native_document_v1'
COMPONENTS_VERSION = 'bvbrc_annotation_components_v1'
MAX_NATIVE_DEPTH = 32
REPRESENTATIONS = ('gto', 'quality_json')
_CONTENT_KEYS = {'source_ref', 'artifact_field', 'artifact_ref', 'sha256', 'byte_count'}
_DOCUMENT_KEYS = {'version', 'representation', 'content', 'expected_task_id', 'capture_complete', 'parsing_state', 'native_document', 'identity', 'records', 'issues'}

def _require(condition, code='bvbrc_annotation_document_invalid'):
    if not condition:
        raise ValueError(code)

def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')

def _finite_json(value, active=None):
    active = set() if active is None else active
    kind = type(value)
    if value is None or kind in {bool, int}:
        return
    if kind is str:
        value.encode('utf-8')
        return
    if kind is float:
        _require(math.isfinite(value))
        return
    _require(kind in {dict, list} and id(value) not in active)
    active.add(id(value))
    try:
        if kind is dict:
            _require(all((type(key) is str for key in value)))
            for key, item in value.items():
                key.encode('utf-8')
                _finite_json(item, active)
        else:
            for item in value:
                _finite_json(item, active)
    finally:
        active.remove(id(value))

def _issue(code, path, *, severity='qualification'):
    return {'code': code, 'path': path, 'severity': severity}

def _members(node, name):
    if type(node) is not dict or node.get('kind') != 'object':
        return []
    return [(index, item['value']) for index, item in enumerate(node['members']) if item['name'] == name]

def _field(node, name, path):
    matches = _members(node, name)
    if not matches:
        return {'state': 'missing', 'path': None, 'value': None}
    if len(matches) != 1:
        return {'state': 'ambiguous', 'path': path, 'value': None}
    index, value = matches[0]
    return {'state': 'null' if value['kind'] == 'null' else 'present', 'path': path + '/members/' + str(index) + '/value', 'value': value}

def _text(field):
    value = field['value']
    return value['value'] if field['state'] == 'present' and value['kind'] == 'string' else None

def _integer(node):
    if type(node) is not dict:
        return None
    kind = node.get('kind')
    token = node.get('token') if kind == 'number' else node.get('value') if node.get('kind') == 'string' else None
    grammar = '0|[1-9][0-9]*' if kind == 'number' else '[0-9]+'
    if type(token) is not str or re.fullmatch(grammar, token, re.ASCII) is None:
        return None
    significant = token.lstrip('0') or '0'
    return int(significant) if len(significant) <= 20 else None

def _validate_native(node, depth=0):
    _require(type(node) is dict and depth <= MAX_NATIVE_DEPTH)
    kind = node.get('kind')
    if kind == 'object':
        _require(set(node) == {'kind', 'members'} and type(node['members']) is list)
        for member in node['members']:
            _require(type(member) is dict and set(member) == {'name', 'value'} and (type(member['name']) is str))
            member['name'].encode('utf-8')
            _validate_native(member['value'], depth + 1)
    elif kind == 'array':
        _require(set(node) == {'kind', 'items'} and type(node['items']) is list)
        for child in node['items']:
            _validate_native(child, depth + 1)
    elif kind == 'number':
        _require(set(node) == {'kind', 'token'} and type(node['token']) is str and (re.fullmatch('-?(?:0|[1-9][0-9]*)(?:\\.[0-9]+)?(?:[eE][+-]?[0-9]+)?', node['token'], re.ASCII) is not None))
    else:
        _require(set(node) == {'kind', 'value'})
        value = node['value']
        _require(kind == 'string' and type(value) is str or (kind == 'boolean' and type(value) is bool) or (kind == 'null' and value is None))
        if kind == 'string':
            value.encode('utf-8')

def _content(value):
    _require(type(value) is dict and set(value) == _CONTENT_KEYS, 'bvbrc_annotation_content_invalid')
    _require(type(value['source_ref']) is str and re.fullmatch('source_[a-f0-9]{24,64}', value['source_ref']) is not None and (value['artifact_field'] == 'artifact_ref') and (type(value['sha256']) is str) and (re.fullmatch('[a-f0-9]{64}', value['sha256']) is not None) and (value['artifact_ref'] == 'artifact_' + value['sha256']) and (type(value['byte_count']) is int) and (value['byte_count'] >= 0), 'bvbrc_annotation_content_invalid')
    return deepcopy(value)

def _records(document, name, issues):
    selected = _field(document, name, '/native_document')
    state, value = (selected['state'], selected['value'])
    if state == 'present' and value['kind'] != 'array':
        state = 'invalid'
    if state != 'present':
        issues.append(_issue('native_' + name + '_' + state, selected['path'] or '/native_document'))
        return {'state': state, 'path': selected['path'], 'rows': None}
    rows = []
    for ordinal, native in enumerate(value['items']):
        path = selected['path'] + '/items/' + str(ordinal)
        identifier = _field(native, 'id', path)
        text = _text(identifier)
        if native['kind'] != 'object':
            issues.append(_issue('native_' + name + '_record_invalid', path))
        elif text is None or not text:
            issues.append(_issue('native_' + name + '_identity_unavailable', path))
        rows.append({'ordinal': ordinal, 'path': path, 'id': text, 'identity_state': 'available' if text else identifier['state'] if identifier['state'] != 'present' else 'invalid', 'native_record': deepcopy(native)})
    occurrences = {}
    for row in rows:
        if row['id']:
            occurrences.setdefault(row['id'], []).append(row)
    for duplicates in occurrences.values():
        if len(duplicates) > 1:
            for row in duplicates:
                row['identity_state'] = 'ambiguous'
                issues.append(_issue('native_' + name + '_identity_duplicate', row['path']))
    return {'state': 'present', 'path': selected['path'], 'rows': rows}

def _location_rows(feature, contig_index, issues):
    location = _field(feature['native_record'], 'location', feature['path'])
    state, node = (location['state'], location['value'])
    if state == 'present' and node['kind'] != 'array':
        state = 'invalid'
    if state != 'present':
        issues.append(_issue('native_feature_location_' + state, location['path'] or feature['path']))
        return {'state': state, 'rows': None}
    if not node['items']:
        issues.append(_issue('native_feature_location_empty', location['path']))
    rows = []
    for ordinal, native in enumerate(node['items']):
        path = location['path'] + '/items/' + str(ordinal)
        row = {'ordinal': ordinal, 'path': path, 'native_location': deepcopy(native), 'state': 'invalid', 'contig_ordinal': None, 'contig_id': None, 'begin': None, 'strand': None, 'length': None, 'interval': None}
        cells = native['items'] if native['kind'] == 'array' else []
        if len(cells) == 4:
            contig_id = cells[0]['value'] if cells[0]['kind'] == 'string' else None
            strand = cells[2]['value'] if cells[2]['kind'] == 'string' else None
            begin, length = (_integer(cells[1]), _integer(cells[3]))
            row.update(contig_id=contig_id, begin=begin, strand=strand, length=length)
            if contig_id and begin is not None and (begin > 0) and (length is not None) and (length > 0) and (strand in {'+', '-'}):
                matches = contig_index.get(contig_id, [])
                if len(matches) != 1:
                    row['state'] = 'ambiguous_contig' if matches else 'missing_contig'
                else:
                    contig = matches[0]
                    dna = _text(_field(contig['native_record'], 'dna', contig['path']))
                    if dna is None:
                        row['state'] = 'contig_sequence_unavailable'
                    else:
                        start = begin - 1 if strand == '+' else begin - length
                        end = begin + length - 1 if strand == '+' else begin
                        if 0 <= start < end <= len(dna):
                            row.update(state='available', contig_ordinal=contig['ordinal'], interval=[start, end])
                        else:
                            row['state'] = 'outside_contig'
        if row['state'] != 'available':
            issues.append(_issue('native_feature_location_' + row['state'], path))
        rows.append(row)
    return {'state': 'present', 'rows': rows}

def _qualified(document, *, representation, capture_complete, expected_task_id):
    issues = []
    identity = {'state': 'unavailable', 'observed_task_id': None}
    records = {name: {'state': 'unavailable', 'path': None, 'rows': None} for name in ('contigs', 'features', 'analysis_events')}
    if not capture_complete:
        issues.append(_issue('native_capture_incomplete', '/capture_complete'))
    if document is None:
        return (identity, records, issues)
    if document['kind'] != 'object':
        issues.append(_issue('native_object_required', '/native_document', severity='error'))
        return (identity, records, issues)
    if representation == 'quality_json':
        issues.append(_issue('native_quality_units_and_method_not_inferred', '/native_document'))
        return (identity, records, issues)
    records = {name: _records(document, name, issues) for name in records}
    contig_index = {}
    for contig in records['contigs']['rows'] or []:
        if contig['id']:
            contig_index.setdefault(contig['id'], []).append(contig)
    for feature in records['features']['rows'] or []:
        feature['location'] = _location_rows(feature, contig_index, issues)
    for event in records['analysis_events']['rows'] or []:
        success = _field(event['native_record'], 'success', event['path'])
        observed = success['value']
        event['success_state'] = success['state']
        if success['state'] == 'present':
            if observed['kind'] == 'number' and observed['token'] in {'0', '1'}:
                event['success_state'] = 'reported_failure' if observed['token'] == '0' else 'reported_success'
            else:
                event['success_state'] = 'unavailable'
        if event['success_state'] == 'reported_failure':
            issues.append(_issue('native_analysis_reported_failure', success['path']))
    metadata = _field(document, 'job_metadata', '/native_document')
    if metadata['state'] == 'present' and metadata['value']['kind'] == 'object':
        task = _field(metadata['value'], 'task_id', metadata['path'])
        observed = _text(task)
        identity['observed_task_id'] = observed
        if observed and observed != 'unknown':
            identity['state'] = 'matched' if observed == expected_task_id else 'conflict'
        elif task['state'] == 'ambiguous':
            identity['state'] = 'ambiguous'
    if identity['state'] != 'matched':
        issues.append(_issue('native_task_identity_' + identity['state'], '/native_document', severity='error' if identity['state'] == 'conflict' else 'qualification'))
    return (identity, records, issues)

def validate_annotation_document(value):
    """Validate a retained parsed document without raw bytes, I/O or JSON parsing."""
    try:
        _finite_json(value)
    except (RecursionError, UnicodeError) as error:
        raise ValueError('bvbrc_annotation_document_invalid') from error
    _require(type(value) is dict and set(value) == _DOCUMENT_KEYS and (value['version'] == DOCUMENT_VERSION) and (type(value['representation']) is str) and (value['representation'] in REPRESENTATIONS) and (type(value['capture_complete']) is bool) and (type(value['expected_task_id']) is str) and bool(value['expected_task_id']) and (type(value['parsing_state']) is str) and (value['parsing_state'] in {'available', 'unavailable'}) and (type(value['issues']) is list))
    _content(value['content'])
    document = value['native_document']
    _require((document is None) == (value['parsing_state'] == 'unavailable'))
    if document is not None:
        _validate_native(document)
    identity, records, issues = _qualified(document, representation=value['representation'], capture_complete=value['capture_complete'], expected_task_id=value['expected_task_id'])
    _require(_canonical(identity) == _canonical(value['identity']) and _canonical(records) == _canonical(value['records']))
    for issue in value['issues']:
        _require(type(issue) is dict and set(issue) == {'code', 'path', 'severity'} and (type(issue['code']) is str) and bool(issue['code']) and (type(issue['path']) is str) and issue['path'].startswith('/') and (type(issue['severity']) is str) and (issue['severity'] in {'error', 'qualification'}))
    _require(all((issue in value['issues'] for issue in issues)))
    if document is not None:
        _, canonical_document, lexical, _ = _analyse(_from_document(document))
        _require(_canonical(canonical_document) == _canonical(document))
        expected_issues = [*[_issue(item['code'], item['pointer']) for item in lexical], *issues]
        _require(_canonical(value['issues']) == _canonical(expected_issues))
    else:
        failures = [issue for issue in value['issues'] if issue not in issues]
        _require(bool(failures) and failures[-1]['code'] in {'invalid_native_utf8', 'invalid_native_json', 'invalid_native_unicode', 'native_document_depth_or_shape_invalid'} and (failures[-1]['path'] == '/native_document') and (failures[-1]['severity'] == 'error') and all((issue['code'] in {'native_duplicate_member', 'native_number_token_required'} and issue['path'].startswith('/native_document') and (issue['severity'] == 'qualification') for issue in failures[:-1])) and (_canonical(value['issues']) == _canonical([*failures, *issues])))
    return deepcopy(value)
