"""Original selected FastqUtils facts through existing episode returns.

The finite native unions have a reversible closed-object communication codec.
It only adds null inactive fields; source facts and their scientific meanings
remain unchanged. Saved validation never parses or recalculates science.
"""
from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
import json
import re

from . import bvbrc_fastqutils_contracts as contracts
from .bvbrc_fastqutils_identity import field_ref
from .bvbrc_appservice_contracts import validate_contract, _finite_json
from .bvbrc_appservice_custody import _references
from .bvbrc_appservice_publication import RESULT_VERSION
from .bvbrc_appservice_saved_results import read_latest_adapter_result
from .communication import plain, validate_closed_schema, validate_form
from .episode_return_records import EpisodeReturnRecords, _same
from .execution_contracts import canonical, digest
from .form_reference_validation import _binding_key, form_validation_value

_FAMILIES = {'measurement': 'measurements', 'component': 'components',
    'category': 'categories', 'population': 'populations',
    'association': 'associations', 'requirements': 'requirements',
    'request_status': 'request_status'}
FACT_SOURCES = tuple('bvbrc_fastqutils_' + value for value in _FAMILIES.values())
_KINDS = dict(zip(FACT_SOURCES, _FAMILIES))
IDENTIFIER_NAMESPACES = ('bvbrc_fastqutils_identifier', 'bvbrc_fastqutils_field')
_PREFIX = 'bvbrc_fastqutils_return_'
_ADAPTER_ID, _ADAPTER_VERSION = 'bvbrc_fastqutils', '2'
_ADAPTER_VERSIONS = ('2',)
_SOURCE_ID = re.compile(r'source_[a-f0-9]{24,64}\Z')


class FastqUtilsReturnError(ValueError):
    def __init__(self, code, path=''):
        self.code, self.path = _PREFIX + code, path
        self.diagnostics = [{'code': self.code, 'path': path}]
        super().__init__(self.code)


def _require(condition, code, path=''):
    if not condition:
        raise FastqUtilsReturnError(code, path)


def _object(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties),
            'additionalProperties': False}


def _identifier(namespace, *, reference=False):
    return {'type': 'string', 'format': 'reference' if reference else 'identifier',
            'x-reference-namespace': namespace}


def _resolve_node(node, kind):
    if '$ref' not in node:
        return node
    name = node['$ref'].split('/')[-1]
    value = contracts._DEFS[name]
    if name in ('FactRecord', 'FactTarget'):
        matches = [branch for branch in value['oneOf']
                   if branch['properties']['kind']['const'] == kind]
        _require(len(matches) == 1, 'fact_schema_unsupported')
        return matches[0]
    return value


def _nullable(node):
    node = deepcopy(node)
    kinds = node['type'] if type(node['type']) is list else [node['type']]
    node['type'] = list(dict.fromkeys([*kinds, 'null']))
    if 'const' in node:
        node['enum'] = [node.pop('const'), None]
    elif 'enum' in node and None not in node['enum']:
        node['enum'].append(None)
    return node


def _merge_nodes(nodes):
    """Join only the reviewed disjoint object alternatives, without prose."""
    if all(_same(node, nodes[0]) for node in nodes):
        return deepcopy(nodes[0])
    if all(node.get('type') == 'object' for node in nodes):
        names = list(dict.fromkeys(name for node in nodes for name in node['properties']))
        properties = {}
        for name in names:
            choices = [node['properties'][name] for node in nodes if name in node['properties']]
            merged = _merge_nodes(choices)
            properties[name] = _nullable(merged) if len(choices) != len(nodes) else merged
        return _object(properties)
    _require(all(node.get('type') == 'string' and ('const' in node or 'enum' in node)
                 for node in nodes), 'fact_schema_unsupported')
    values = list(dict.fromkeys(value for node in nodes
                              for value in node.get('enum', [node.get('const')])))
    return {'type': 'string', 'enum': values}


def _report_node(node, kind, field=None):
    node = deepcopy(_resolve_node(node, kind))
    if 'oneOf' in node:
        _require(set(node) == {'oneOf'}, 'fact_schema_unsupported')
        return _merge_nodes([_report_node(branch, kind, field) for branch in node['oneOf']])
    if 'anyOf' in node:
        choices = node['anyOf']
        _require(set(node) == {'anyOf'} and len(choices) == 2
                 and choices[1] == {'type': 'null'}, 'fact_schema_unsupported')
        return _nullable(_report_node(choices[0], kind, field))
    # Original semantic validation owns conditional value/axis relationships.
    node.pop('allOf', None)
    node.pop('minLength', None)
    node.pop('pattern', None)
    if 'type' not in node:
        values = node.get('enum', [node.get('const')])
        _require(bool(values) and all(type(value) is str for value in values), 'fact_schema_unsupported')
        node['type'] = 'string'
    if node['type'] == 'string' and 'enum' not in node and 'const' not in node:
        if field in ('source_ref', 'source_refs'):
            return _identifier('source', reference=True)
        return _identifier('bvbrc_fastqutils_identifier')
    if 'properties' in node:
        node['properties'] = {name: _report_node(child, kind, name)
                              for name, child in node['properties'].items()}
    if 'items' in node:
        node['items'] = _report_node(node['items'], kind, field)
    return node


