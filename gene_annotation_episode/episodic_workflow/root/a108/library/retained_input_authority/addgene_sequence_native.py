"""Pure readers for supplied Addgene sequence-page representations.

Page categories and sequence identifiers are source assertions.  This module
does not acquire a page, follow a locator, infer topology, or assign confidence.
Raw response bytes and transport provenance remain the caller's responsibility.
"""
from __future__ import annotations
import re
_CATEGORIES = {'addgene-full': ('full', 'addgene_verified'), 'addgene-partial': ('partial', 'addgene_verified'), 'depositor-full': ('full', 'depositor'), 'depositor-partial': ('partial', 'depositor')}
_ISSUES = ('authentication_required', 'response_incomplete', 'representation_unavailable', 'invalid_encoding', 'invalid_html', 'empty_literal', 'invalid_literal', 'incomplete_literal', 'ambiguous_sequence_identity', 'conflicting_sequence_literals', 'download_required')
_DNA = frozenset('ACGTRYSWKMBDHVNacgtryswkmbdhvn')
_LINK = re.compile('(?:https://(?:www\\.)?addgene\\.org)?/browse/sequence/([0-9]+)/?(?:[?#].*)?\\Z')

def _object(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}

def _nullable(kind, **extra):
    return {'type': [kind, 'null'], **extra}
_LOCATOR_SCHEMA = _object({'tag': {'type': 'string', 'minLength': 1}, 'attribute': {'type': 'string', 'minLength': 1}, 'value': {'type': 'string', 'minLength': 1}, 'source_element_ordinal': {'type': 'integer', 'minimum': 0}})
_ROW_SCHEMA = _object({'record_ordinal': {'type': 'integer', 'minimum': 0}, 'sequence_id': _nullable('string', pattern='^[0-9]+$'), 'source_completeness': {'enum': ['full', 'partial', 'unknown']}, 'source_verification': {'enum': ['addgene_verified', 'depositor', 'unknown']}, 'section_id': _nullable('string'), 'native_header': _nullable('string'), 'sequence': _nullable('string', minLength=1), 'sequence_status': {'enum': ['available', 'authentication_required', 'download_required', 'invalid', 'unavailable']}, 'locators': {'type': 'array', 'minItems': 1, 'items': _LOCATOR_SCHEMA}, 'native_sequence_text': _nullable('string'), 'issue_codes': {'type': 'array', 'uniqueItems': True, 'items': {'enum': list(_ISSUES)}}})
ADDGENE_SEQUENCE_PAGE_SCHEMA = {'$schema': 'https://json-schema.org/draft/2020-12/schema', **_object({'version': {'const': 'addgene_sequence_page_v1'}, 'source_ref': {'type': 'string', 'minLength': 1}, 'requested_id': {'type': 'string', 'pattern': '^[0-9]+$'}, 'response_complete': {'type': 'boolean'}, 'parse_status': {'enum': ['complete', 'partial', 'invalid']}, 'authentication_required': {'type': 'boolean'}, 'records': {'type': 'array', 'items': _ROW_SCHEMA}, 'issues': {'type': 'array', 'uniqueItems': True, 'items': _object({'code': {'enum': list(_ISSUES)}, 'record_ordinal': _nullable('integer', minimum=0)})}})}
