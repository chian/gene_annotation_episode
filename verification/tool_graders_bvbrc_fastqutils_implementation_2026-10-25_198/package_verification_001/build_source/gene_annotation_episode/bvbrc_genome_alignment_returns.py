"""Original selected GenomeAlignment values across existing typed boundaries.

Saved-value validation is separate from custody. No native reader, source
comparison, scientific calculator or acquisition is called here. Current own
facts use the latest publication; historical returns retain their named source.
"""
from __future__ import annotations

from copy import deepcopy
import json
import re

from .bvbrc_genome_alignment_bundle_contracts import (
    FACT_SCHEMAS, MEMBER, REFERENCE_KINDS, encode_reference,
    validate_parameters, validate_requested_form,
)
from .bvbrc_genome_alignment_bundle_projection import (
    validate_projected_facts, requested_projection_status,
)
from .bvbrc_appservice_contracts import _finite_json, _Validator, validate_contract
from .bvbrc_appservice_custody import _references
from .bvbrc_appservice_publication import RESULT_VERSION
from .bvbrc_appservice_saved_results import read_latest_adapter_result
from .communication import plain, validate_form
from .episode_return_records import EpisodeReturnRecords, _same
from .execution_contracts import canonical, digest
from .form_reference_validation import _binding_key, form_validation_value


_FAMILIES = {
    'measurement': 'measurements', 'v4_segment': 'v4_segments',
    'backbone_span': 'backbone_spans', 'bbcols_interval': 'bbcols_intervals',
    'coverage_intervals': 'coverage_intervals',
    'xmfa_native_coordinate': 'xmfa_native_coordinates',
    'xmfa_source_coordinate': 'xmfa_source_coordinates',
    'xmfa_original_coordinates': 'xmfa_original_coordinates',
    'xmfa_inverse_coordinates': 'xmfa_inverse_coordinates',
    'request_status': 'request_status', 'missing_requirements': 'requirements',
    'qualifications': 'qualifications',
}
FACT_SOURCES = tuple('bvbrc_genome_alignment_' + family for family in _FAMILIES.values())
IDENTIFIER_NAMESPACES = tuple('bvbrc_genome_alignment_' + kind for kind in REFERENCE_KINDS)
_KINDS = dict(zip(FACT_SOURCES, _FAMILIES))
_PREFIX = 'bvbrc_genome_alignment_return_'
_ADAPTER_ID = 'bvbrc_genome_alignment'
_SOURCE_ID = re.compile(r'source_[a-f0-9]{24,64}\Z')


def _require(condition, code):
    if not condition:
        raise ValueError(_PREFIX + code)


def _object(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties),
        'additionalProperties': False}


def _identifier(namespace, *, reference=False):
    return {'type': 'string', 'format': 'reference' if reference else 'identifier',
        'x-reference-namespace': namespace}


def _report_node(original, field=None):
    """Expand E schemas into communication's closed, non-disjunctive grammar.

    Member namespace/index dependence and the narrower DNA symbol domain remain
    mandatory semantic checks against E's original schema on every value. The
    host grammar alone is not their validator.
    """
    node = deepcopy(original)
    if 'anyOf' in node:
        choices = node['anyOf']
        _require(set(node) == {'anyOf'} and len(choices) == 2
            and choices[1] == {'type': 'null'}, 'saved_identity_structure_invalid')
        result = _report_node(choices[0], field)
        result['type'] = [result['type'], 'null']
        if 'enum' in result:
            result['enum'].append(None)
        if 'const' in result:
            result['enum'] = [result.pop('const'), None]
        return result
    if 'oneOf' in node:
        _require(node == MEMBER, 'saved_identity_structure_invalid')
        return _object({'namespace': {'type': 'string', 'enum': [
            branch['properties']['namespace']['const'] for branch in MEMBER['oneOf']]},
            'index': {'type': 'integer', 'minimum': 0}})
    if 'prefixItems' in node:
        items = node.pop('prefixItems')
        _require(len(items) == 2 and items[0] == items[1]
            and node.get('items') is False and node.get('minItems') == node.get('maxItems') == 2,
            'saved_identity_structure_invalid')
        node['items'] = items[0]
    if 'type' not in node and ('enum' in node or 'const' in node):
        values = node.get('enum', [node.get('const')])
        _require(all(type(v) is str for v in values), 'saved_identity_structure_invalid')
        node['type'] = 'string'
    pattern = node.pop('pattern', None)
    if pattern is not None and node.get('format') != 'alignment_symbol':
        kinds = [kind for kind in REFERENCE_KINDS
            if pattern == '^bvbrc_genome_alignment_' + kind + ':[^/]+/[^/]+$']
        _require(len(kinds) == 1, 'saved_identity_structure_invalid')
        node.update(_identifier('bvbrc_genome_alignment_' + kinds[0]))
    # '+'/'-' are literal strands, not CODE identifiers. E's original enum
    # still rejects 'unknown', which the shared format also supports elsewhere.
    if node.get('format') == 'alignment_strand':
        node.pop('enum', None)
    node.pop('minLength', None)
    if 'properties' in node:
        node['properties'] = {name: _report_node(value, name)
            for name, value in node['properties'].items()}
    if 'items' in node:
        node['items'] = (_identifier('source', reference=True) if field == 'source_refs'
            else _report_node(node['items']))
    return node


