"""Lossless, Store-free VCF 4.2 observations and selected population accounting.

This module reads supplied bytes, not paths or Sources.  File descriptors and
Source associations are supplied witnesses; they do not establish permission.
Every data slot, including a malformed one, keeps its original ordinal.  The
calculator selects retained observations; it performs no variant calling,
allele-frequency estimation, event reconstruction or biological classification.
"""
from __future__ import annotations
import base64
import binascii
import hashlib
import json
import math
import re
from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.alignment_correspondence import _copy, _ratio
from gene_annotation_episode.episodic_workflow.root.a106.domain import ContractError, validate_schema
SHEET_VERSION = 'vcf_result_sheet_v1'
SELECTION_VERSION = 'vcf_result_selection_v1'
COMPONENTS_VERSION = 'vcf_result_components_v1'
VALUE_VERSION = 'vcf_result_values_v1'
RETURN_VERSION = 'vcf_result_return_v1'
_FIXED = ('chrom', 'pos', 'id', 'ref', 'alt', 'qual', 'filter', 'info')
_HEADER = ('#CHROM', 'POS', 'ID', 'REF', 'ALT', 'QUAL', 'FILTER', 'INFO')
_SHA = re.compile('[0-9a-f]{64}\\Z')
_SOURCE = re.compile('source_[0-9a-f]{24,64}\\Z')
_INT = re.compile('[+-]?[0-9]+\\Z')
_FLOAT = re.compile('[+-]?(?:[0-9]+(?:\\.[0-9]*)?|\\.[0-9]+)(?:[eE][+-]?[0-9]+)?\\Z')
_INPUT_KEYS = {'input_id', 'retained_file', 'original_file', 'source_ref', 'capture'}

def _need(condition, code):
    if not condition:
        raise ValueError('vcf_result_' + code)

def _closed(value, keys):
    _need(type(value) is dict and set(value) == set(keys), 'shape_invalid')

def _text(value, *, nullable=False, empty=False):
    _need(nullable and value is None or (type(value) is str and (empty or bool(value))), 'text_invalid')

def _integer(value, *, nullable=False, minimum=0):
    _need(nullable and value is None or (type(value) is int and value >= minimum), 'integer_invalid')

def _digest(value, *, nullable=False):
    _need(nullable and value is None or (type(value) is str and _SHA.fullmatch(value) is not None), 'digest_invalid')

def _same(left, right):
    return json.dumps(left, sort_keys=True, separators=(',', ':'), allow_nan=False) == json.dumps(right, sort_keys=True, separators=(',', ':'), allow_nan=False)

def _issues(values):
    _need(type(values) is list, 'issues_invalid')
    for value in values:
        _closed(value, ('code', 'phase', 'path', 'severity', 'evidence_refs'))
        _text(value['code'])
        _need(value['phase'] == 'native_decode' and value['severity'] in ('qualification', 'error'), 'issue_invalid')
        _need(type(value['path']) is str and (not value['path'] or value['path'].startswith('/')), 'issue_invalid')
        _need(value['evidence_refs'] == [], 'issue_invalid')

def _file(value):
    if value is None:
        return
    _closed(value, ('artifact_ref', 'sha256', 'size_bytes', 'format'))
    _text(value['artifact_ref'])
    _digest(value['sha256'])
    _need(value['artifact_ref'] == 'artifact_' + value['sha256'], 'file_identity_conflict')
    _integer(value['size_bytes'])
    _text(value['format'])

def _input(value, retained_size):
    _closed(value, _INPUT_KEYS)
    _text(value['input_id'])
    _text(value['source_ref'], nullable=True)
    _need(value['source_ref'] is None or _SOURCE.fullmatch(value['source_ref']) is not None, 'source_reference_invalid')
    _file(value['retained_file'])
    _file(value['original_file'])
    cap = value['capture']
    _closed(cap, ('state', 'byte_start_0based', 'byte_end_0based_exclusive', 'original_size_bytes'))
    _need(cap['state'] in ('complete', 'truncated', 'missing', 'unknown'), 'capture_invalid')
    _need(type(cap['byte_start_0based']) is int and cap['byte_start_0based'] == 0, 'capture_invalid')
    _integer(cap['byte_end_0based_exclusive'])
    _integer(cap['original_size_bytes'], nullable=True)
    _need(cap['byte_end_0based_exclusive'] == retained_size, 'capture_size_conflict')
    original_size = cap['original_size_bytes']
    _need(original_size is None or original_size >= retained_size, 'capture_size_conflict')
    if cap['state'] == 'missing':
        _need(retained_size == 0, 'missing_capture_has_bytes')
    if cap['state'] == 'complete':
        _need(original_size in (None, retained_size), 'capture_size_conflict')
        if value['original_file'] is not None and value['retained_file'] is not None:
            _need(_same(value['original_file'], value['retained_file']), 'complete_file_identity_conflict')
    if value['original_file'] is not None and original_size is not None:
        _need(value['original_file']['size_bytes'] == original_size, 'original_size_conflict')
    if value['original_file'] is not None:
        _need(value['original_file']['size_bytes'] >= retained_size, 'original_size_conflict')

def _raw(value):
    if value is None:
        return None
    _closed(value, ('encoding', 'data', 'sha256', 'size_bytes'))
    _need(value['encoding'] == 'base64' and type(value['data']) is str, 'raw_encoding_invalid')
    try:
        raw = base64.b64decode(value['data'], validate=True)
    except (ValueError, binascii.Error) as error:
        raise ValueError('vcf_result_raw_encoding_invalid') from error
    _need(base64.b64encode(raw).decode('ascii') == value['data'], 'raw_encoding_invalid')
    _digest(value['sha256'])
    _integer(value['size_bytes'])
    _need(len(raw) == value['size_bytes'] and hashlib.sha256(raw).hexdigest() == value['sha256'], 'raw_identity_conflict')
    return raw

