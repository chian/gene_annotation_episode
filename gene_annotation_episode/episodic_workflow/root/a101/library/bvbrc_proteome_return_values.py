"""Pure original and directional GenomeComparison facts and one original failure identity."""
from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
import re
from gene_annotation_episode.episodic_workflow.root.a101.library import bvbrc_proteome_fact_contracts as contracts
from gene_annotation_episode.episodic_workflow.root.a101.library import bvbrc_proteome_directional_fact_contracts as directional
from gene_annotation_episode.episodic_workflow.root.a101.library.bvbrc_proteome_bundle_contracts import validate_parameters
from gene_annotation_episode.episodic_workflow.root.a101.library.bvbrc_proteome_bundle_projection import validate_saved_projection
from gene_annotation_episode.episodic_workflow.root.a101.library.bvbrc_appservice_contracts import _finite_json
from gene_annotation_episode.episodic_workflow.root.a101.library.bvbrc_appservice_contracts import _Validator
from gene_annotation_episode.episodic_workflow.root.a101.library.bvbrc_appservice_contracts import validate_contract
from gene_annotation_episode.episodic_workflow.root.a101.bvbrc_appservice_publication import RESULT_VERSION
from gene_annotation_episode.episodic_workflow.root.a101.communication import plain
from gene_annotation_episode.episodic_workflow.root.a101.episode_return_records import _same
from gene_annotation_episode.episodic_workflow.root.a101.execution_contracts import canonical
from gene_annotation_episode.episodic_workflow.root.a101.execution_contracts import digest

_FAMILIES = {
    'measurement': 'measurements', 'ratio': 'ratios', 'population': 'populations',
    'association': 'associations', 'selection': 'selections',
    'requirements': 'requirements', 'qualifications': 'qualifications',
    'request_status': 'request_status',
    **directional.FAMILIES,
}

FACT_SOURCES = tuple('bvbrc_proteome_' + family for family in _FAMILIES.values())

_KINDS = dict(zip(FACT_SOURCES, _FAMILIES))

_TOKEN_KINDS = {
    'track_key': 'track', 'association_key': 'association', 'association_keys': 'association',
    'inventory_key': 'inventory', 'reference_identifier': 'native_identifier',
    'subject_identifier': 'native_identifier', 'protein_key': 'protein',
    'report_key': 'report', 'field': 'requested_field', 'native_category': 'native_category',
    'document_id': 'document',
}

IDENTIFIER_NAMESPACES = tuple('bvbrc_proteome_' + kind for kind in
    (*contracts.REFERENCE_KINDS, *dict.fromkeys(_TOKEN_KINDS.values())))

_PREFIX = 'bvbrc_proteome_return_'

_ADAPTER_ID, _ADAPTER_VERSION = 'bvbrc_proteome', '1'

_ADAPTER_VERSIONS = ('1', '2')

_SOURCE_ID = re.compile(r'source_[a-f0-9]{24,64}\Z')

class ProteomeReturnError(ValueError):
    """Stable failure identity and pointer, without echoing supplied operands."""
    def __init__(self, code, path=''):
        self.code, self.path = _PREFIX + code, path
        self.diagnostics = [{'code': self.code, 'path': path}]
        super().__init__(self.code)

def _require(condition, code, path=''):
    if not condition:
        raise ProteomeReturnError(code, path)

def _object(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties),
            'additionalProperties': False}

def _identifier(namespace, *, reference=False):
    return {'type': 'string', 'format': 'reference' if reference else 'identifier',
            'x-reference-namespace': namespace}

