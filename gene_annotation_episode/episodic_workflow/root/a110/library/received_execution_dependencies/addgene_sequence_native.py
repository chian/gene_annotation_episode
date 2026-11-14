from __future__ import annotations
from copy import deepcopy
import re
_CATEGORIES = {'addgene-full': ('full', 'addgene_verified'), 'addgene-partial': ('partial', 'addgene_verified'), 'depositor-full': ('full', 'depositor'), 'depositor-partial': ('partial', 'depositor')}
_ISSUES = ('authentication_required', 'response_incomplete', 'representation_unavailable', 'invalid_encoding', 'invalid_html', 'empty_literal', 'invalid_literal', 'incomplete_literal', 'ambiguous_sequence_identity', 'conflicting_sequence_literals', 'download_required')
_DNA = frozenset('ACGTRYSWKMBDHVNacgtryswkmbdhvn')
_ASCII_SPACE = ' \t\r\n\x0b\x0c'
_LINK = re.compile('(?:https://(?:www\\.)?addgene\\.org)?/browse/sequence/([0-9]+)/?(?:[?#].*)?\\Z')

def _object(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}

def _nullable(kind, **extra):
    return {'type': [kind, 'null'], **extra}
_LOCATOR_SCHEMA = _object({'tag': {'type': 'string', 'minLength': 1}, 'attribute': {'type': 'string', 'minLength': 1}, 'value': {'type': 'string', 'minLength': 1}, 'source_element_ordinal': {'type': 'integer', 'minimum': 0}})
_ROW_SCHEMA = _object({'record_ordinal': {'type': 'integer', 'minimum': 0}, 'sequence_id': _nullable('string', pattern='^[0-9]+$'), 'source_completeness': {'enum': ['full', 'partial', 'unknown']}, 'source_verification': {'enum': ['addgene_verified', 'depositor', 'unknown']}, 'section_id': _nullable('string'), 'native_header': _nullable('string'), 'sequence': _nullable('string', minLength=1), 'sequence_status': {'enum': ['available', 'authentication_required', 'download_required', 'invalid', 'unavailable']}, 'locators': {'type': 'array', 'minItems': 1, 'items': _LOCATOR_SCHEMA}, 'native_sequence_text': _nullable('string'), 'issue_codes': {'type': 'array', 'uniqueItems': True, 'items': {'enum': list(_ISSUES)}}})
ADDGENE_SEQUENCE_PAGE_SCHEMA = {'$schema': 'https://json-schema.org/draft/2020-12/schema', **_object({'version': {'const': 'addgene_sequence_page_v1'}, 'source_ref': {'type': 'string', 'minLength': 1}, 'requested_id': {'type': 'string', 'pattern': '^[0-9]+$'}, 'response_complete': {'type': 'boolean'}, 'parse_status': {'enum': ['complete', 'partial', 'invalid']}, 'authentication_required': {'type': 'boolean'}, 'records': {'type': 'array', 'items': _ROW_SCHEMA}, 'issues': {'type': 'array', 'uniqueItems': True, 'items': _object({'code': {'enum': list(_ISSUES)}, 'record_ordinal': _nullable('integer', minimum=0)})}})}

def _schema_check(value, schema):
    """Validate this closed JSON schema without importing an execution library."""
    if 'const' in schema and (type(value) is not type(schema['const']) or value != schema['const']):
        raise ValueError('addgene_sequence_schema')
    if 'enum' in schema and (not any((type(value) is type(item) and value == item for item in schema['enum']))):
        raise ValueError('addgene_sequence_schema')
    types = {'object': dict, 'array': list, 'string': str, 'integer': int, 'boolean': bool, 'null': type(None)}
    wanted = schema.get('type')
    if wanted is not None:
        wanted = [wanted] if type(wanted) is str else wanted
        if type(value) not in [types[item] for item in wanted]:
            raise ValueError('addgene_sequence_schema')
    if value is None:
        return
    if type(value) is dict:
        if set(value) != set(schema['properties']):
            raise ValueError('addgene_sequence_schema')
        for key, item in value.items():
            _schema_check(item, schema['properties'][key])
    elif type(value) is list:
        if len(value) < schema.get('minItems', 0):
            raise ValueError('addgene_sequence_schema')
        if schema.get('uniqueItems') and any((item in value[:index] for index, item in enumerate(value))):
            raise ValueError('addgene_sequence_schema')
        for item in value:
            _schema_check(item, schema['items'])
    elif type(value) is str:
        if len(value) < schema.get('minLength', 0) or ('pattern' in schema and re.fullmatch(schema['pattern'], value) is None):
            raise ValueError('addgene_sequence_schema')
    elif type(value) is int and value < schema.get('minimum', value):
        raise ValueError('addgene_sequence_schema')