def _number(token, kind):
    text = token['raw_token']
    if text == '.':
        return {'kind': 'missing', 'value': None}
    if text is None:
        return {'kind': 'undecodable', 'value': None}
    if kind == 'Integer':
        if not _INT.fullmatch(text):
            return {'kind': 'malformed', 'value': None}
        try:
            return {'kind': 'Integer', 'value': int(text)}
        except ValueError:
            return {'kind': 'overflow', 'value': None}
    if kind == 'Float':
        if text.lower().lstrip('+-') in ('nan', 'inf', 'infinity'):
            return {'kind': 'nonfinite', 'value': None}
        if not _FLOAT.fullmatch(text):
            return {'kind': 'malformed', 'value': None}
        value = float(text)
        if not math.isfinite(value):
            return {'kind': 'overflow', 'value': None}
        mantissa = re.split('[eE]', text)[0]
        if value == 0 and any((char in '123456789' for char in mantissa)):
            return {'kind': 'underflow', 'value': None}
        return {'kind': 'Float', 'value': value}
    if kind == 'Character':
        return {'kind': 'Character', 'value': text} if len(text) == 1 else {'kind': 'malformed', 'value': None}
    if kind == 'String':
        return {'kind': 'String', 'value': text}
    return {'kind': 'unknown', 'value': None}

def _definition(definitions, namespace, key):
    return [d for d in definitions if d['namespace'] == namespace and d['id'] == key]

def _genotype_labels(allele_count, ploidy, observed):
    """Label the explicit haploid/diploid order; other ploidies stay indexed."""
    if ploidy == 1:
        return [[index] for index in range(min(allele_count, observed))]
    if ploidy == 2:
        result = []
        for second in range(allele_count):
            for first in range(second + 1):
                if len(result) == observed:
                    return result
                result.append([first, second])
        return result
    return []