def _report_node(original, field=None):
    """Translate only the reviewed fact grammar; retain its semantic validator.

    Communication cannot express CellFact's state/value union or native category
    literals containing spaces. Both keep their exact original semantic domains
    through mandatory fact-schema validation and saved-value equality.
    """
    node = deepcopy(original)
    if 'anyOf' in node:
        choices = node['anyOf']
        _require(set(node) == {'anyOf'} and len(choices) == 2
                 and choices[1] == {'type': 'null'}, 'fact_schema_unsupported')
        result = _report_node(choices[0], field)
        result['type'] = [result['type'], 'null']
        if 'enum' in result:
            result['enum'].append(None)
        if 'const' in result:
            result['enum'] = [result.pop('const'), None]
        return result
    if 'oneOf' in node:
        axis = directional._expanded(directional._DEFS['AxisPosition'])
        if node == axis:
            node.pop('oneOf')
            return _report_node(node, field)
        cell = contracts.fact_schemas()['measurement']['properties']['cell']
        _require(node == cell, 'fact_schema_unsupported')
        props = deepcopy(cell['oneOf'][0]['properties'])
        props['state'] = {'type': 'string', 'enum': list(contracts.CELL_STATES)}
        props['value'] = {'type': ['number', 'null']}
        return _report_node(_object(props))
    pattern = node.pop('pattern', None)
    if pattern is not None:
        if original == directional._reference('source'):
            return _identifier('source', reference=True)
        kinds = [kind for kind in contracts.REFERENCE_KINDS
                 if original == contracts.reference_schema(kind)]
        if kinds:
            _require(len(kinds) == 1, 'fact_schema_unsupported')
            return _identifier('bvbrc_proteome_' + kinds[0])
        _require((field == 'track_key' and original == contracts.TRACK)
                 or (field in {'association_key', 'association_keys'}
                     and original == contracts.ASSOCIATION), 'fact_schema_unsupported')
    if field == 'native_category' and node == contracts.enum('bi (<->)', 'uni (->)', 'unrecognized'):
        return _identifier('bvbrc_proteome_native_category')
    if 'type' not in node and ('enum' in node or 'const' in node):
        values = node.get('enum', [node.get('const')])
        _require(all(type(value) is str for value in values), 'fact_schema_unsupported')
        node['type'] = 'string'
    if node.get('type') == 'string' and 'enum' not in node and 'const' not in node:
        if node.get('format') == 'alignment_symbol':
            return node
        if field in {'native_source_refs', 'native_source_ref'}:
            return _identifier('source', reference=True)
        _require(field in _TOKEN_KINDS and original in (contracts.TEXT, contracts.TRACK, contracts.ASSOCIATION),
                 'fact_schema_unsupported')
        return _identifier('bvbrc_proteome_' + _TOKEN_KINDS[field])
    if 'properties' in node:
        node['properties'] = {name: _report_node(value, name) for name, value in node['properties'].items()}
    if 'items' in node:
        node['items'] = _report_node(node['items'], field)
    return node

@lru_cache(maxsize=1)
def _fact_source_templates() -> dict:
    schemas = _fact_schemas()
    return {source: {'type': 'array',
        'meaning': 'Recorded GenomeComparison ' + kind + ' facts from the original selected result.',
        'report_schema': {'type': 'array', 'items': _object({
            'source_ref': _identifier('execution_result', reference=True),
            'field': _identifier('bvbrc_proteome_field'),
            'value': _report_node(schemas[kind])}), 'x-source': source}}
        for source, kind in _KINDS.items()}

def proteome_fact_sources() -> dict:
    """Detach fixed grammar templates; never retain a returned fact or authority."""
    return deepcopy(_fact_source_templates())

@lru_cache(maxsize=1)
def _fact_schemas():
    return {**contracts.fact_schemas(), **directional.directional_fact_schemas()}

def _version_contracts(version):
    _require(version in _ADAPTER_VERSIONS, 'proteome_adapter_required')
    if version == '1':
        return validate_parameters, contracts.validate_requested_form, validate_saved_projection
    from gene_annotation_episode.episodic_workflow.root.a101.library.bvbrc_proteome_bundle_v2_contracts import validate_parameters_v2
    from gene_annotation_episode.episodic_workflow.root.a101.library.bvbrc_proteome_directional_projection import validate_saved_projection_v2
    return validate_parameters_v2, directional.validate_requested_form_v2, validate_saved_projection_v2

def _validate_fact(kind, value, *, selector=None):
    if kind in directional.FAMILIES:
        return directional.validate_directional_fact(kind, value, selector=selector)
    _require(_Validator(contracts.fact_schemas()[kind]).is_valid(value), 'returned_facts_invalid')
    return deepcopy(value)

def requested_sources(schema: dict) -> tuple[str, ...]:
    return tuple(dict.fromkeys(node['x-source']
        for node in plain(schema).get('properties', {}).values()
        if node.get('x-source') in FACT_SOURCES))

def _checked(function, value, code, path=''):
    try:
        return function(value)
    except (ValueError, KeyError, TypeError, OverflowError, RecursionError) as error:
        raise ProteomeReturnError(code, path) from error

def _contract(name, value, code, path=''):
    return _checked(lambda item: validate_contract(name, item), value, code, path)

def _saved_content(value, binding, name):
    _require((value is None) == (binding is None), 'saved_' + name + '_binding_conflict')
    if binding is not None:
        binding = _contract('ContentBinding', binding, 'saved_' + name + '_binding_conflict')
        _checked(_finite_json, value, 'saved_' + name + '_content_conflict')
        _require(binding['artifact_field'] == 'artifact_ref'
                 and binding['sha256'] == digest(value)
                 and binding['byte_count'] == len(canonical(value).encode('utf-8')),
                 'saved_' + name + '_content_conflict')

