"""Typed views of the existing native MACS2 peak components.

Native row, geometry, number and issue definitions come from the shared ATAC
contracts. A result is a retained-data view, never an annotation-confidence
score or a request to execute MACS2.
"""
from copy import deepcopy
import json

from jsonschema import Draft202012Validator, validators

from .atac_differential_result_contracts import (
    atac_result_schema, canonical, digest, validate_atac_result_record,
)
from .macs2_peak_components import native_peak_counts, project_native_peak_window


TOOL = 'result.macs2.peaks'
VERSION = 'ordinary_macs2_peak_result_v1'
PACKET_VERSION = 'ordinary_macs2_peak_packet_v1'
STORED_VERSION = 'ordinary_macs2_peak_stored_v1'
CONTROL_VERSION = 'ordinary_macs2_peak_publication_v1'
FACT_SOURCE = 'macs2_peak_outcomes'
_SOURCE = {'type': 'string', 'pattern': '^source_[0-9a-f]{24,64}$',
    'format': 'reference', 'x-reference-namespace': 'source'}
_STATUS = {'enum': ['complete', 'partial', 'unavailable']}
_NATIVE = {'enum': ['succeeded', 'failed', 'not_run', 'unknown']}
_STRICT = validators.extend(Draft202012Validator, type_checker=
    Draft202012Validator.TYPE_CHECKER.redefine('integer', lambda _checker, value: type(value) is int))


def _require(condition, code):
    if not condition:
        raise ValueError('macs2_peak_' + code)


def _object(properties):
    return dict(type='object', properties=properties, required=list(properties), additionalProperties=False)


def _definitions():
    definitions = {}
    for kind in ('NativePeakWindow', 'ParsedMacs2PeaksXls', 'NativePeakComponents', 'Summary'):
        for name, definition in atac_result_schema(kind)['$defs'].items():
            _require(name not in definitions or canonical(definitions[name]) == canonical(definition),
                'shared_definition_conflict')
            definitions[name] = deepcopy(definition)
    # Failure is the exact native contract's direct object, rather than a
    # result-schema document with a $defs wrapper.
    failure_schema = atac_result_schema('Failure')
    definitions['Failure'] = {key: deepcopy(value) for key, value in failure_schema.items()
        if key not in ('$schema', '$defs', '$id')}
    for name, definition in failure_schema.get('$defs', {}).items():
        _require(name not in definitions or canonical(definitions[name]) == canonical(definition),
            'shared_definition_conflict')
        definitions[name] = deepcopy(definition)
    xls = definitions['ParsedMacs2PeaksXls']['properties']
    properties = dict(version={'const': VERSION}, source_ref=deepcopy(_SOURCE), status=deepcopy(_STATUS),
        native_outcome=deepcopy(_NATIVE),
        run_key=deepcopy(definitions['AtacCallpeakBinding']['properties']['run_key']),
        reference_id=deepcopy(definitions['AtacReference']['properties']['reference_id']),
        native_peak_counts=deepcopy(definitions['Summary']['properties']['native_peak_counts']),
        reported_metadata=deepcopy(xls['reported_metadata']), reported_numbers=deepcopy(xls['reported_numbers']),
        peak_window={'$ref': '#/$defs/NativePeakWindow'},
        issues=deepcopy(definitions['NativePeakComponents']['properties']['issues']),
        failures={'type': 'array', 'items': {'$ref': '#/$defs/Failure'}})
    definitions['Macs2PeakReturn'] = _object(properties)
    definitions['Macs2PeakValue'] = _object({key: deepcopy(value) for key, value in properties.items()
        if key not in ('version', 'source_ref')})
    return definitions