def _schemas():
    """One finite structural schema map; runtime validators add supplied joins."""
    text = {'type': 'string'}
    nullable_text = {'type': ['string', 'null']}
    integer = {'type': 'integer', 'minimum': 0}
    nullable_integer = {'type': ['integer', 'null'], 'minimum': 0}
    digest = {'type': 'string', 'pattern': '^[0-9a-f]{64}$'}
    ref = lambda name: {'$ref': '#/$defs/' + name}
    array = lambda item: {'type': 'array', 'items': item}
    nullable = lambda item: {'anyOf': [item, {'type': 'null'}]}

    def obj(properties):
        return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}

    def tag(version, properties):
        return obj({'version': {'const': version}, **properties})
    definitions = {}
    definitions['File'] = obj({'artifact_ref': {'type': 'string', 'pattern': '^artifact_[0-9a-f]{64}$'}, 'sha256': digest, 'size_bytes': integer, 'format': {'type': 'string', 'minLength': 1}})
    definitions['Capture'] = obj({'state': {'enum': ['complete', 'truncated', 'missing', 'unknown']}, 'byte_start_0based': {'const': 0}, 'byte_end_0based_exclusive': integer, 'original_size_bytes': nullable_integer})
    definitions['Input'] = obj({'input_id': {'type': 'string', 'minLength': 1}, 'retained_file': nullable(ref('File')), 'original_file': nullable(ref('File')), 'source_ref': {'type': ['string', 'null'], 'pattern': '^source_[0-9a-f]{24,64}$'}, 'capture': ref('Capture')})
    definitions['Raw'] = obj({'encoding': {'const': 'base64'}, 'data': text, 'sha256': digest, 'size_bytes': integer})
    definitions['Location'] = obj({'input_id': text, 'artifact_ref': nullable_text, 'sha256': digest, 'byte_start_0based': integer, 'byte_end_0based_exclusive': integer, 'line_start_1based': {'type': 'integer', 'minimum': 1}, 'line_end_1based_inclusive': {'type': 'integer', 'minimum': 1}})
    definitions['Token'] = obj({'raw_token': nullable_text, 'raw_base64': text, 'locator': ref('Location')})
    definitions['Issue'] = obj({'code': {'type': 'string', 'pattern': '^vcf_result_'}, 'phase': {'const': 'native_decode'}, 'path': text, 'severity': {'enum': ['qualification', 'error']}, 'evidence_refs': {'type': 'array', 'maxItems': 0}})
    issues = array(ref('Issue'))
    definitions['Attribute'] = obj({'attribute_ordinal_0based': integer, 'key': nullable_text, 'token': ref('Token'), 'value_token': nullable(ref('Token')), 'decoded_value': nullable_text, 'quoted': {'type': 'boolean'}})
    attributes = array(ref('Attribute'))
    definitions['Definition'] = obj({'definition_ordinal_0based': integer, 'line_ordinal_0based': integer, 'namespace': {'enum': ['INFO', 'FORMAT', 'FILTER', 'ALT', 'contig', 'SAMPLE']}, 'id': nullable_text, 'number': nullable_text, 'type': nullable_text, 'description': nullable_text, 'attributes': attributes, 'state': {'enum': ['available', 'malformed']}, 'issues': issues})
    definitions['Meta'] = obj({'line_ordinal_0based': integer, 'key': nullable_text, 'value': nullable(ref('Token')), 'attributes': attributes, 'definition_ordinal_0based': nullable_integer, 'issues': issues})
    definitions['HeaderSample'] = obj({'sample_ordinal_0based': integer, 'column_ordinal_0based': integer, 'name': ref('Token')})
    definitions['Header'] = obj({'state': {'enum': ['available', 'missing', 'malformed', 'truncated', 'unsupported']}, 'fileformat': nullable_text, 'decoder': {'enum': ['vcf4.2', 'unsupported', 'unavailable']}, 'meta_lines': array(ref('Meta')), 'definitions': array(ref('Definition')), 'columns': array(ref('Token')), 'samples': array(ref('HeaderSample')), 'issues': issues})
    definitions['Decoded'] = obj({'kind': {'enum': ['Integer', 'Float', 'String', 'Character', 'missing', 'unknown', 'malformed', 'undecodable', 'overflow', 'underflow', 'nonfinite']}, 'value': {'type': ['integer', 'number', 'string', 'null']}})
    definitions['FieldValue'] = obj({'value_ordinal_0based': integer, 'token': ref('Token'), 'decoded': ref('Decoded'), 'allele_index': nullable_integer, 'genotype_index_0based': nullable_integer, 'genotype_allele_indices': nullable(array(integer))})
    definitions['Cardinality'] = obj({'expected': nullable_integer, 'observed': integer, 'state': {'enum': ['matched', 'mismatch', 'missing', 'unknown']}, 'ploidy': nullable_integer, 'ploidy_basis': {'enum': [None, 'literal_GT_slots']}})
    definitions['Field'] = obj({'field_ordinal_0based': integer, 'key': nullable_text, 'token': nullable(ref('Token')), 'value_token': nullable(ref('Token')), 'has_equals': {'type': ['boolean', 'null']}, 'definition_ordinals': array(integer), 'declared_type': nullable_text, 'declared_number': nullable_text, 'state': {'enum': ['available', 'missing', 'omitted', 'malformed', 'ambiguous_definition', 'undeclared']}, 'flag': {'type': ['boolean', 'null']}, 'values': array(ref('FieldValue')), 'cardinality': ref('Cardinality'), 'issues': issues})
    definitions['Allele'] = obj({'allele_ordinal_0based': integer, 'token': ref('Token'), 'allele_index': nullable_integer, 'state': {'enum': ['called', 'missing', 'malformed', 'outside_alleles']}})
    definitions['Separator'] = obj({'separator_ordinal_0based': integer, 'token': ref('Token'), 'value': {'enum': ['/', '|']}})
    definitions['Genotype'] = obj({'token': ref('Token'), 'alleles': array(ref('Allele')), 'separators': array(ref('Separator')), 'ploidy': nullable_integer, 'state': {'enum': ['available', 'malformed']}})
    definitions['Sample'] = obj({'sample_ordinal_0based': integer, 'sample_name': nullable_text, 'column_present': {'type': 'boolean'}, 'token': nullable(ref('Token')), 'fields': array(ref('Field')), 'genotype': nullable(ref('Genotype')), 'extra_fields': array(ref('Token'))})
    definitions['Format'] = obj({'format_ordinal_0based': integer, 'key': nullable_text, 'token': ref('Token'), 'definition_ordinals': array(integer)})
    definitions['Alt'] = obj({'alt_ordinal_0based': integer, 'allele_index_1based': {'type': 'integer', 'minimum': 1}, 'token': ref('Token')})
    definitions['Qual'] = obj({'token': ref('Token'), 'decoded': ref('Decoded'), 'unit': {'const': 'phred'}})
    definitions['Filter'] = obj({'token': nullable(ref('Token')), 'state': {'enum': ['not_applied', 'passed', 'failed', 'malformed']}, 'codes': array(text)})
    definitions['Record'] = obj({'record_ordinal_0based': integer, 'line_ordinal_0based': integer, 'locator': ref('Location'), 'state': {'enum': ['decoded', 'malformed', 'truncated', 'unsupported']}, 'fixed': obj({key: nullable(ref('Token')) for key in _FIXED}), 'chrom': nullable_text, 'pos_1based': nullable_integer, 'identifiers': array(text), 'ref': nullable_text, 'alts': array(ref('Alt')), 'qual': nullable(ref('Qual')), 'filter': ref('Filter'), 'info': array(ref('Field')), 'format': array(ref('Format')), 'samples': array(ref('Sample')), 'extra_columns': array(ref('Token')), 'issues': issues})
    definitions['Line'] = obj({'line_ordinal_0based': integer, 'kind': {'enum': ['meta', 'header', 'record', 'blank', 'unknown', 'fragment']}, 'locator': ref('Location'), 'newline': {'enum': ['lf', 'crlf', 'cr', 'none']}, 'complete': {'type': 'boolean'}})
    definitions['Selection'] = tag(SELECTION_VERSION, {'record_ordinals': nullable({'type': 'array', 'items': integer, 'uniqueItems': True}), 'sample_ordinals': nullable({'type': 'array', 'items': integer, 'uniqueItems': True}), 'info_keys': nullable({'type': 'array', 'items': {'type': 'string', 'minLength': 1}, 'uniqueItems': True}), 'format_keys': nullable({'type': 'array', 'items': {'type': 'string', 'minLength': 1}, 'uniqueItems': True}), 'offset': integer, 'limit': integer})
    definitions['Fraction'] = obj({'value': {'type': ['number', 'null']}, 'numerator': integer, 'denominator': integer, 'unit': {'const': 'fraction'}, 'missing_reason': {'enum': [None, 'selected_population_empty']}})
    counts = ('retained_record_slots', 'selected_record_slots', 'returned_record_slots', 'omitted_by_window_record_slots', 'selected_alt_tokens', 'returned_alt_tokens', 'selected_sample_cells', 'returned_sample_cells', 'selected_observed_sample_cells', 'returned_observed_sample_cells', 'selected_genotype_slots', 'returned_genotype_slots')
    definitions['Population'] = obj({'capture_state': {'enum': ['complete', 'truncated', 'missing', 'unknown']}, 'header_state': {'enum': ['available', 'missing', 'malformed', 'truncated', 'unsupported']}, 'record_population_complete': {'type': 'boolean'}, 'total_original_record_slots': nullable_integer, **{key: integer for key in counts}, 'offset': integer, 'limit': integer, 'has_more': {'type': 'boolean'}, 'returned_record_fraction': ref('Fraction')})
    definitions['Sheet'] = tag(SHEET_VERSION, {'input': ref('Input'), 'raw_content': nullable(ref('Raw')), 'lines': array(ref('Line')), 'header': ref('Header'), 'records': array(ref('Record')), 'issues': issues})
    definitions['Value'] = tag(VALUE_VERSION, {'input': ref('Input'), 'selection': ref('Selection'), 'population': ref('Population'), 'header': ref('Header'), 'records': array(ref('Record')), 'issues': issues})
    definitions['Components'] = tag(COMPONENTS_VERSION, {'sheet_sha256': digest, 'value': ref('Value')})
    definitions['Return'] = tag(RETURN_VERSION, {'source_ref': {'type': 'string', 'pattern': '^source_[0-9a-f]{24,64}$', 'format': 'reference', 'x-reference-namespace': 'source'}, 'value': ref('Value')})
    return definitions