def _valid_branch(value, node):
    return contracts._StrictValidator({**node, '$defs': contracts._DEFS}).is_valid(value)


def _codec(value, node, kind, *, decode=False):
    node = _resolve_node(node, kind)
    if value is None:
        return None
    if 'anyOf' in node:
        return _codec(value, node['anyOf'][0], kind, decode=decode)
    if 'oneOf' in node:
        merged = _report_node(node, kind)
        if decode:
            _require(type(value) is dict and set(value) == set(merged['properties']), 'returned_facts_invalid')
            matches = []
            for branch in node['oneOf']:
                names = set(branch['properties'])
                if any(value[key] is not None for key in set(value) - names):
                    continue
                try:
                    decoded = _codec({key: value[key] for key in branch['properties']}, branch, kind, decode=True)
                    if _valid_branch(decoded, branch):
                        matches.append(decoded)
                except (ValueError, KeyError, TypeError):
                    continue
            _require(len(matches) == 1, 'returned_facts_invalid')
            return matches[0]
        branches = [branch for branch in node['oneOf'] if _valid_branch(value, branch)]
        _require(len(branches) == 1, 'returned_facts_invalid')
        encoded = _codec(value, branches[0], kind)
        return {key: encoded.get(key) for key in merged['properties']}
    if node.get('type') == 'object':
        _require(type(value) is dict and set(value) == set(node['properties']), 'returned_facts_invalid')
        return {key: _codec(value[key], child, kind, decode=decode)
                for key, child in node['properties'].items()}
    if node.get('type') == 'array':
        _require(type(value) is list, 'returned_facts_invalid')
        return [_codec(child, node['items'], kind, decode=decode) for child in value]
    return deepcopy(value)


def _native_fact(kind, value):
    value = contracts.validate_contract('ProjectedField', value)
    _require(value['selection']['target']['kind'] == kind
        and all(row['kind'] == kind for row in value['records']), 'returned_facts_invalid')
    return value


def encode_return_value(kind, value):
    _require(kind in _FAMILIES, 'returned_facts_invalid')
    native = _native_fact(kind, value)
    return _codec(native, {'$ref': '#/$defs/ProjectedField'}, kind)


def decode_return_value(kind, value):
    _require(kind in _FAMILIES, 'returned_facts_invalid')
    contracts.validate_finite_json(value)
    native = _codec(value, {'$ref': '#/$defs/ProjectedField'}, kind, decode=True)
    native = _native_fact(kind, native)
    _require(_same(value, encode_return_value(kind, native)), 'returned_facts_invalid')
    return native


def _validate_fact(kind, value):
    decode_return_value(kind, value)
    return deepcopy(value)


@lru_cache(maxsize=1)
def _fact_source_templates():
    return {source: {'type': 'array',
        'meaning': 'Original selected FastqUtils ' + kind + ' facts with exact populations and qualifications.',
        'report_schema': {'type': 'array', 'items': _object({
            'source_ref': _identifier('execution_result', reference=True),
            'field': _identifier('bvbrc_fastqutils_field'),
            'value': _report_node({'$ref': '#/$defs/ProjectedField'}, kind)}), 'x-source': source}}
        for source, kind in _KINDS.items()}


def fastqutils_fact_sources():
    return deepcopy(_fact_source_templates())


def parent_form_schema(form):
    selected = contracts.validate_contract('RequestedForm', form)
    descriptors, grouped = fastqutils_fact_sources(), {}
    for row in selected['fields']:
        source = 'bvbrc_fastqutils_' + _FAMILIES[row['selection']['target']['kind']]
        grouped.setdefault(source, []).append(row)
    properties = {}
    for index, (source, fields) in enumerate(grouped.items()):
        node = deepcopy(descriptors[source]['report_schema'])
        node.update(minItems=0, maxItems=len(fields))
        # Do not bound native rows by expected cardinality: all excess actual
        # matches must survive the return as a cardinality-mismatch result.
        properties['facts_' + str(index)] = node
    return validate_closed_schema(_object(properties))


def requested_sources(schema):
    return tuple(dict.fromkeys(node['x-source'] for node in plain(schema).get('properties', {}).values()
        if node.get('x-source') in FACT_SOURCES))