def _literal(text):
    lines = re.split('\\r\\n|\\r|\\n', text)
    first = next((index for index, line in enumerate(lines) if line.strip(_ASCII_SPACE)), None)
    if first is None:
        return (None, None, 'empty_literal')
    header = lines[first] if lines[first].startswith('>') else None
    body = lines[first + 1:] if header is not None else lines[first:]
    sequence = ''.join(body).translate({ord(symbol): None for symbol in _ASCII_SPACE})
    if not sequence:
        return (header, None, 'empty_literal')
    if not set(sequence) <= _DNA or (header is not None and (not header[1:].strip(_ASCII_SPACE))):
        return (header, None, 'invalid_literal')
    return (header, sequence, None)

def _page_status(page):
    if any((issue['code'] in {'invalid_encoding', 'invalid_html'} for issue in page['issues'])) and (not page['records']):
        return 'invalid'
    return 'complete' if page['response_complete'] and page['records'] and (not page['issues']) else 'partial'

def validate_addgene_sequence_page(value) -> dict:
    """Return detached typed data; reject contradictory status/identity joins."""
    try:
        _schema_check(value, ADDGENE_SEQUENCE_PAGE_SCHEMA)
        page = deepcopy(value)
    except (RecursionError, TypeError) as error:
        raise ValueError('addgene_sequence_finite_json_required') from error
    rows = page['records']
    if not page['source_ref'].strip() or page['parse_status'] != _page_status(page):
        raise ValueError('addgene_sequence_page_relationship')
    issues = {(item['code'], item['record_ordinal']) for item in page['issues']}
    for code, ordinal in issues:
        if ordinal is not None and ordinal >= len(rows):
            raise ValueError('addgene_sequence_issue_relationship')
    if (('response_incomplete', None) in issues) != (not page['response_complete']):
        raise ValueError('addgene_sequence_response_relationship')
    if (('authentication_required', None) in issues) != page['authentication_required']:
        raise ValueError('addgene_sequence_authentication_relationship')
    if not rows and (not any((code in {'representation_unavailable', 'invalid_encoding', 'invalid_html'} for code, _ in issues))):
        raise ValueError('addgene_sequence_empty_relationship')
    locator_owners, previous_first = ({}, -1)
    for ordinal, row in enumerate(rows):
        if row['record_ordinal'] != ordinal:
            raise ValueError('addgene_sequence_record_ordinal')
        category = _CATEGORIES.get(row['section_id'], ('unknown', 'unknown'))
        if (row['source_completeness'], row['source_verification']) != category:
            raise ValueError('addgene_sequence_category_relationship')
        if set(row['issue_codes']) != {code for code, owner in issues if owner == ordinal}:
            raise ValueError('addgene_sequence_issue_relationship')
        source_ordinals = [locator['source_element_ordinal'] for locator in row['locators']]
        if source_ordinals != sorted(source_ordinals) or source_ordinals[0] <= previous_first:
            raise ValueError('addgene_sequence_locator_order')
        previous_first = source_ordinals[0]
        status, text = (row['sequence_status'], row['native_sequence_text'])
        if status == 'available':
            if text is None or row['sequence'] is None or row['issue_codes']:
                raise ValueError('addgene_sequence_status_relationship')
            header, sequence, issue = _literal(text)
            if issue is not None or (header, sequence) != (row['native_header'], row['sequence']):
                raise ValueError('addgene_sequence_literal_relationship')
        elif row['sequence'] is not None:
            raise ValueError('addgene_sequence_status_relationship')
        elif status == 'authentication_required':
            if not page['authentication_required'] or row['issue_codes'] != ['authentication_required'] or text is not None:
                raise ValueError('addgene_sequence_authentication_relationship')
        elif status == 'download_required':
            if text is not None or row['native_header'] is not None or row['sequence_id'] is None or (row['issue_codes'] != ['download_required']) or page['authentication_required']:
                raise ValueError('addgene_sequence_status_relationship')
        elif status == 'invalid':
            if text is None or not row['issue_codes'] or (not set(row['issue_codes']) <= {'empty_literal', 'invalid_literal', 'incomplete_literal', 'ambiguous_sequence_identity', 'conflicting_sequence_literals'}):
                raise ValueError('addgene_sequence_status_relationship')
            header, _, literal_issue = _literal(text)
            if header != row['native_header'] or (literal_issue is not None and literal_issue not in row['issue_codes']):
                raise ValueError('addgene_sequence_literal_relationship')
        elif text is not None or row['native_header'] is not None or (not row['issue_codes']):
            raise ValueError('addgene_sequence_status_relationship')
        for locator in row['locators']:
            key = tuple((locator[name] for name in ('tag', 'attribute', 'value', 'source_element_ordinal')))
            if key in locator_owners:
                raise ValueError('addgene_sequence_duplicate_locator')
            locator_owners[key] = ordinal
            if locator['tag'] != locator['tag'].lower() or locator['attribute'] != locator['attribute'].lower():
                raise ValueError('addgene_sequence_locator_relationship')
            if locator['attribute'] == 'href':
                match = _LINK.fullmatch(locator['value'])
                if locator['tag'] != 'a' or match is None or match[1] != row['sequence_id']:
                    raise ValueError('addgene_sequence_locator_relationship')
            elif locator['tag'] != 'textarea' or locator['attribute'] != 'class' or 'copy-from' not in locator['value'].split():
                raise ValueError('addgene_sequence_locator_relationship')
    return page