def vcf_result_schema(kind='Sheet'):
    """Return a detached closed schema; only Return's top Source is semantic."""
    _need(kind in ('Sheet', 'Selection', 'Components', 'Value', 'Return'), 'schema_kind_invalid')
    definitions = _schemas()
    return _copy({'$schema': 'https://json-schema.org/draft/2020-12/schema', '$ref': '#/$defs/' + kind, '$defs': definitions})

def _wire(value, kind):
    value = _copy(value)
    try:
        validate_schema(value, vcf_result_schema(kind))
    except ContractError as error:
        raise ValueError('vcf_result_' + kind.lower() + '_schema_invalid') from error

    def strict(node, parent=None, key=None):
        if type(node) is float:
            numeric = type(parent) is dict and key == 'value' and (set(parent) == {'kind', 'value'} and parent['kind'] == 'Float' or set(parent) == {'value', 'numerator', 'denominator', 'unit', 'missing_reason'})
            _need(numeric, 'integer_alias_invalid')
        elif type(node) is dict:
            for name, child in node.items():
                strict(child, node, name)
        elif type(node) is list:
            for child in node:
                strict(child)
    strict(value)
    return value

def _validate_location(value, item, digest=None):
    _closed(value, ('input_id', 'artifact_ref', 'sha256', 'byte_start_0based', 'byte_end_0based_exclusive', 'line_start_1based', 'line_end_1based_inclusive'))
    file = item['retained_file']
    _need(value['input_id'] == item['input_id'] and value['artifact_ref'] == (None if file is None else file['artifact_ref']), 'locator_identity_conflict')
    _digest(value['sha256'])
    expected_digest = digest if digest is not None else None if file is None else file['sha256']
    _need(expected_digest is None or value['sha256'] == expected_digest, 'locator_identity_conflict')
    for key in ('byte_start_0based', 'byte_end_0based_exclusive'):
        _integer(value[key])
    _need(value['byte_start_0based'] <= value['byte_end_0based_exclusive'] <= item['capture']['byte_end_0based_exclusive'], 'locator_bounds_invalid')
    _integer(value['line_start_1based'], minimum=1)
    _integer(value['line_end_1based_inclusive'], minimum=1)
    _need(value['line_start_1based'] == value['line_end_1based_inclusive'], 'locator_line_invalid')

def _validate_tokens(value, item, raw=None, digest=None):
    if type(value) is list:
        for child in value:
            _validate_tokens(child, item, raw, digest)
    elif type(value) is dict:
        if set(value) == {'raw_token', 'raw_base64', 'locator'}:
            _validate_location(value['locator'], item, digest)
            try:
                payload = base64.b64decode(value['raw_base64'], validate=True)
            except (ValueError, binascii.Error) as error:
                raise ValueError('vcf_result_token_encoding_invalid') from error
            _need(base64.b64encode(payload).decode('ascii') == value['raw_base64'], 'token_encoding_invalid')
            loc = value['locator']
            _need(len(payload) == loc['byte_end_0based_exclusive'] - loc['byte_start_0based'], 'token_size_conflict')
            if raw is not None:
                _need(payload == raw[loc['byte_start_0based']:loc['byte_end_0based_exclusive']], 'token_bytes_conflict')
            try:
                decoded = payload.decode('utf-8')
            except UnicodeDecodeError:
                decoded = None
            _need(value['raw_token'] == decoded, 'token_text_conflict')
        else:
            for child in value.values():
                _validate_tokens(child, item, raw, digest)

def _ordered(values, key, *, contiguous):
    indices = [row[key] for row in values]
    _need(all((type(index) is int and index >= 0 for index in indices)), 'ordinal_invalid')
    _need(len(indices) == len(set(indices)), 'duplicate_ordinal')
    if contiguous:
        _need(indices == list(range(len(indices))), 'ordinal_order_conflict')

