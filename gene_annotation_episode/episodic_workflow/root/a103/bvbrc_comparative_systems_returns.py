"""Original ComparativeSystems numerical facts through existing typed returns.

The provider's internal JSON Schema is rendered separately for communication.
Every value is copied from its authenticated original publication. Saved reads
perform no parsing, scientific calculation, network call or model composition.
"""
from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
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
_SOURCE_ID = re.compile(r'source_[a-f0-9]{24,64}\Z')
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


@lru_cache(maxsize=None)
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


@lru_cache(maxsize=None)
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


@lru_cache(maxsize=1)
def _fact_source_templates():
    return {source: {'type': 'array',
        'meaning': 'Original selected ComparativeSystems ' + kind + ' facts and their retained qualifications.',
        'report_schema': {'type': 'array', 'items': _object({
            'source_ref': _identifier('execution_result', reference=True),
            'field': _identifier('bvbrc_comparative_systems_identifier'),
            'value': _projected_schema(kind)}), 'x-source': source}}
        for source, kind in _KINDS.items()}


def comparative_systems_fact_sources():
    # Cache only immutable schema construction, never an authenticated fact or
    # a saved-state decision. Callers receive their own schema trees.
    return deepcopy(_fact_source_templates())


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
    native, failure_context = decode_comparative_publication_result(saved, sheet=sheet, components=components)
    try:
        validate_saved_comparative_systems_projection(native['sheet'], native['components'],
            **{key: native[key] for key in ('facts', 'status', 'missing_requirements', 'diagnostics')},
            requested_form=form, parameters=parameters, original_task=task, bundle=bundle, failure_context=failure_context)
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


