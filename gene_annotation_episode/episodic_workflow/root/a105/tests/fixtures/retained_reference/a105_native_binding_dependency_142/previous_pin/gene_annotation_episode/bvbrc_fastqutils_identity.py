"""Canonical FastqUtils identities; no source possession or biological inference."""
from __future__ import annotations

import re
from urllib.parse import quote, unquote_to_bytes

from .bvbrc_fastqutils_contracts import FastqUtilsContractError, json_sha256, validate_contract

_TOKEN = re.compile(r'[A-Za-z][A-Za-z0-9_.-]{0,127}\Z')
_POINTER = re.compile(r'(?:/(?:[^~/]|~[01])*)*\Z')
_DIGEST = re.compile(r'[a-f0-9]{64}\Z')
_INPUT = re.compile(r'/(?:paired_end_libs|single_end_libs|srr_libs)/(?:0|[1-9][0-9]*)\Z')
_KINDS = frozenset(('document', 'artifact', 'cell', 'category', 'label', 'sequence', 'alignment',
                   'header', 'population', 'library', 'stage', 'association', 'lineage',
                   'component', 'requirement', 'field'))
_COLLECTIONS = {'cell': 'cells', 'category': 'categories', 'label': 'labels',
                'sequence': 'sequences', 'alignment': 'alignments', 'header': 'headers', 'lineage': 'lineage'}


def _check(condition):
    if not condition:
        raise FastqUtilsContractError('reference_invalid')


def _escape(value):
    _check(type(value) is str)
    return value.replace('~', '~0').replace('/', '~1')


def _ordinal(value):
    _check(type(value) is int and value >= 0)
    return str(value)


def encode_reference(kind: str, analysis_id: str, pointer: str) -> str:
    _check(type(kind) is str and kind in _KINDS)
    _check(type(analysis_id) is str and _TOKEN.fullmatch(analysis_id))
    _check(type(pointer) is str and _POINTER.fullmatch(pointer))
    try:
        return 'bvbrc_fastqutils_' + kind + ':' + quote(analysis_id, safe='') + '/' + quote(pointer, safe='')
    except UnicodeError as error:
        raise FastqUtilsContractError('reference_invalid') from error


def decode_reference(reference: str, *, expected_kind: str | None = None) -> dict:
    _check(type(reference) is str and reference.startswith('bvbrc_fastqutils_'))
    try:
        prefix, encoded = reference.split(':', 1)
        kind = prefix[len('bvbrc_fastqutils_'):]
        analysis, pointer = encoded.split('/')
        result = {'kind': kind, 'analysis_id': unquote_to_bytes(analysis).decode('utf-8', errors='strict'),
                  'pointer': unquote_to_bytes(pointer).decode('utf-8', errors='strict')}
        _check(expected_kind is None or expected_kind == kind)
        _check(encode_reference(**result) == reference)
        return result
    except (UnicodeError, ValueError) as error:
        if isinstance(error, FastqUtilsContractError):
            raise
        raise FastqUtilsContractError('reference_invalid') from error


def document_ref(analysis_id: str, document_id: str) -> str:
    _check(type(document_id) is str and _TOKEN.fullmatch(document_id))
    return encode_reference('document', analysis_id, '/documents/' + _escape(document_id))


def _artifact_pointer(context):
    context = validate_contract('ParseContext', context)
    return '/documents/' + _escape(context['document_id']) + '/sha256/' + context['content']['sha256']


def artifact_ref(context: dict) -> str:
    context = validate_contract('ParseContext', context)
    return encode_reference('artifact', context['analysis_id'], _artifact_pointer(context))


def native_ref(kind: str, context: dict, ordinal: int) -> str:
    _check(type(kind) is str and kind in _COLLECTIONS)
    context = validate_contract('ParseContext', context)
    return encode_reference(kind, context['analysis_id'], _artifact_pointer(context) +
                            '/' + _COLLECTIONS[kind] + '/' + _ordinal(ordinal))


def population_ref(context: dict, key: str, ordinal: int) -> str:
    _check(type(key) is str and _TOKEN.fullmatch(key))
    context = validate_contract('ParseContext', context)
    return encode_reference('population', context['analysis_id'], _artifact_pointer(context) +
                            '/populations/' + key + '/' + _ordinal(ordinal))


def library_ref(analysis_id: str, task_ref: str, input_pointer: str) -> str:
    _check(type(task_ref) is str and bool(task_ref))
    _check(type(input_pointer) is str and _INPUT.fullmatch(input_pointer))
    return encode_reference('library', analysis_id, '/tasks/' + _escape(task_ref) + '/inputs' + input_pointer)


def stage_ref(analysis_id: str, task_ref: str, recipe_ordinal: int) -> str:
    _check(type(task_ref) is str and bool(task_ref))
    return encode_reference('stage', analysis_id, '/tasks/' + _escape(task_ref) + '/recipe/' + _ordinal(recipe_ordinal))


def metadata_ref(kind: str, analysis_id: str, metadata_id: str) -> str:
    _check(type(kind) is str and kind in ('association', 'population'))
    _check(type(metadata_id) is str and _TOKEN.fullmatch(metadata_id))
    return encode_reference(kind, analysis_id, '/metadata/' + _escape(metadata_id))


def join_ref(kind: str, analysis_id: str, metadata_id: str, population_refs: list[str]) -> str:
    _check(type(kind) is str and kind in ('population', 'cell'))
    _check(type(metadata_id) is str and _TOKEN.fullmatch(metadata_id))
    _check(type(population_refs) is list and bool(population_refs))
    for reference in population_refs:
        decoded = decode_reference(reference, expected_kind='population')
        _check(decoded['analysis_id'] == analysis_id)
    return encode_reference(kind, analysis_id, '/metadata/' + _escape(metadata_id) + '/inputs/' +
                            json_sha256(sorted(population_refs)) + '/' + kind)


def component_ref(analysis_id: str, sheet_sha256: str, parameters_sha256: str,
                  calculation_id: str, metric: str, threshold: int | None) -> str:
    _check(type(sheet_sha256) is str and _DIGEST.fullmatch(sheet_sha256))
    _check(type(parameters_sha256) is str and _DIGEST.fullmatch(parameters_sha256))
    _check(type(calculation_id) is str and _TOKEN.fullmatch(calculation_id))
    _check(type(metric) is str and _TOKEN.fullmatch(metric))
    suffix = 'none' if threshold is None else _ordinal(threshold)
    return encode_reference('component', analysis_id, '/sheets/' + sheet_sha256 + '/parameters/' +
                            parameters_sha256 + '/calculations/' + _escape(calculation_id) + '/' + metric + '/' + suffix)


def requirement_ref(analysis_id: str, scope_pointer: str, code: str) -> str:
    _check(type(scope_pointer) is str and _POINTER.fullmatch(scope_pointer))
    _check(type(code) is str and _TOKEN.fullmatch(code))
    return encode_reference('requirement', analysis_id, scope_pointer + '/' + code)


def literal_ref(analysis_id: str, record_ref: str, field_pointer: str) -> str:
    _check(type(record_ref) is str and bool(record_ref))
    _check(type(field_pointer) is str and _POINTER.fullmatch(field_pointer))
    return encode_reference('label', analysis_id, '/records/' + _escape(record_ref) + field_pointer)


def field_ref(analysis_id: str, field: str) -> str:
    _check(type(field) is str and _TOKEN.fullmatch(field))
    return encode_reference('field', analysis_id, '/facts/' + _escape(field))
