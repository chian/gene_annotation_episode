from pathlib import Path
base=Path('gene_annotation_episode')
old=(base/'bvbrc_proteome_returns.py').read_text()
start=old.index('class BVBRCProteomeReturns(')
cls=old[start:old.index('\n\n__all__',start)]
cls=cls.replace('BVBRCProteomeReturns','BVBRCComparativeSystemsReturns').replace('proteome_fact_sources','comparative_systems_fact_sources').replace('project_proteome_facts','project_comparative_systems_return_facts').replace('ProteomeReturnError','ComparativeSystemsReturnError').replace('proteome_adapter_required','comparative_adapter_required')
cls=cls.replace('item: _validate_fact(_KINDS[source], value)', 'item: _validate_fact(_KINDS[source], value)')
cls=cls.replace('lambda value: _validate_fact(_KINDS[source], value)', 'lambda value: _validate_fact(_KINDS[source], value)')
(base/'bvbrc_comparative_systems_returns.py').write_text('''"""Original ComparativeSystems numerical facts through existing typed returns.

The provider's internal JSON Schema is rendered separately for communication.
Every value is copied from its authenticated original publication. Saved reads
perform no parsing, scientific calculation, network call or model composition.
"""
from __future__ import annotations

from copy import deepcopy
import json
import re

from .bvbrc_comparative_systems_fact_contracts import (
    FACT_SOURCES as _FAMILY_MAP, MARKER, validate_requested_form, requested_selection,
    validate_requested_selection,
)
from .bvbrc_comparative_systems_handoff_contracts import schema as shared_schema, validate_shape
from .bvbrc_comparative_systems_bundle_contracts import validate_parameters
from .bvbrc_comparative_systems_bundle_projection import validate_saved_comparative_systems_projection
from .bvbrc_comparative_systems_publication import decode_comparative_publication_result
from .bvbrc_appservice_contracts import _finite_json, _Validator, validate_contract
from .bvbrc_appservice_custody import _references
from .bvbrc_appservice_publication import RESULT_VERSION
from .bvbrc_appservice_saved_results import read_latest_adapter_result
from .communication import plain, validate_form, validate_closed_schema
from .episode_return_records import EpisodeReturnRecords, _same
from .execution_contracts import canonical, digest
from .form_reference_validation import _binding_key, form_validation_value

FACT_SOURCES = tuple(dict.fromkeys(_FAMILY_MAP.values()))
_KINDS = {source: kind for kind, source in _FAMILY_MAP.items() if kind != 'computed_measurement'}
_VALUE_TYPES = {'measurement': 'NumericCellV1', 'ratio': 'RatioComponentV1',
    'population': 'PopulationFactV1', 'membership': 'MembershipFactV1',
    'requirement': 'RequirementV1', 'qualification': 'DiagnosticV1'}
IDENTIFIER_NAMESPACES = tuple('bvbrc_comparative_systems_' + value for value in
    ('analysis', 'population', 'owner', 'pointer', 'identifier'))
_PREFIX = 'bvbrc_comparative_systems_return_'
_ADAPTER_ID, _ADAPTER_VERSION = 'bvbrc_comparative_systems', '1'
_ADAPTER_VERSIONS = ('1',)
_SOURCE_ID = re.compile(r'source_[a-f0-9]{24,64}\\Z')
_IDENTIFIER_FIELDS = {'field', 'field_id', 'document_id', 'requirement_id', 'affected_field_ids',
    'family_id', 'pathway_id', 'ec_number', 'subsystem_id', 'role_id', 'superclass_native',
    'superclass_aggregation', 'class_name', 'subclass', 'subsystem_name', 'comparison_id',
    'genome_id', 'member_id', 'native_field', 'raw_artifact_ref', 'missing_members',
    'unresolved_members'}


class ComparativeSystemsReturnError(ValueError):
    def __init__(self, code, path=''):
        self.code, self.path = _PREFIX + code, path
        self.diagnostics = [{'code': self.code, 'path': path}]
        super().__init__(self.code)


def _require(condition, code, path=''):
    if not condition:
        raise ComparativeSystemsReturnError(code, path)


def _object(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}


def _identifier(namespace, *, reference=False):
    return {'type': 'string', 'format': 'reference' if reference else 'identifier', 'x-reference-namespace': namespace}


def _expanded(name):
    closure = shared_schema(name)
    def expand(node):
        if type(node) is list:
            return [expand(value) for value in node]
        if type(node) is not dict:
            return node
        if '$ref' in node:
            return expand(closure['$defs'][node['$ref'].split('/')[-1]])
        return {key: expand(value) for key, value in node.items()}
    return expand(closure['$defs'][name])


def _value_schema(kind):
    if kind == 'request_status':
        return deepcopy(shared_schema('FactValueV1')['$defs']['FactValueV1']['oneOf'][-1])
    return _expanded(_VALUE_TYPES[kind])


def _report_node(original, field=None):
    node = deepcopy(original)
    if 'anyOf' in node:
        choices = node['anyOf']
        _require(set(node) == {'anyOf'} and len(choices) == 2 and choices[1] == {'type': 'null'}, 'fact_schema_unsupported')
        result = _report_node(choices[0], field)
        result['type'] = [result['type'], 'null']
        if 'enum' in result:
            result['enum'].append(None)
        return result
    if 'allOf' in node:
        _require(original == _expanded('NumericCellV1'), 'fact_schema_unsupported')
        del node['allOf']  # Original saved-value validation owns state/value relationships.
    _require(not any(key in node for key in ('oneOf', 'if', 'then', 'else', '$ref')), 'fact_schema_unsupported')
    node.pop('minLength', None)
    node.pop('pattern', None)
    if 'type' not in node:
        values = node.get('enum', [node.get('const')])
        if all(type(value) is str for value in values):
            node['type'] = 'string'
        elif all(type(value) is int for value in values):
            node['type'] = 'integer'
        else:
            _require(False, 'fact_schema_unsupported')
    if node.get('type') == 'string' and 'enum' not in node and 'const' not in node:
        if field in {'source_ref', 'source_refs'}:
            return _identifier('source', reference=True)
        special = {'analysis_id': 'analysis', 'population_id': 'population', 'genome_population_id': 'population',
            'component_population_id': 'population', 'owner_id': 'owner', 'pointer': 'pointer', 'json_pointer': 'pointer'}
        _require(field in special or field in _IDENTIFIER_FIELDS, 'fact_schema_unsupported')
        return _identifier('bvbrc_comparative_systems_' + special.get(field, 'identifier'))
    if 'properties' in node:
        node['properties'] = {name: _report_node(value, name) for name, value in node['properties'].items()}
    if 'items' in node:
        node['items'] = _report_node(node['items'], field)
    return node


def _projected_schema(kind):
    return _object({'field_id': _identifier('bvbrc_comparative_systems_identifier'),
        'values': {'type': 'array', 'items': _report_node(_value_schema(kind))},
        'status': {'type': 'string', 'enum': ['satisfied', 'partial', 'invalid', 'unavailable']}})


def comparative_systems_fact_sources():
    return {source: {'type': 'array',
        'meaning': 'Original selected ComparativeSystems ' + kind + ' facts and their retained qualifications.',
        'report_schema': {'type': 'array', 'items': _object({
            'source_ref': _identifier('execution_result', reference=True),
            'field': _identifier('bvbrc_comparative_systems_identifier'),
            'value': _projected_schema(kind)}), 'x-source': source}}
        for source, kind in _KINDS.items()}


def parent_form_schema(selection):
    """Render the selected finite kinds using only communication keywords.

    All fields belonging to one source are delivered together by existing
    x-source semantics. Exact per-field cardinalities remain enforced by the
    authenticated provider selection; the structural bound permits partials.
    """
    selected = validate_requested_selection(selection)
    descriptors, grouped = comparative_systems_fact_sources(), {}
    for field in selected['fields']:
        grouped.setdefault(_FAMILY_MAP[field['selector']['kind']], []).append(field)
    properties = {}
    for index, (source, fields) in enumerate(grouped.items()):
        node = deepcopy(descriptors[source]['report_schema'])
        node.update(minItems=0, maxItems=len(fields))
        node['items']['properties']['value']['properties']['values'].update(
            minItems=0, maxItems=max(field['expected_cardinality'] for field in fields))
        properties['facts_' + str(index)] = node
    return validate_closed_schema(_object(properties))


def _validate_fact(kind, value):
    value = validate_shape('ProjectedFieldV1', value)
    _require(all(_Validator(_value_schema(kind)).is_valid(row) for row in value['values']), 'returned_facts_invalid')
    return value


def requested_sources(schema):
    return tuple(dict.fromkeys(node['x-source'] for node in plain(schema).get('properties', {}).values()
        if node.get('x-source') in FACT_SOURCES))


def _checked(function, value, code, path=''):
    try:
        return function(value)
    except (ValueError, KeyError, TypeError, OverflowError, RecursionError) as error:
        raise ComparativeSystemsReturnError(code, path) from error


def _contract(name, value, code, path=''):
    return _checked(lambda item: validate_contract(name, item), value, code, path)


def _saved_content(value, binding, name):
    _require((value is None) == (binding is None), 'saved_' + name + '_binding_conflict')
    if binding is not None:
        binding = _contract('ContentBinding', binding, 'saved_' + name + '_binding_conflict')
        _checked(_finite_json, value, 'saved_' + name + '_content_conflict')
        _require(binding['artifact_field'] == 'artifact_ref' and binding['sha256'] == digest(value)
                 and binding['byte_count'] == len(canonical(value).encode('utf-8')), 'saved_' + name + '_content_conflict')


def _saved_facts(body, sheet, components):
    _require(type(body) is dict and body.get('version') == RESULT_VERSION, 'publication_required')
    source = body.get('source_ref')
    _require(type(source) is str and _SOURCE_ID.fullmatch(source) is not None and body.get('reference') == source,
             'result_source_conflict')
    publication, inputs = body.get('publication'), body.get('publication_inputs')
    _require(type(publication) is dict and type(inputs) is dict, 'publication_required')
    binding = publication.get('bundle_content')
    _require(type(binding) is dict and binding.get('source_ref') == source
        and source in publication.get('result_record_refs', []) and source in body.get('record_refs', []), 'result_source_conflict')
    bundle = _contract('ArtifactBundle', body.get('bundle'), 'saved_bundle_invalid')
    _saved_content(bundle, binding, 'bundle')
    task = bundle['original_task']
    _require(task['required_application_id'] == task['native_application_id'] == 'ComparativeSystems', 'original_task_conflict')
    saved = _contract('AdapterResult', publication.get('adapter_result'), 'saved_adapter_invalid')
    _require((saved['adapter_id'], saved['adapter_version']) == (_ADAPTER_ID, _ADAPTER_VERSION), 'comparative_adapter_required')
    selector = _contract('ResultSelector', inputs.get('selector'), 'original_selector_conflict')
    selected = selector['adapter']
    _require(type(selected) is dict and all(selected[key] == saved[key] for key in ('adapter_id', 'adapter_version'))
             and _same(inputs.get('adapter'), selected), 'original_adapter_conflict')
    pin = inputs.get('adapter_implementation_sha256')
    _require(type(pin) is str and re.fullmatch(r'[0-9a-f]{64}', pin) is not None, 'original_adapter_pin_required')
    _require(type(body.get('assignment')) is dict and _same(body['assignment'].get('selector'), selector)
             and bundle['requested_selector_sha256'] == digest(selector), 'original_selector_conflict')
    parameters = _checked(validate_parameters, selected['parameters'], 'original_parameters_invalid')
    form = _checked(validate_requested_form, selector['requested_schema'], 'original_form_invalid')
    _saved_content(sheet, saved['sheet_content'], 'sheet')
    _saved_content(components, saved['components_content'], 'components')
    native = decode_comparative_publication_result(saved, sheet=sheet, components=components)
    try:
        validate_saved_comparative_systems_projection(native['sheet'], native['components'],
            **{key: native[key] for key in ('facts', 'status', 'missing_requirements', 'diagnostics')},
            requested_form=form, parameters=parameters, original_task=task, bundle=bundle)
    except (ValueError, KeyError, TypeError, OverflowError, RecursionError) as error:
        raise ComparativeSystemsReturnError('saved_projection_invalid') from error
    rows = {name: [] for name in FACT_SOURCES}
    for field, value in native['facts'].items():
        kind = form['properties'][field][MARKER]['selector']['kind']
        _require(value['field_id'] == field, 'requested_field_identity_conflict')
        rows[_FAMILY_MAP[kind]].append({'source_ref': source, 'field': field, 'value': deepcopy(value)})
    return rows


def project_comparative_systems_return_facts(body, *, requested_sources, sheet, components):
    _require(type(requested_sources) is tuple and len(requested_sources) == len(set(requested_sources))
        and all(type(name) is str and name in FACT_SOURCES for name in requested_sources), 'requested_sources_invalid')
    if not requested_sources:
        return {}
    rows = _saved_facts(body, sheet, components)
    return {name: rows[name] for name in requested_sources}


''' + cls + '''\n\n__all__ = ['FACT_SOURCES', 'IDENTIFIER_NAMESPACES', 'comparative_systems_fact_sources',
    'parent_form_schema', 'requested_sources', 'project_comparative_systems_return_facts',
    'BVBRCComparativeSystemsReturns', 'ComparativeSystemsReturnError']
''')