def _validate_header(header):
    _ordered(header['definitions'], 'definition_ordinal_0based', contiguous=True)
    _ordered(header['samples'], 'sample_ordinal_0based', contiguous=True)
    _issues(header['issues'])
    formats = [meta for meta in header['meta_lines'] if meta['key'] == 'fileformat']
    declared = formats[0]['value']['raw_token'] if len(formats) == 1 and formats[0]['value'] is not None else None
    _need(header['fileformat'] == declared, 'fileformat_binding_conflict')
    if header['decoder'] == 'vcf4.2':
        _need(declared == 'VCFv4.2', 'decoder_version_conflict')
    if header['decoder'] == 'unavailable':
        _need(declared is None, 'decoder_version_conflict')
    if header['state'] == 'available':
        columns = [token['raw_token'] for token in header['columns']]
        names = [sample['name']['raw_token'] for sample in header['samples']]
        _need(header['decoder'] == 'vcf4.2' and (not header['issues']) and (len(formats) == 1) and (formats[0]['line_ordinal_0based'] == 0) and (tuple(columns[:8]) == _HEADER) and (len(columns) == 8 or (len(columns) >= 10 and columns[8] == 'FORMAT')) and all(names) and (len(names) == len(set(names))), 'available_header_conflict')

    def attributes(rows):
        for attribute in rows:
            payload = base64.b64decode(attribute['token']['raw_base64'])
            left, equal, right = payload.partition(b'=')
            try:
                key = left.decode('utf-8') if equal else None
            except UnicodeDecodeError:
                key = None
            token = attribute['value_token']
            _need(attribute['key'] == key and (token is not None) == bool(equal), 'attribute_token_conflict')
            if token is not None:
                _need(base64.b64decode(token['raw_base64']) == right, 'attribute_token_conflict')
            text = None if token is None else token['raw_token']
            quoted = text is not None and len(text) >= 2 and (text[0] == text[-1] == '"')
            decoded = re.sub('\\\\([\\\\"])', '\\1', text[1:-1]) if quoted else text
            _need(attribute['quoted'] is quoted and attribute['decoded_value'] == decoded, 'attribute_value_conflict')
    for sample in header['samples']:
        index = sample['sample_ordinal_0based']
        _need(sample['column_ordinal_0based'] == index + 9 and index + 9 < len(header['columns']) and _same(sample['name'], header['columns'][index + 9]), 'sample_header_conflict')
    for definition in header['definitions']:
        _ordered(definition['attributes'], 'attribute_ordinal_0based', contiguous=True)
        attributes(definition['attributes'])
        for field, key in (('id', 'ID'), ('number', 'Number'), ('type', 'Type'), ('description', 'Description')):
            matches = [a['decoded_value'] for a in definition['attributes'] if a['key'] == key]
            _need(definition[field] == (matches[0] if len(matches) == 1 else None), 'definition_attribute_conflict')
        _issues(definition['issues'])
    for meta in header['meta_lines']:
        _ordered(meta['attributes'], 'attribute_ordinal_0based', contiguous=True)
        attributes(meta['attributes'])
        index = meta['definition_ordinal_0based']
        if index is not None:
            _need(index < len(header['definitions']), 'definition_reference_invalid')
            definition = header['definitions'][index]
            _need(definition['line_ordinal_0based'] == meta['line_ordinal_0based'] and definition['namespace'] == meta['key'] and _same(definition['attributes'], meta['attributes']), 'definition_reference_conflict')
        _issues(meta['issues'])

def _validate_field(field, header, namespace, alt_count):
    _issues(field['issues'])
    _ordered(field['values'], 'value_ordinal_0based', contiguous=True)
    matches = _definition(header['definitions'], namespace, field['key'])
    _need(field['definition_ordinals'] == [d['definition_ordinal_0based'] for d in matches], 'definition_binding_conflict')
    available = len(matches) == 1 and matches[0]['state'] == 'available'
    kind, number = (matches[0]['type'], matches[0]['number']) if available else (None, None)
    _need(field['declared_type'] == kind and field['declared_number'] == number, 'definition_binding_conflict')
    token, native_value = (field['token'], field['value_token'])
    if namespace == 'INFO' and token is not None:
        payload = base64.b64decode(token['raw_base64'])
        left, equal, right = payload.partition(b'=')
        try:
            key = left.decode('utf-8')
        except UnicodeDecodeError:
            key = None
        _need(field['key'] == key and field['has_equals'] is bool(equal) and ((native_value is not None) == bool(equal)), 'field_token_conflict')
        if native_value is not None:
            _need(base64.b64decode(native_value['raw_base64']) == right, 'field_token_conflict')
    elif namespace == 'FORMAT':
        _need(field['has_equals'] is None and _same(token, native_value), 'field_token_conflict')
    omitted = namespace == 'FORMAT' and token is None and (native_value is None)
    _need(namespace != 'INFO' or token is not None, 'field_token_conflict')
    expected_state = 'omitted' if omitted else 'ambiguous_definition' if len(matches) > 1 else 'undeclared' if not available else 'available'
    expected_flag = None
    if not omitted:
        if namespace == 'INFO' and kind == 'Flag':
            expected_flag = field['has_equals'] is False
            if not expected_flag:
                expected_state = 'malformed'
        elif native_value is None:
            expected_state = 'malformed'
        elif native_value['raw_token'] == '.':
            expected_state = 'missing'
    _need(field['state'] == expected_state and field['flag'] is expected_flag, 'field_state_conflict')
    if native_value is not None and kind != 'Flag':
        payload = base64.b64decode(native_value['raw_base64'])
        expected_values = [payload] if kind == 'String' and number == '1' or not available else payload.split(b',')
        _need([base64.b64decode(v['token']['raw_base64']) for v in field['values']] == expected_values, 'field_value_tokens_conflict')
    cardinality = field['cardinality']
    _need(cardinality['observed'] == len(field['values']), 'cardinality_count_conflict')
    if number == 'G':
        ploidy = cardinality['ploidy']
        _need(ploidy is None or (type(ploidy) is int and ploidy > 0), 'ploidy_invalid')
        expected = None if ploidy is None else math.comb(alt_count + ploidy, ploidy)
        _need(cardinality['ploidy_basis'] == (None if ploidy is None else 'literal_GT_slots'), 'ploidy_basis_conflict')
    else:
        try:
            expected = int(number) if number is not None and number.isdigit() else alt_count if number == 'A' else alt_count + 1 if number == 'R' else None
        except ValueError:
            expected = None
        _need(cardinality['ploidy'] is None and cardinality['ploidy_basis'] is None, 'ploidy_basis_conflict')
    _need(cardinality['expected'] == expected, 'cardinality_expected_conflict')
    expected_state = 'missing' if field['state'] in ('missing', 'omitted') else 'unknown' if expected is None else 'matched' if len(field['values']) == expected else 'mismatch'
    if kind == 'Flag' and field['flag'] is True:
        expected_state = 'matched'
    _need(cardinality['state'] == expected_state, 'cardinality_state_conflict')
    labels = _genotype_labels(alt_count + 1, cardinality['ploidy'], len(field['values'])) if number == 'G' else []
    for index, value in enumerate(field['values']):
        _need(_same(value['decoded'], _number(value['token'], kind)), 'native_value_conflict')
        allele = None if field['state'] == 'missing' else index + 1 if number == 'A' and index < alt_count else index if number == 'R' and index <= alt_count else None
        label = labels[index] if field['state'] != 'missing' and index < len(labels) else None
        _need(value['allele_index'] == allele and value['genotype_index_0based'] == (index if number == 'G' else None) and (value['genotype_allele_indices'] == label), 'value_association_conflict')
    if field['state'] == 'omitted':
        _need(field['token'] is None and field['value_token'] is None and (not field['values']), 'omitted_value_conflict')
    if field['state'] == 'missing':
        _need(field['value_token'] is not None and field['value_token']['raw_token'] == '.', 'missing_value_conflict')
    if field['flag'] is True:
        _need(namespace == 'INFO' and kind == 'Flag' and (number == '0') and (field['has_equals'] is False) and (field['value_token'] is None) and (not field['values']), 'flag_value_conflict')