class BVBRCComparativeSystemsReturns(EpisodeReturnRecords):
    _require = staticmethod(_require)
    fact_sources = staticmethod(comparative_systems_fact_sources)

    def __init__(self, execution):
        super().__init__(execution.store, execution.run_id, failure_prefix=_PREFIX)
        self.api = execution

    def _authenticate(self, context):
        self.authenticate(context, allow_unsaved=True)
        self.api.appservice.custody.authenticate(context, allow_unsaved=True)
        self._require(context.role == context.path[-1][0], 'publication_owner_conflict')

    def _owner(self, context, body):
        self._require(body.get('run_id') == self.run_id and body.get('episode_id') == context.episode_id
            and self._equal(body.get('scope'), context.scope)
            and self._equal(body.get('assignment'), context.assignment)
            and self._equal(body['publication_inputs'].get('selector'), context.assignment.get('selector')),
            'publication_owner_conflict')
        task = body['bundle']['original_task']
        pin = body['publication_inputs'].get('adapter_implementation_sha256')
        configuration = getattr(self.api, 'configuration', {}).get(task['resource_id'], {})
        selected = body['publication_inputs']['selector']['adapter']
        self._require(selected['adapter_id'] == _ADAPTER_ID and selected['adapter_version'] in _ADAPTER_VERSIONS,
                      'comparative_adapter_required')
        self._require(any(self._equal(row, {'adapter_id': _ADAPTER_ID, 'adapter_version': selected['adapter_version'],
            'implementation_sha256': pin}) for row in configuration.get('scientific_adapters', [])),
            'original_adapter_pin_conflict')

    def _possessed_sources(self, context, facts):
        schemas, seen = _fact_source_templates(), set()
        for source, rows in facts.items():
            for reference, namespace in _references(rows, schemas[source]['report_schema']):
                if namespace in {'source', 'execution_result'} and reference not in seen:
                    self._require(self.store.get(reference).get('record_type') == 'source', 'actual_source_required')
                    self.api.appservice.custody.possession(context, reference)
                    seen.add(reference)

    def facts(self, context, schema) -> dict:
        sources = requested_sources(schema)
        if not sources:
            return {}
        self._authenticate(context)
        # A published acquisition with no usable result reference still
        # supersedes previous publications. The shared helper locates only
        # named result sources; do not let that locator revive older science.
        selector = plain(context.assignment).get('selector', {})
        selected = selector.get('adapter') if type(selector) is dict else None
        if (context.role == 'results' and type(selected) is dict
                and selected.get('adapter_id') == _ADAPTER_ID and selected.get('adapter_version') in _ADAPTER_VERSIONS):
            _contract('ResultSelector', selector, 'original_selector_conflict')
            for _, outcome in reversed(list(self.api.appservice.publications.api._own_outcomes(context))):
                result = outcome.get('result') or {}
                if result.get('publication_ref') is not None:
                    if not result.get('result_record_refs'):
                        return {source: [] for source in sources}
                    break
        latest = read_latest_adapter_result(self.api.appservice.publications, context, adapter_ids=(_ADAPTER_ID,))
        if latest is None:
            return {source: [] for source in sources}
        body, sheet, components = latest
        self._owner(context, body)
        facts = project_comparative_systems_return_facts(body, requested_sources=sources, sheet=sheet, components=components)
        self._possessed_sources(context, facts)
        return facts

    def _attempts(self, context):
        self._authenticate(context)
        return self.db.execute('SELECT decision_index,contract FROM runtime_report_attempts '
            'WHERE run_id=? AND parent_episode_id=? AND form IS NOT NULL AND failure IS NULL '
            'ORDER BY decision_index', (self.run_id, context.episode_id)).fetchall()

    def _attempt(self, context, index):
        self._authenticate(context)
        # Custody authenticates full or compact forms against the original
        # decision's frozen fact catalog before returning the expanded schema.
        child, form, schema = self.api.appservice.custody._attempt(context, index)
        _checked(lambda value: validate_form(value, schema, lambda *_: True), form, 'returned_form_invalid')
        self.store.validate_scope(plain(child.scope), parent_scope=plain(context.scope))
        original_index = int(child.path[-1][1].removeprefix('child_'))
        row = self.db.execute('SELECT action FROM runtime_actions WHERE run_id=? AND episode_id=? '
            'AND decision_index=?', (self.run_id, context.episode_id, original_index)).fetchone()
        self._require(row is not None, 'original_commission_required')
        selected = json.loads(row['action'])
        original = plain(child.request)['report_contract']
        if selected.get('kind') in {'episode_child', 'child', 'job_child'}:
            self._require(self._equal(selected.get('scope'), child.scope)
                and selected.get('purpose') == original['decision'], 'original_commission_conflict')
        if self._equal(schema, original['measurements']['schema']):
            frozen = self.db.execute('SELECT form FROM runtime_forms WHERE run_id=? AND episode_id=?',
                (self.run_id, child.episode_id)).fetchone()
            self._require(frozen is not None and frozen['form'] is not None
                and self._equal(json.loads(frozen['form']), form), 'frozen_form_conflict')
        return child, form, schema

    def _original_publication(self, context, reference, sources):
        publications = self.api.appservice.publications
        body = publications.read(reference, context.scope, episode_id=context.episode_id)
        self._owner(context, body)
        saved = body['publication']['adapter_result']
        contents = [None if saved[name + '_content'] is None else publications.read_content_source(
            saved[name + '_content']['source_ref'], context.scope) for name in ('sheet', 'components')]
        return project_comparative_systems_return_facts(body, requested_sources=sources, sheet=contents[0], components=contents[1])

    def _values(self, form, schema):
        _checked(lambda value: validate_form(value, schema, lambda *_: True), form, 'returned_form_invalid')
        values, descriptors = {}, _fact_source_templates()
        for name, node in schema['properties'].items():
            source = node.get('x-source')
            if source in FACT_SOURCES:
                rows = form[name]
                # The parent's narrower grammar cannot remove original fields,
                # weaken CellFact semantics or expand the native literal domain.
                _checked(lambda value: validate_form({'value': value},
                    _object({'value': descriptors[source]['report_schema']}), lambda *_: True),
                    rows, 'returned_facts_invalid')
                self._require(source not in values or self._equal(values[source], rows), 'returned_facts_conflict')
                identities = set()
                for row in rows:
                    _checked(lambda value: _validate_fact(_KINDS[source], value), row['value'], 'returned_facts_invalid')
                    identity = row['source_ref'], row['field']
                    self._require(identity not in identities, 'duplicate_returned_field')
                    identities.add(identity)
                values[source] = rows
        return values

    def _frozen(self, context, values):
        frozen = self.db.execute('SELECT facts FROM runtime_forms WHERE run_id=? AND episode_id=?',
            (self.run_id, context.episode_id)).fetchone()
        if frozen is not None:
            saved = json.loads(frozen['facts'])
            self._require(all(source in saved and self._equal(saved[source], rows)
                for source, rows in values.items()), 'frozen_facts_conflict')

    def _validate_historical(self, context, form, schema):
        """Authenticate named original publications, never today's newest result."""
        self._authenticate(context)
        values = self._values(form, schema)
        self._frozen(context, values)
        if context.role == 'results':
            references = list(dict.fromkeys(row['source_ref'] for rows in values.values() for row in rows))
            expected = {source: [] for source in values}
            for reference in references:
                for source, rows in self._original_publication(context, reference, tuple(values)).items():
                    expected[source].extend(rows)
            self._require(self._equal(values, expected), 'returned_facts_conflict')
        elif context.role in {'annotation', 'scientific_process'}:
            received = self.received_facts(context, schema)
            self._require(all(all(any(self._equal(row, original) for original in received[source])
                for row in rows) for source, rows in values.items()), 'returned_facts_conflict')
        else:
            raise ComparativeSystemsReturnError('unsupported_return_owner')
        self._possessed_sources(context, values)

    def received_context(self, context) -> list[dict]:
        grouped, seen = {}, {}
        for attempt in self._attempts(context):
            schema = json.loads(attempt['contract']).get('measurements', {}).get('schema', {})
            if not requested_sources(schema):
                continue
            child, form, schema = self._attempt(context, attempt['decision_index'])
            self._validate_historical(child, form, schema)
            for source, values in self._values(form, schema).items():
                rows, identities = grouped.setdefault(source, []), seen.setdefault(source, set())
                for row in values:
                    key = canonical(row)
                    if key not in identities:
                        rows.append(deepcopy(row))
                        identities.add(key)
        return [{'fact_source': source, 'facts': rows} for source, rows in grouped.items()]

    def received_facts(self, context, schema) -> dict:
        sources = requested_sources(schema)
        facts = {source: [] for source in sources}
        for group in self.received_context(context) if sources else ():
            if group['fact_source'] in facts:
                facts[group['fact_source']] = group['facts']
        return facts

    def validate_received_report(self, context, form, schema) -> None:
        if not requested_sources(schema):
            return
        self._authenticate(context)
        values = self._values(plain(form), plain(schema))
        if context.role == 'results':
            expected = self.facts(context, schema)
        elif context.role in {'annotation', 'scientific_process'}:
            expected = self.received_facts(context, schema)
        else:
            raise ComparativeSystemsReturnError('unsupported_return_owner')
        self._require(self._equal(values, expected), 'returned_facts_conflict')
        self._frozen(context, values)

    def record_admission(self, context, form, schema, operation_key) -> list[str]:
        if not requested_sources(schema):
            return []
        child, saved_form, saved_schema = self._attempt(context, self._admission_index(context, operation_key))
        self._require(self._equal(form, saved_form) and self._equal(schema, saved_schema), 'admitted_form_conflict')
        self._validate_historical(child, saved_form, saved_schema)
        descriptors = _fact_source_templates()
        return list(dict.fromkeys(reference for source, rows in self._values(saved_form, saved_schema).items()
            for reference, namespace in _references(rows, descriptors[source]['report_schema'])
            if namespace in {'source', 'execution_result'}))

    @staticmethod
    def _has_reference(facts, reference, namespace):
        schemas = _fact_source_templates()
        return any(value == reference and kind == namespace for source, rows in facts.items()
            for value, kind in _references(rows, schemas[source]['report_schema']))

    def _resolve(self, context, facts, reference, namespace):
        names = ('source', 'execution_result') if namespace is None else (namespace,)
        found = any(self._has_reference(facts, reference, name) for name in names)
        if found and namespace in {None, 'source', 'execution_result'}:
            self._require(self.store.get(reference).get('record_type') == 'source', 'actual_source_required')
            self.api.appservice.custody.possession(context, reference)
        return found if namespace in IDENTIFIER_NAMESPACES or found else None

    def resolve_own(self, context, reference, namespace) -> bool | None:
        if namespace not in (*IDENTIFIER_NAMESPACES, 'source', 'execution_result', None):
            return None
        schema = (plain(context.request).get('report_contract') or {}).get('measurements', {}).get('schema', {})
        values = form_validation_value(
            (self, 'own', _binding_key(context), canonical(schema)),
            lambda: self.facts(context, schema))
        return self._resolve(context, values, reference, namespace)

    def resolve_received(self, context, reference, namespace) -> bool | None:
        if namespace not in (*IDENTIFIER_NAMESPACES, 'source', 'execution_result', None):
            return None
        values = form_validation_value(
            (self, 'received', _binding_key(context)),
            lambda: {group['fact_source']: group['facts'] for group in self.received_context(context)})
        return self._resolve(context, values, reference, namespace)


__all__ = ['FACT_SOURCES', 'IDENTIFIER_NAMESPACES', 'comparative_systems_fact_sources',
    'parent_form_schema', 'requested_sources', 'project_comparative_systems_return_facts',
    'BVBRCComparativeSystemsReturns', 'ComparativeSystemsReturnError']