def macs2_peak_result_schema(kind='Return'):
    """Export only definitions reachable from the exact selected view."""
    names = {'Return': 'Macs2PeakReturn', 'Value': 'Macs2PeakValue'}
    _require(kind in names, 'schema_invalid')
    definitions, pending, reachable = _definitions(), [names[kind]], {}
    while pending:
        name = pending.pop()
        if name in reachable:
            continue
        reachable[name] = deepcopy(definitions[name])
        def references(value):
            if isinstance(value, dict):
                if '$ref' in value:
                    reference = value['$ref']
                    _require(reference.startswith('#/$defs/'), 'shared_reference_invalid')
                    yield reference.removeprefix('#/$defs/')
                for child in value.values():
                    yield from references(child)
            elif isinstance(value, list):
                for child in value:
                    yield from references(child)
        pending.extend(references(reachable[name]))
    return {'$schema': 'https://json-schema.org/draft/2020-12/schema',
        '$ref': '#/$defs/' + names[kind], '$defs': reachable}


def _validate(kind, value):
    try:
        # This also excludes non-JSON and nonfinite values without repairing
        # native lexical tokens retained by the common readers.
        value = json.loads(canonical(value))
        _STRICT(macs2_peak_result_schema(kind)).validate(value)
    except (ValueError, TypeError, KeyError) as error:
        raise ValueError('macs2_peak_return_invalid') from error
    except Exception as error:
        from jsonschema.exceptions import ValidationError
        if not isinstance(error, ValidationError):
            raise
        raise ValueError('macs2_peak_return_invalid') from error
    return value


def validate_macs2_peak_return(value):
    return _validate('Return', value)


def project_macs2_peak_values(components, *, native_outcome, row_window, failures=()):
    """Select values using the one shared counter and native-row projector."""
    components = validate_atac_result_record('NativePeakComponents', components)
    _require(native_outcome in _NATIVE['enum'], 'native_outcome_invalid')
    _require(len(components['callpeak_bindings']) == 1, 'single_callpeak_required')
    binding = components['callpeak_bindings'][0]
    reports = [row for row in components['peaks_xls'] if row['callpeak_run_key'] == binding['run_key']]
    _require(len(reports) == 1, 'xls_association_invalid')
    status = ('unavailable' if components['data_status'] == 'unavailable' else 'complete'
        if components['data_status'] == 'complete_reported_data' and not components['issues'] and not failures
        and native_outcome == 'succeeded' else 'partial')
    value = dict(status=status, native_outcome=native_outcome, run_key=binding['run_key'],
        reference_id=components['reference']['reference_id'], native_peak_counts=native_peak_counts(components),
        reported_metadata=deepcopy(reports[0]['reported_metadata']),
        reported_numbers=deepcopy(reports[0]['reported_numbers']),
        peak_window=project_native_peak_window(components, run_keys=[binding['run_key']], row_window=row_window),
        issues=deepcopy(components['issues']), failures=deepcopy(list(failures)))
    return _validate('Value', value)


def macs2_peak_return(value, *, source_ref):
    return validate_macs2_peak_return(dict(version=VERSION, source_ref=source_ref,
        **_validate('Value', value)))


def macs2_peak_fact_sources():
    schema = macs2_peak_result_schema('Return')
    result = {'$schema': schema['$schema'], '$defs': schema['$defs'], 'type': 'array',
        'items': {'$ref': schema['$ref']}, 'x-source': FACT_SOURCE}
    result['$id'] = 'urn:gene-annotation:macs2-peak-return:' + digest(result)
    return {FACT_SOURCE: dict(type='array', meaning=(
        'Recorded native MACS2 treatment/control peak measurements, preserving selected row windows, '
        'format-specific coordinates, reported numbers, source associations, missingness and qualifications; '
        'enrichment peaks do not establish direct binding or gene-function correctness.'), report_schema=result)}


__all__ = ['TOOL', 'VERSION', 'PACKET_VERSION', 'STORED_VERSION', 'CONTROL_VERSION', 'FACT_SOURCE',
    'macs2_peak_result_schema', 'validate_macs2_peak_return', 'project_macs2_peak_values',
    'macs2_peak_return', 'macs2_peak_fact_sources']