def _validate_record(record, header, *, selected=False):
    _issues(record['issues'])
    _ordered(record['alts'], 'alt_ordinal_0based', contiguous=True)
    for index, alt in enumerate(record['alts']):
        _need(alt['allele_index_1based'] == index + 1, 'allele_index_conflict')
    alt_token = record['fixed']['alt']
    expected_alts = [] if alt_token is None or alt_token['raw_token'] == '.' else base64.b64decode(alt_token['raw_base64']).split(b',')
    _need([base64.b64decode(alt['token']['raw_base64']) for alt in record['alts']] == expected_alts, 'alternate_tokens_conflict')
    _ordered(record['info'], 'field_ordinal_0based', contiguous=not selected)
    _ordered(record['format'], 'format_ordinal_0based', contiguous=not selected)
    _ordered(record['samples'], 'sample_ordinal_0based', contiguous=not selected)
    for key, value in (('chrom', record['chrom']), ('ref', record['ref'])):
        token = record['fixed'][key]
        _need(value == (None if token is None else token['raw_token']), 'fixed_value_conflict')
    position = record['fixed']['pos']
    try:
        expected_position = int(position['raw_token']) if position is not None and position['raw_token'] is not None and re.fullmatch('[0-9]+', position['raw_token']) else None
    except ValueError:
        expected_position = None
    _need(record['pos_1based'] == expected_position, 'position_value_conflict')
    id_token = record['fixed']['id']
    identifiers = [] if id_token is None or id_token['raw_token'] in (None, '.') else id_token['raw_token'].split(';')
    _need(record['identifiers'] == identifiers, 'identifier_tokens_conflict')
    if record['qual'] is not None:
        _need(_same(record['qual']['token'], record['fixed']['qual']) and _same(record['qual']['decoded'], _number(record['qual']['token'], 'Float')), 'quality_value_conflict')
    filter_value = record['filter']
    _need(_same(filter_value['token'], record['fixed']['filter']), 'filter_token_conflict')
    token = filter_value['token']
    text = None if token is None else token['raw_token']
    if filter_value['state'] == 'not_applied':
        _need(text == '.' and (not filter_value['codes']), 'filter_state_conflict')
    elif filter_value['state'] == 'passed':
        _need(text == 'PASS' and (not filter_value['codes']), 'filter_state_conflict')
    elif filter_value['state'] == 'failed':
        _need(text is not None and text.split(';') == filter_value['codes'] and all((code and code not in ('.', 'PASS', '0') for code in filter_value['codes'])), 'filter_state_conflict')
    for field in record['info']:
        _validate_field(field, header, 'INFO', len(record['alts']))
    format_map = {f['format_ordinal_0based']: f for f in record['format']}
    for fmt in record['format']:
        _need(fmt['key'] == fmt['token']['raw_token'] and fmt['definition_ordinals'] == [d['definition_ordinal_0based'] for d in _definition(header['definitions'], 'FORMAT', fmt['key'])], 'format_binding_conflict')
    for sample in record['samples']:
        index = sample['sample_ordinal_0based']
        _need(sample['sample_name'] == (header['samples'][index]['name']['raw_token'] if index < len(header['samples']) else None), 'sample_name_conflict')
        _need(sample['column_present'] or sample['token'] is None, 'sample_presence_conflict')
        if not selected:
            _need(sample['column_present'] == (sample['token'] is not None), 'sample_presence_conflict')
        _ordered(sample['fields'], 'field_ordinal_0based', contiguous=not selected)
        _need([f['field_ordinal_0based'] for f in sample['fields']] == list(format_map), 'sample_format_binding_conflict')
        for field in sample['fields']:
            _need(field['key'] == format_map[field['field_ordinal_0based']]['key'], 'sample_format_binding_conflict')
            _validate_field(field, header, 'FORMAT', len(record['alts']))
        genotype = sample['genotype']
        if not sample['column_present']:
            _need(genotype is None and all((field['state'] == 'omitted' and field['token'] is None and (field['value_token'] is None) for field in sample['fields'])), 'sample_presence_conflict')
        if genotype is None:
            if not selected:
                _need(all((field['cardinality']['ploidy'] is None for field in sample['fields'] if field['declared_number'] == 'G')), 'genotype_ploidy_conflict')
            continue
        _ordered(genotype['alleles'], 'allele_ordinal_0based', contiguous=True)
        _ordered(genotype['separators'], 'separator_ordinal_0based', contiguous=True)
        _need(len(genotype['alleles']) == len(genotype['separators']) + 1, 'genotype_shape_conflict')
        pieces = []
        for slot, allele in enumerate(genotype['alleles']):
            text = allele['token']['raw_token']
            try:
                called = int(text) if text is not None and re.fullmatch('[0-9]+', text) else None
            except ValueError:
                called = None
            state = 'missing' if text == '.' else 'malformed' if called is None else 'called' if called <= len(record['alts']) else 'outside_alleles'
            _need(allele['allele_index'] == called and allele['state'] == state, 'genotype_allele_conflict')
            pieces.append(base64.b64decode(allele['token']['raw_base64']))
            if slot < len(genotype['separators']):
                separator = genotype['separators'][slot]
                _need(separator['value'] == separator['token']['raw_token'], 'genotype_separator_conflict')
                pieces.append(separator['value'].encode())
        _need(b''.join(pieces) == base64.b64decode(genotype['token']['raw_base64']), 'genotype_token_conflict')
        valid = all((a['state'] in ('called', 'missing') for a in genotype['alleles']))
        ploidy = len(genotype['alleles']) if valid and genotype['token']['raw_token'] != '.' else None
        _need(genotype['ploidy'] == ploidy and genotype['state'] == ('available' if valid else 'malformed'), 'genotype_state_conflict')
        matches = [f for f in sample['fields'] if f['key'] == 'GT']
        _need(len(matches) == 1 and _same(matches[0]['value_token'], genotype['token']), 'genotype_field_conflict')
        for field in sample['fields']:
            if field['declared_number'] == 'G':
                _need(field['cardinality']['ploidy'] == ploidy, 'genotype_ploidy_conflict')