def genome_alignment_fact_sources() -> dict:
    result = {}
    for source, kind in _KINDS.items():
        result[source] = {'type': 'array',
            'meaning': 'Recorded GenomeAlignment ' + kind + ' facts from the original selected result.',
            'report_schema': {'type': 'array', 'items': _object({
                'source_ref': _identifier('execution_result', reference=True),
                'field': _identifier('bvbrc_genome_alignment_field'),
                'value': _report_node(FACT_SCHEMAS[kind])}), 'x-source': source}}
    return result


def requested_sources(schema: dict) -> tuple[str, ...]:
    return tuple(dict.fromkeys(node['x-source']
        for node in plain(schema).get('properties', {}).values()
        if node.get('x-source') in FACT_SOURCES))


def _saved_content(value, binding, name):
    _require((value is None) == (binding is None), 'saved_' + name + '_binding_conflict')
    if binding is not None:
        _finite_json(value)
        _require(binding['sha256'] == digest(value)
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
    saved = validate_contract('AdapterResult', publication.get('adapter_result'))
    _require(saved['adapter_id'] == _ADAPTER_ID and saved['adapter_version'] == '1', 'genome_alignment_adapter_required')
    selector = validate_contract('ResultSelector', inputs.get('selector'))
    selected = selector['adapter']
    _require(type(selected) is dict and all(selected[k] == saved[k] for k in ('adapter_id', 'adapter_version'))
        and _same(inputs.get('adapter'), selected), 'original_adapter_conflict')
    pin = inputs.get('adapter_implementation_sha256')
    _require(type(pin) is str and re.fullmatch(r'[0-9a-f]{64}', pin) is not None, 'original_adapter_pin_required')
    assignment = body.get('assignment')
    _require(type(assignment) is dict and _same(assignment.get('selector'), selector), 'original_selector_conflict')
    parameters = validate_parameters(selected['parameters'])
    form = validate_requested_form(selector['requested_schema'])
    _saved_content(sheet, saved['sheet_content'], 'sheet')
    _saved_content(components, saved['components_content'], 'components')
    if sheet is not None:
        _require(type(sheet) is dict and type(sheet.get('data')) is dict
            and type(body.get('bundle')) is dict, 'saved_identity_structure_invalid')
        task = validate_contract('OriginalTask', body['bundle'].get('original_task'))
        _require(_same(sheet['data'].get('original_task'), task), 'original_task_conflict')
    facts = saved['facts']
    _require(set(facts) == set(form['properties']) or
        not facts and saved['status'] == 'invalid' and sheet is None and components is None,
        'requested_saved_facts_conflict')
    operands = dict(sheet=sheet, components=components,
        missing_requirements=tuple(saved['missing_requirements']), diagnostics=tuple(saved['diagnostics']),
        requested_form=form, parameters=parameters)
    # These are E's saved-only functions; no bundle consumption is invoked.
    validate_projected_facts(facts, **operands)
    _require(saved['status'] == requested_projection_status(facts, **operands), 'saved_status_conflict')
    rows = {source_name: [] for source_name in FACT_SOURCES}
    for field, node in form['properties'].items() if facts else ():
        kind = node['x-genome-alignment-fact']['kind']
        _require(_Validator(FACT_SCHEMAS[kind]).is_valid(facts[field]), 'requested_saved_facts_conflict')
        rows['bvbrc_genome_alignment_' + _FAMILIES[kind]].append({
            'source_ref': source, 'field': encode_reference('field', parameters['analysis_id'], field),
            'value': deepcopy(facts[field])})
    return rows


def project_genome_alignment_facts(body: dict, *, requested_sources: tuple[str, ...],
    sheet: dict | None, components: dict | None) -> dict:
    """Project only the original selected fields; the caller proves custody."""
    _require(type(requested_sources) is tuple
        and all(type(name) is str and name in FACT_SOURCES for name in requested_sources)
        and len(requested_sources) == len(set(requested_sources)), 'requested_sources_invalid')
    if not requested_sources:
        return {}
    rows = _saved_facts(body, sheet, components)
    return {name: rows[name] for name in requested_sources}


class BVBRCGenomeAlignmentReturns(EpisodeReturnRecords):
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

    def _possessed_sources(self, context, facts):
        schemas = genome_alignment_fact_sources()
        seen = set()
        for source, rows in facts.items():
            for reference, namespace in _references(rows, schemas[source]['report_schema']):
                if namespace in {'source', 'execution_result'} and reference not in seen:
                    self._require(self.store.get(reference).get('record_type') == 'source', 'requirement_source_required')
                    self.api.appservice.custody.possession(context, reference)
                    seen.add(reference)

    def facts(self, context, schema) -> dict:
        sources = requested_sources(schema)
        if not sources:
            return {}
        self._authenticate(context)
        latest = read_latest_adapter_result(self.api.appservice.publications, context, adapter_ids=(_ADAPTER_ID,))
        if latest is None:
            return {source: [] for source in sources}
        body, sheet, components = latest
        self._owner(context, body)
        facts = project_genome_alignment_facts(body, requested_sources=sources, sheet=sheet, components=components)
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
        validate_form(form, schema, lambda *_: True)
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
        return project_genome_alignment_facts(body, requested_sources=sources, sheet=contents[0], components=contents[1])

    def _values(self, form, schema):
        validate_form(form, schema, lambda *_: True)
        values = {}
        descriptors = genome_alignment_fact_sources()
        for name, node in schema['properties'].items():
            source = node.get('x-source')
            if source in FACT_SOURCES:
                rows = form[name]
                # A caller's narrower report grammar cannot weaken the family
                # record shape before its original scientific semantics check.
                validate_form({'value': rows}, _object({'value': descriptors[source]['report_schema']}), lambda *_: True)
                self._require(source not in values or self._equal(values[source], rows), 'returned_facts_conflict')
                for row in rows:
                    self._require(_Validator(FACT_SCHEMAS[_KINDS[source]]).is_valid(row['value']),
                        'returned_facts_conflict')
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
                original = self._original_publication(context, reference, tuple(values))
                for source, rows in original.items():
                    expected[source].extend(rows)
            # An empty frozen return contains no source or scientific assertion.
            self._require(self._equal(values, expected), 'returned_facts_conflict')
        elif context.role in {'annotation', 'scientific_process'}:
            received = self.received_facts(context, schema)
            self._require(all(all(any(self._equal(row, original) for original in received[source])
                for row in rows) for source, rows in values.items()), 'returned_facts_conflict')
        else:
            raise ValueError(_PREFIX + 'unsupported_return_owner')
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
                        rows.append(deepcopy(row)); identities.add(key)
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
            raise ValueError(_PREFIX + 'unsupported_return_owner')
        self._require(self._equal(values, expected), 'returned_facts_conflict')
        self._frozen(context, values)

    def record_admission(self, context, form, schema, operation_key) -> list[str]:
        if not requested_sources(schema):
            return []
        child, saved_form, saved_schema = self._attempt(context, self._admission_index(context, operation_key))
        self._require(self._equal(form, saved_form) and self._equal(schema, saved_schema), 'admitted_form_conflict')
        self._validate_historical(child, saved_form, saved_schema)
        return list(dict.fromkeys(reference for name, node in saved_schema['properties'].items()
            if node.get('x-source') in FACT_SOURCES for reference, namespace in _references(saved_form[name], node)
            if namespace in {'source', 'execution_result'}))

    @staticmethod
    def _has_reference(facts, reference, namespace):
        schemas = genome_alignment_fact_sources()
        return any(value == reference and kind == namespace for source, rows in facts.items()
            for value, kind in _references(rows, schemas[source]['report_schema']))

    def _resolve(self, context, facts, reference, namespace):
        names = ('source', 'execution_result') if namespace is None else (namespace,)
        found = any(self._has_reference(facts, reference, name) for name in names)
        if found and namespace in {None, 'source', 'execution_result'}:
            self._require(self.store.get(reference).get('record_type') == 'source', 'requirement_source_required')
            self.api.appservice.custody.possession(context, reference)
        return found if namespace in IDENTIFIER_NAMESPACES or found else None

    def resolve_own(self, context, reference, namespace) -> bool | None:
        if namespace not in (*IDENTIFIER_NAMESPACES, 'source', 'execution_result', None):
            return None
        schema = (plain(context.request).get('report_contract') or {}).get('measurements', {}).get('schema', {})
        facts = form_validation_value((self, 'own', _binding_key(context), canonical(schema)),
            lambda: self.facts(context, schema))
        return self._resolve(context, facts, reference, namespace)

    def resolve_received(self, context, reference, namespace) -> bool | None:
        if namespace not in (*IDENTIFIER_NAMESPACES, 'source', 'execution_result', None):
            return None
        facts = form_validation_value((self, 'received', _binding_key(context)),
            lambda: {group['fact_source']: group['facts'] for group in self.received_context(context)})
        return self._resolve(context, facts, reference, namespace)


__all__ = ['FACT_SOURCES', 'IDENTIFIER_NAMESPACES', 'genome_alignment_fact_sources',
    'requested_sources', 'project_genome_alignment_facts', 'BVBRCGenomeAlignmentReturns']