def _checked(function, value, code, path=''):
    try:
        return function(value)
    except (ValueError, KeyError, TypeError, OverflowError, RecursionError) as error:
        raise FastqUtilsReturnError(code, path) from error


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
    from .bvbrc_fastqutils_saved_codec import validate_saved_projection
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
    _require(task['required_application_id'] == task['native_application_id'] == 'FastqUtils', 'original_task_conflict')
    saved = _contract('AdapterResult', publication.get('adapter_result'), 'saved_adapter_invalid')
    _require((saved['adapter_id'], saved['adapter_version']) == (_ADAPTER_ID, _ADAPTER_VERSION), 'fastqutils_adapter_required')
    selector = _contract('ResultSelector', inputs.get('selector'), 'original_selector_conflict')
    selected = selector['adapter']
    _require(type(selected) is dict and all(selected[key] == saved[key] for key in ('adapter_id', 'adapter_version'))
        and _same(inputs.get('adapter'), selected), 'original_adapter_conflict')
    pin = inputs.get('adapter_implementation_sha256')
    _require(type(pin) is str and re.fullmatch(r'[0-9a-f]{64}', pin) is not None, 'original_adapter_pin_required')
    _require(type(body.get('assignment')) is dict and _same(body['assignment'].get('selector'), selector)
        and bundle['requested_selector_sha256'] == digest(selector), 'original_selector_conflict')
    parameters = _checked(contracts.validate_parameters, selected['parameters'], 'original_parameters_invalid')
    form = _checked(contracts.validate_requested_form, selector['requested_schema'], 'original_form_invalid')
    _saved_content(sheet, saved['sheet_content'], 'sheet')
    _saved_content(components, saved['components_content'], 'components')
    try:
        validate_saved_projection(sheet, components,
            **{key: saved[key] for key in ('facts', 'status', 'missing_requirements', 'diagnostics')},
            requested_form=selector['requested_schema'], parameters=parameters, original_task=task, bundle=bundle)
    except (ValueError, KeyError, TypeError, OverflowError, RecursionError) as error:
        raise FastqUtilsReturnError('saved_projection_invalid') from error
    rows = {name: [] for name in FACT_SOURCES}
    selections = {row['field']: row['selection'] for row in form['fields']}
    _require(set(saved['facts']) == set(selections) or
        not saved['facts'] and saved['status'] == 'invalid', 'requested_saved_facts_conflict')
    for field, value in saved['facts'].items():
        kind = selections[field]['target']['kind']
        _require(_same(value['selection'], selections[field]), 'requested_saved_facts_conflict')
        rows['bvbrc_fastqutils_' + _FAMILIES[kind]].append({'source_ref': source,
            'field': field_ref(parameters['analysis_id'], field), 'value': encode_return_value(kind, value)})
    return rows


def project_fastqutils_return_facts(body, *, requested_sources, sheet, components):
    _require(type(requested_sources) is tuple and len(requested_sources) == len(set(requested_sources))
        and all(type(name) is str and name in FACT_SOURCES for name in requested_sources), 'requested_sources_invalid')
    if not requested_sources:
        return {}
    rows = _saved_facts(body, sheet, components)
    return {name: rows[name] for name in requested_sources}


class BVBRCFastqUtilsReturns(EpisodeReturnRecords):
    _require = staticmethod(_require)
    fact_sources = staticmethod(fastqutils_fact_sources)

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
                      'fastqutils_adapter_required')
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
        facts = project_fastqutils_return_facts(body, requested_sources=sources, sheet=sheet, components=components)
        self._possessed_sources(context, facts)
        return facts

    def _attempts(self, context):
        self._authenticate(context)
        return self.db.execute('SELECT decision_index,contract FROM runtime_report_attempts '
            'WHERE run_id=? AND parent_episode_id=? AND form IS NOT NULL AND failure IS NULL '
            'ORDER BY decision_index', (self.run_id, context.episode_id)).fetchall()

    def _attempt(self, context, index):
        self._authenticate(context)
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
                and self._equal(json.loads(selected['schema_json']), original['measurements']['schema'])
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
        return project_fastqutils_return_facts(body, requested_sources=sources, sheet=contents[0], components=contents[1])

    def _values(self, form, schema):
        _checked(lambda value: validate_form(value, schema, lambda *_: True), form, 'returned_form_invalid')
        values, descriptors = {}, _fact_source_templates()
        for name, node in schema['properties'].items():
            source = node.get('x-source')
            if source in FACT_SOURCES:
                rows = form[name]
                # The parent's narrower grammar cannot remove original fields,
                # weaken ProjectedField semantics or expand the native literal domain.
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
            raise FastqUtilsReturnError('unsupported_return_owner')
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
            raise FastqUtilsReturnError('unsupported_return_owner')
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


__all__ = ["FACT_SOURCES", "IDENTIFIER_NAMESPACES", "fastqutils_fact_sources", "parent_form_schema", "requested_sources", "project_fastqutils_return_facts", "BVBRCFastqUtilsReturns", "FastqUtilsReturnError", "encode_return_value", "decode_return_value"]