def validate_vcf_sheet(sheet):
    """Validate retained relationships without invoking the VCF parser."""
    sheet = _wire(sheet, 'Sheet')
    raw = _raw(sheet['raw_content'])
    item = sheet['input']
    _input(item, 0 if raw is None else len(raw))
    _need((raw is None) == (item['capture']['state'] == 'missing'), 'missing_capture_conflict')
    if raw is not None and item['retained_file'] is not None:
        _need(item['retained_file']['sha256'] == hashlib.sha256(raw).hexdigest() and item['retained_file']['size_bytes'] == len(raw), 'file_bytes_identity_conflict')
    _issues(sheet['issues'])
    _validate_header(sheet['header'])
    _validate_tokens(sheet['header'], item, raw, None if raw is None else hashlib.sha256(raw).hexdigest())
    _ordered(sheet['lines'], 'line_ordinal_0based', contiguous=True)
    _ordered(sheet['records'], 'record_ordinal_0based', contiguous=True)
    cursor = 0
    for line in sheet['lines']:
        _validate_location(line['locator'], item, None if raw is None else hashlib.sha256(raw).hexdigest())
        loc = line['locator']
        _need(loc['byte_start_0based'] == cursor and loc['line_start_1based'] == line['line_ordinal_0based'] + 1, 'line_order_conflict')
        cursor = loc['byte_end_0based_exclusive']
    _need(raw is None and (not sheet['lines']) and (not sheet['records']) or (raw is not None and (cursor == len(raw) or (sheet['header']['state'] == 'unsupported' and (not sheet['lines']) and (not sheet['records'])))), 'line_coverage_conflict')
    for record in sheet['records']:
        _validate_record(record, sheet['header'])
        _validate_location(record['locator'], item, None if raw is None else hashlib.sha256(raw).hexdigest())
        _validate_tokens(record, item, raw, None if raw is None else hashlib.sha256(raw).hexdigest())
        index = record['line_ordinal_0based']
        _need(index < len(sheet['lines']) and sheet['lines'][index]['kind'] in ('record', 'fragment'), 'record_line_conflict')
        physical = sheet['lines'][index]
        bounds, loc = (physical['locator'], record['locator'])
        terminator_size = {'none': 0, 'lf': 1, 'cr': 1, 'crlf': 2}[physical['newline']]
        _need(loc['line_start_1based'] == index + 1 and loc['byte_start_0based'] == bounds['byte_start_0based'] and (loc['byte_end_0based_exclusive'] == bounds['byte_end_0based_exclusive'] - terminator_size), 'record_line_bounds_conflict')

        def enclosed(node):
            if type(node) is dict:
                if set(node) == {'raw_token', 'raw_base64', 'locator'}:
                    token_loc = node['locator']
                    _need(token_loc['line_start_1based'] == index + 1 and token_loc['line_end_1based_inclusive'] == index + 1 and (loc['byte_start_0based'] <= token_loc['byte_start_0based'] <= token_loc['byte_end_0based_exclusive'] <= loc['byte_end_0based_exclusive']), 'record_token_bounds_conflict')
                else:
                    for child in node.values():
                        enclosed(child)
            elif type(node) is list:
                for child in node:
                    enclosed(child)
        enclosed(record)
    return sheet

