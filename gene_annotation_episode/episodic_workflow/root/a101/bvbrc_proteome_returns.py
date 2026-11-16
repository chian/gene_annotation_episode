"""Original selected GenomeComparison facts across existing typed boundaries.

Saved-value validation is separate from publication custody. No native parser,
sheet constructor, calculator, acquisition or execution is called here. Current
own facts use the latest publication; admitted history keeps its named source.
"""
from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
import json
import re

from .library import bvbrc_proteome_fact_contracts as contracts
from .library import bvbrc_proteome_directional_fact_contracts as directional
from .library.bvbrc_proteome_bundle_contracts import validate_parameters
from .library.bvbrc_proteome_bundle_projection import validate_saved_projection
from .library.bvbrc_appservice_contracts import _finite_json, _Validator, validate_contract
from .bvbrc_appservice_custody import _references
from .bvbrc_appservice_publication import RESULT_VERSION
from .bvbrc_appservice_saved_results import read_latest_adapter_result
from .communication import plain, validate_form
from .episode_return_records import EpisodeReturnRecords, _same
from .execution_contracts import canonical, digest
from .form_reference_validation import _binding_key, form_validation_value
from gene_annotation_episode.episodic_workflow.root.a101.library.bvbrc_proteome_return_values import FACT_SOURCES, IDENTIFIER_NAMESPACES, ProteomeReturnError, _ADAPTER_ID, _ADAPTER_VERSIONS, _KINDS, _PREFIX, _checked, _contract, _fact_source_templates, _object, _validate_fact, project_proteome_facts, proteome_fact_sources, _require, requested_sources


# These are original native tokens, not newly invented Store records. Their
# availability is established only by the exact authenticated requested facts.


































class BVBRCProteomeReturns(EpisodeReturnRecords):
    _require = staticmethod(_require)
    fact_sources = staticmethod(proteome_fact_sources)

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
        configuration = getattr(self.api, 'configuration', {}).get(task['resource_id'], {})
        selected = body['publication_inputs']['selector']['adapter']
        self._require(selected['adapter_id'] == _ADAPTER_ID and selected['adapter_version'] in _ADAPTER_VERSIONS,
                      'proteome_adapter_required')
        self._require(any(self._equal(row, {'adapter_id': _ADAPTER_ID, 'adapter_version': selected['adapter_version']}) for row in configuration.get('scientific_adapters', [])),
            'original_adapter_pin_conflict')

    def _possessed_sources(self, context, facts):
        schemas, seen = proteome_fact_sources(), set()
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
        facts = project_proteome_facts(body, requested_sources=sources, sheet=sheet, components=components)
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
        return project_proteome_facts(body, requested_sources=sources, sheet=contents[0], components=contents[1])

    def _values(self, form, schema):
        _checked(lambda value: validate_form(value, schema, lambda *_: True), form, 'returned_form_invalid')
        values, descriptors = {}, proteome_fact_sources()
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
            raise ProteomeReturnError('unsupported_return_owner')
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
            raise ProteomeReturnError('unsupported_return_owner')
        self._require(self._equal(values, expected), 'returned_facts_conflict')
        self._frozen(context, values)

    def record_admission(self, context, form, schema, operation_key) -> list[str]:
        if not requested_sources(schema):
            return []
        child, saved_form, saved_schema = self._attempt(context, self._admission_index(context, operation_key))
        self._require(self._equal(form, saved_form) and self._equal(schema, saved_schema), 'admitted_form_conflict')
        self._validate_historical(child, saved_form, saved_schema)
        descriptors = proteome_fact_sources()
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


__all__ = ['BVBRCProteomeReturns']