def _saved_facts(body, sheet, components):
    _require(type(body) is dict and body.get('version') == RESULT_VERSION, 'publication_required')
    source = body.get('source_ref')
    _require(type(source) is str and _SOURCE_ID.fullmatch(source) is not None
             and body.get('reference') == source, 'result_source_conflict')
    publication, inputs = body.get('publication'), body.get('publication_inputs')
    _require(type(publication) is dict and type(inputs) is dict, 'publication_required')
    binding = publication.get('bundle_content')
    _require(type(binding) is dict and binding.get('source_ref') == source
             and type(publication.get('result_record_refs')) is list and source in publication['result_record_refs']
             and type(body.get('record_refs')) is list and source in body['record_refs'], 'result_source_conflict')
    bundle = _contract('ArtifactBundle', body.get('bundle'), 'saved_bundle_invalid', '/bundle')
    _saved_content(bundle, binding, 'bundle')
    task = _contract('OriginalTask', bundle['original_task'], 'original_task_conflict')
    _require(task['required_application_id'] == task['native_application_id'] == 'GenomeComparison', 'original_task_conflict')
    saved = _contract('AdapterResult', publication.get('adapter_result'), 'saved_adapter_invalid')
    _require(saved['adapter_id'] == _ADAPTER_ID and saved['adapter_version'] in _ADAPTER_VERSIONS,
             'proteome_adapter_required')
    check_parameters, check_form, check_projection = _version_contracts(saved['adapter_version'])
    selector = _contract('ResultSelector', inputs.get('selector'), 'original_selector_conflict')
    selected = selector['adapter']
    _require(type(selected) is dict and all(selected[key] == saved[key] for key in ('adapter_id', 'adapter_version'))
             and _same(inputs.get('adapter'), selected), 'original_adapter_conflict')
    pin = inputs.get('adapter_implementation_sha256')
    _require(type(pin) is str and re.fullmatch(r'[0-9a-f]{64}', pin) is not None, 'original_adapter_pin_required')
    assignment = body.get('assignment')
    _require(type(assignment) is dict and _same(assignment.get('selector'), selector)
             and bundle['requested_selector_sha256'] == digest(selector), 'original_selector_conflict')
    parameters = _checked(check_parameters, selected['parameters'], 'original_parameters_invalid')
    form = _checked(check_form, selector['requested_schema'], 'original_form_invalid')
    _saved_content(sheet, saved['sheet_content'], 'sheet')
    _saved_content(components, saved['components_content'], 'components')
    facts = saved['facts']
    _require(set(facts) == set(form['properties']) or
             not facts and saved['status'] == 'invalid' and sheet is None and components is None,
             'requested_saved_facts_conflict')
    # Full ProviderSheet is the saved sheet itself. This function validates and
    # reprojects copies; it never repairs corruption with native constructors.
    try:
        check_projection(sheet, components, facts=facts, status=saved['status'],
            missing_requirements=tuple(saved['missing_requirements']), diagnostics=tuple(saved['diagnostics']),
            requested_form=form, parameters=parameters, original_task=task, bundle_sha256=binding['sha256'], bundle=bundle)
    except (ValueError, KeyError, TypeError, OverflowError, RecursionError) as error:
        raise ProteomeReturnError('saved_projection_invalid') from error
    rows = {name: [] for name in FACT_SOURCES}
    for field, node in form['properties'].items() if facts else ():
        kind = node['x-bvbrc-proteome']['kind']
        _checked(lambda value: _validate_fact(kind, value, selector=node['x-bvbrc-proteome']),
                 facts[field], 'requested_saved_facts_conflict')
        pointer = '/facts/' + field.replace('~', '~0').replace('/', '~1')
        rows['bvbrc_proteome_' + _FAMILIES[kind]].append({
            'source_ref': source, 'field': contracts.encode_reference('field', parameters['analysis_id'], pointer),
            'value': deepcopy(facts[field])})
    return rows

def project_proteome_facts(body: dict, *, requested_sources: tuple[str, ...],
                          sheet: dict | None, components: dict | None) -> dict:
    """Copy original selected facts; the caller authenticates publication custody."""
    _require(type(requested_sources) is tuple
             and all(type(name) is str and name in FACT_SOURCES for name in requested_sources)
             and len(requested_sources) == len(set(requested_sources)), 'requested_sources_invalid')
    if not requested_sources:
        return {}
    rows = _saved_facts(body, sheet, components)
    return {name: rows[name] for name in requested_sources}
