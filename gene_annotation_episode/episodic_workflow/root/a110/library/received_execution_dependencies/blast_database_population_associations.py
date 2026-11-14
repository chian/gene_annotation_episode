from __future__ import annotations
import math
import re
CONTEXT_SCHEMA = 'blast_database_population_context_v1'
ASSOCIATION_SCHEMA = 'blast_database_population_association_input_v1'
PREFIX = 'blast_database_population_'
_KEY = {'artifact_key', 'member_ordinal', 'report_index', 'search_pointer'}
_PROVENANCE = {'source_ref', 'pointer'}
_SEMANTIC = {'namespace', 'value', 'version', 'release', 'scope', 'preparation_type'}
_SELECTED = {'native_database_operand', 'native_paths', 'identity', 'manifest_sha256', 'manifest_size_bytes', 'invocation_source', 'manifest_source'}
_RECORD = {'source_ref', 'artifact_ref', 'sha256', 'size_bytes', 'pointer', 'value'}
_ASSOCIATION = {'schema', 'association_key', 'search_key', 'database_key', 'metadata_source', 'assertion_source', 'census_source', 'selected_database', 'assertion_record', 'census_record'}

def _copy(value):
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float and math.isfinite(value):
        return value
    if type(value) is list:
        return [_copy(v) for v in value]
    if type(value) is dict and all((type(k) is str for k in value)):
        return {k: _copy(v) for k, v in value.items()}
    raise ValueError(PREFIX + 'finite_json_required')

def _fields(value, keys):
    return type(value) is dict and set(value) == keys

def _text(value):
    return type(value) is str and bool(value.strip())

def _integer(value, minimum=0):
    return type(value) is int and value >= minimum

def _pointer(value):
    return type(value) is str and (not value or value.startswith('/')) and (re.search('~(?![01])', value) is None)

def _digest(value):
    return type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None

def _provenance(value):
    return _fields(value, _PROVENANCE) and _text(value['source_ref']) and _pointer(value['pointer'])

def _key(value):
    return _fields(value, _KEY) and _text(value['artifact_key']) and _integer(value['report_index']) and (value['member_ordinal'] is None or _integer(value['member_ordinal'])) and _pointer(value['search_pointer'])

def _identity(value, *, source):
    return _fields(value, _SEMANTIC | ({'source'} if source else set())) and all((_text(value[k]) for k in ('namespace', 'value'))) and all((value[k] is None or _text(value[k]) for k in ('version', 'release', 'scope'))) and (value['preparation_type'] in ('sequence_database', 'rps', 'delta', 'unknown')) and (not source or _provenance(value['source']))

def _record(value):
    return _fields(value, _RECORD) and all((_text(value[k]) for k in ('source_ref', 'artifact_ref'))) and _digest(value['sha256']) and _integer(value['size_bytes']) and _pointer(value['pointer'])

def _selected(value):
    return _fields(value, _SELECTED) and _text(value['native_database_operand']) and (type(value['native_paths']) is list) and bool(value['native_paths']) and all((_text(p) for p in value['native_paths'])) and _identity(value['identity'], source=True) and _digest(value['manifest_sha256']) and _integer(value['manifest_size_bytes']) and _provenance(value['invocation_source']) and _provenance(value['manifest_source'])

def validate_blast_database_population_context(context: dict) -> dict:
    """Detach the unchanged closed input, preserving every raw source value.

    Structural caller errors raise the two closed contract codes. An assertion
    or census's original JSON ``value`` is intentionally not normalized here;
    malformed source contents remain inspectable during qualification.
    """
    context = _copy(context)
    valid = _fields(context, {'schema', 'search_key', 'associations'}) and context['schema'] == CONTEXT_SCHEMA and _key(context['search_key']) and (type(context['associations']) is list)
    if valid:
        for row in context['associations']:
            valid = _fields(row, _ASSOCIATION) and row['schema'] == ASSOCIATION_SCHEMA and _key(row['search_key']) and all((_text(row[k]) for k in ('association_key', 'database_key'))) and all((_provenance(row[k]) for k in ('metadata_source', 'assertion_source', 'census_source'))) and (row['selected_database'] is None or _selected(row['selected_database'])) and all((row[k] is None or _record(row[k]) for k in ('assertion_record', 'census_record')))
            if not valid:
                break
    if not valid:
        raise ValueError(PREFIX + 'context_fields_invalid')
    return context
