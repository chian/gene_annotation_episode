"""Typed views of the existing native MACS2 peak components.

Native row, geometry, number and issue definitions come from the shared ATAC
contracts. A result is a retained-data view, never an annotation-confidence
score or a request to execute MACS2.
"""
from copy import deepcopy
import json
from jsonschema import Draft202012Validator, validators
from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.atac_differential_result_contracts import atac_result_schema, canonical, digest
VERSION = 'ordinary_macs2_peak_result_v1'
FACT_SOURCE = 'macs2_peak_outcomes'
_SOURCE = {'type': 'string', 'pattern': '^source_[0-9a-f]{24,64}$', 'format': 'reference', 'x-reference-namespace': 'source'}
_STATUS = {'enum': ['complete', 'partial', 'unavailable']}
_NATIVE = {'enum': ['succeeded', 'failed', 'not_run', 'unknown']}
_STRICT = validators.extend(Draft202012Validator, type_checker=Draft202012Validator.TYPE_CHECKER.redefine('integer', lambda _checker, value: type(value) is int))

def _require(condition, code):
    if not condition:
        raise ValueError('macs2_peak_' + code)

def _object(properties):
    return dict(type='object', properties=properties, required=list(properties), additionalProperties=False)

def _definitions():
    definitions = {}
    for kind in ('NativePeakWindow', 'ParsedMacs2PeaksXls', 'NativePeakComponents', 'Summary'):
        for name, definition in atac_result_schema(kind)['$defs'].items():
            _require(name not in definitions or canonical(definitions[name]) == canonical(definition), 'shared_definition_conflict')
            definitions[name] = deepcopy(definition)
    failure_schema = atac_result_schema('Failure')
    definitions['Failure'] = {key: deepcopy(value) for key, value in failure_schema.items() if key not in ('$schema', '$defs', '$id')}
    for name, definition in failure_schema.get('$defs', {}).items():
        _require(name not in definitions or canonical(definitions[name]) == canonical(definition), 'shared_definition_conflict')
        definitions[name] = deepcopy(definition)
    xls = definitions['ParsedMacs2PeaksXls']['properties']
    properties = dict(version={'const': VERSION}, source_ref=deepcopy(_SOURCE), status=deepcopy(_STATUS), native_outcome=deepcopy(_NATIVE), run_key=deepcopy(definitions['AtacCallpeakBinding']['properties']['run_key']), reference_id=deepcopy(definitions['AtacReference']['properties']['reference_id']), native_peak_counts=deepcopy(definitions['Summary']['properties']['native_peak_counts']), reported_metadata=deepcopy(xls['reported_metadata']), reported_numbers=deepcopy(xls['reported_numbers']), peak_window={'$ref': '#/$defs/NativePeakWindow'}, issues=deepcopy(definitions['NativePeakComponents']['properties']['issues']), failures={'type': 'array', 'items': {'$ref': '#/$defs/Failure'}})
    definitions['Macs2PeakReturn'] = _object(properties)
    definitions['Macs2PeakValue'] = _object({key: deepcopy(value) for key, value in properties.items() if key not in ('version', 'source_ref')})
    return definitions

def macs2_peak_result_schema(kind='Return'):
    """Export only definitions reachable from the exact selected view."""
    names = {'Return': 'Macs2PeakReturn', 'Value': 'Macs2PeakValue'}
    _require(kind in names, 'schema_invalid')
    definitions, pending, reachable = (_definitions(), [names[kind]], {})
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
    return {'$schema': 'https://json-schema.org/draft/2020-12/schema', '$ref': '#/$defs/' + names[kind], '$defs': reachable}

def _validate(kind, value):
    try:
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

def macs2_peak_fact_sources():
    schema = macs2_peak_result_schema('Return')
    result = {'$schema': schema['$schema'], '$defs': schema['$defs'], 'type': 'array', 'items': {'$ref': schema['$ref']}, 'x-source': FACT_SOURCE}
    result['$id'] = 'urn:gene-annotation:macs2-peak-return:' + digest(result)
    return {FACT_SOURCE: dict(type='array', meaning='Recorded native MACS2 treatment/control peak measurements, preserving selected row windows, format-specific coordinates, reported numbers, source associations, missingness and qualifications; enrichment peaks do not establish direct binding or gene-function correctness.', report_schema=result)}