def validate_vcf_selection(selection, *, sheet):
    """Check exact caller order; sheet=None permits metadata-only shape checks."""
    selection = _wire(selection, 'Selection')
    for key in ('record_ordinals', 'sample_ordinals'):
        if selection[key] is not None:
            _need(all((type(index) is int and index >= 0 for index in selection[key])) and len(set(selection[key])) == len(selection[key]), 'selection_indices_invalid')
    for key in ('info_keys', 'format_keys'):
        if selection[key] is not None:
            _need(all((type(name) is str and name and (not any((c in name for c in '\t\r\n:;=,'))) for name in selection[key])) and len(set(selection[key])) == len(selection[key]), 'selection_keys_invalid')
    if sheet is not None:
        sheet = validate_vcf_sheet(sheet)
        if selection['record_ordinals'] is not None:
            _need(all((index < len(sheet['records']) for index in selection['record_ordinals'])), 'selected_record_not_retained')
        if selection['sample_ordinals'] is not None:
            sample_bound = max([len(sheet['header']['samples']), *[len(row['samples']) for row in sheet['records']]])
            _need(all((index < sample_bound for index in selection['sample_ordinals'])), 'selected_sample_not_retained')
    return selection

def _counts(rows):
    return {'alt_tokens': sum((len(row['alts']) for row in rows)), 'sample_cells': sum((len(row['samples']) for row in rows)), 'observed_sample_cells': sum((sample['column_present'] for row in rows for sample in row['samples'])), 'genotype_slots': sum((len(sample['genotype']['alleles']) for row in rows for sample in row['samples'] if sample['genotype'] is not None))}

def _validate_value(value):
    value = _wire(value, 'Value')
    item, pop, selection = (value['input'], value['population'], value['selection'])
    _input(item, item['capture']['byte_end_0based_exclusive'])
    if item['retained_file'] is not None and item['capture']['state'] != 'missing':
        _need(item['retained_file']['size_bytes'] == item['capture']['byte_end_0based_exclusive'], 'file_capture_size_conflict')
    validate_vcf_selection(selection, sheet=None)
    _validate_header(value['header'])
    _issues(value['issues'])
    _validate_tokens(value['header'], item)
    _ordered(value['records'], 'record_ordinal_0based', contiguous=False)
    _need(pop['capture_state'] == item['capture']['state'] and pop['header_state'] == value['header']['state'], 'population_context_conflict')
    _need(pop['offset'] == selection['offset'] and pop['limit'] == selection['limit'], 'population_window_conflict')
    selected_count = pop['retained_record_slots'] if selection['record_ordinals'] is None else len(selection['record_ordinals'])
    _need(pop['selected_record_slots'] == selected_count and selected_count <= pop['retained_record_slots'], 'selected_population_conflict')
    if selection['record_ordinals'] is not None:
        _need(all((index < pop['retained_record_slots'] for index in selection['record_ordinals'])), 'selected_record_not_retained')
    returned_count = min(max(selected_count - selection['offset'], 0), selection['limit'])
    expected_ordinals = [selection['offset'] + index for index in range(returned_count)] if selection['record_ordinals'] is None else selection['record_ordinals'][selection['offset']:selection['offset'] + selection['limit']]
    _need([row['record_ordinal_0based'] for row in value['records']] == expected_ordinals, 'returned_record_order_conflict')
    _need(pop['returned_record_slots'] == len(value['records']) == returned_count and pop['omitted_by_window_record_slots'] == selected_count - returned_count and (pop['has_more'] == (selection['offset'] + returned_count < selected_count)), 'returned_population_conflict')
    if pop['record_population_complete']:
        _need(pop['capture_state'] == 'complete' and pop['header_state'] == 'available' and (pop['total_original_record_slots'] == pop['retained_record_slots']), 'complete_population_conflict')
    else:
        _need(pop['total_original_record_slots'] is None, 'unknown_population_conflict')
    for record in value['records']:
        _validate_record(record, value['header'], selected=True)
        _validate_location(record['locator'], item)
        _validate_tokens(record, item)
        if selection['info_keys'] is not None:
            _need(record['fixed']['info'] is None and all((f['key'] in selection['info_keys'] for f in record['info'])), 'unselected_info_exposed')
        if selection['format_keys'] is not None:
            _need(all((f['key'] in selection['format_keys'] for f in record['format'])), 'unselected_format_exposed')
        if selection['sample_ordinals'] is not None:
            _need([s['sample_ordinal_0based'] for s in record['samples']] == [index for index in selection['sample_ordinals'] if any((s['sample_ordinal_0based'] == index for s in record['samples']))], 'selected_sample_order_conflict')
        _need(not record['extra_columns'], 'unselected_columns_exposed')
        for sample in record['samples']:
            if selection['format_keys'] is not None:
                _need(sample['token'] is None and (not sample['extra_fields']) and ('GT' in selection['format_keys'] or sample['genotype'] is None), 'unselected_sample_values_exposed')
    counts = _counts(value['records'])
    for key, count in counts.items():
        _need(pop['returned_' + key] == count and pop['selected_' + key] >= count, 'population_operand_conflict')
        if returned_count == selected_count:
            _need(pop['selected_' + key] == count, 'population_operand_conflict')
    _need(pop['selected_observed_sample_cells'] <= pop['selected_sample_cells'] and pop['returned_observed_sample_cells'] <= pop['returned_sample_cells'], 'sample_population_conflict')
    fraction = pop['returned_record_fraction']
    _need(fraction['numerator'] == returned_count and fraction['denominator'] == selected_count and (fraction['value'] == _ratio(returned_count, selected_count)) and (fraction['missing_reason'] == ('selected_population_empty' if selected_count == 0 else None)), 'population_fraction_conflict')
    return value

def validate_vcf_components(components):
    """Validate selected saved values without calling parser or calculator."""
    components = _wire(components, 'Components')
    _digest(components['sheet_sha256'])
    components['value'] = _validate_value(components['value'])
    return components

def validate_vcf_return(value):
    value = _wire(value, 'Return')
    _text(value['source_ref'])
    _need(_SOURCE.fullmatch(value['source_ref']) is not None, 'source_reference_invalid')
    value['value'] = _validate_value(value['value'])
    return value
