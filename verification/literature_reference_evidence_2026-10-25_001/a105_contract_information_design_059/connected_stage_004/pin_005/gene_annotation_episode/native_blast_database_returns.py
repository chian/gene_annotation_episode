"""Original immediate-child authority for selected database numerical returns.

Frozen row values are checked against the original results owner on every
boundary. A source in Store, or another child's receipt, is not row authority.
"""
from __future__ import annotations

from copy import deepcopy
import json

from .communication import plain, validate_form
from .episode_return_records import EpisodeReturnRecords
from .execution_contracts import canonical
from .form_reference_validation import _binding_key, form_validation_value
from .native_blast_database_result_views import native_blast_database_fact_sources
from .native_blast_database_results import (ACQUISITION_SOURCE, FAILURE_SOURCE, IDENTIFIER_NAMESPACES,
    REFERENCE_SOURCE, schema_references)

FACT_SOURCES = tuple(native_blast_database_fact_sources())
_GENERIC = 'execution_result_refs'
_REFERENCE_SOURCES = (REFERENCE_SOURCE, _GENERIC)


def requested_sources(schema):
    return tuple(dict.fromkeys(node['x-source'] for node in plain(schema).get('properties', {}).values()
        if node.get('x-source') in FACT_SOURCES))


def _generic(schema):
    return any(node.get('x-source') == _GENERIC for node in plain(schema).get('properties', {}).values())


class NativeBLASTDatabaseReturns(EpisodeReturnRecords):
    def __init__(self, owner):
        super().__init__(owner.store, owner.run_id, failure_prefix='native_blast_database_return_')
        self.owner, self.results = owner, owner.native_blast_database_results

    def _handles(self, context, schema):
        return bool(requested_sources(schema) or _generic(schema) and self.results.applies(context))

    def _values(self, form, schema, *, generic=False):
        validate_form(form, schema, lambda *_: True)
        descriptors, values = native_blast_database_fact_sources(), {}
        for name, node in plain(schema).get('properties', {}).items():
            source = node.get('x-source')
            if source not in FACT_SOURCES and not (generic and source == _GENERIC):
                continue
            expected = descriptors[REFERENCE_SOURCE if source == _GENERIC else source]['report_schema']
            value = plain(form[name])
            validate_form({'value': value}, {'type': 'object', 'properties': {'value': expected},
                'required': ['value'], 'additionalProperties': False}, lambda *_: True)
            self._require(source not in values or self._equal(values[source], value), 'conflicting_fields')
            values[source] = value
        return values

    def _frozen(self, context, values):
        row = self.db.execute('SELECT facts FROM runtime_forms WHERE run_id=? AND episode_id=?',
            (self.run_id, context.episode_id)).fetchone()
        if row is not None:
            saved = json.loads(row['facts'])
            self._require(all(source in saved and self._equal(value, saved[source]) for source, value in values.items()), 'frozen_facts_conflict')

    def _own_facts(self, context, sources):
        self.authenticate(context)
        self._require(self.results.applies(context), 'original_results_owner_required')
        actual = self.results.facts(context)
        return {source: actual[source] for source in sources}

    def _attempt(self, context, index):
        child, form, schema = super()._attempt(context, index)
        self.store.validate_scope(plain(child.scope), parent_scope=plain(context.scope))
        original = plain(child.request)['report_contract']
        original_index = int(child.path[-1][1].removeprefix('child_'))
        row = self.db.execute('SELECT action FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?',
            (self.run_id, context.episode_id, original_index)).fetchone()
        self._require(row is not None, 'original_commission_required')
        selected = json.loads(row['action'])
        self._require(selected.get('kind') in {'child', 'episode_child', 'job_child'}
            or selected.get('kind') == 'tool' and selected.get('tool') == 'process.revise', 'original_commission_conflict')
        if selected.get('kind') in {'child', 'episode_child', 'job_child'}:
            self._require(self._equal(selected.get('scope'), child.scope)
                and self._equal(json.loads(selected['schema_json']), original['measurements']['schema'])
                and selected.get('purpose') == original['decision'], 'original_commission_conflict')
            if selected.get('kind') in {'episode_child', 'job_child'}:
                self._require(selected.get('role') == child.role, 'commission_role_conflict')
            if child.role == 'results':
                self._require(self._equal(selected.get('assignment'), child.assignment), 'commission_assignment_conflict')
        if self._equal(schema, original['measurements']['schema']):
            row = self.db.execute('SELECT form FROM runtime_forms WHERE run_id=? AND episode_id=?',
                (self.run_id, child.episode_id)).fetchone()
            self._require(row is not None and row['form'] is not None and self._equal(json.loads(row['form']), form), 'frozen_form_conflict')
        return child, form, schema

    def _validate_historical(self, context, form, schema):
        self.authenticate(context)
        values = self._values(form, schema, generic=context.role == 'results')
        self._frozen(context, values)
        if context.role == 'results':
            self._require(self._equal(values, self._own_facts(context, values)), 'returned_facts_conflict')
        elif context.role in {'annotation', 'scientific_process'}:
            expected = self.received_facts(context, schema)
            for source, value in values.items():
                self._require(self._equal(value, expected[source]) if source == ACQUISITION_SOURCE else
                    all(any(self._equal(row, saved) for saved in expected[source]) for row in value), 'returned_facts_conflict')
        else:
            self._require(False, 'unsupported_return_owner')
        return values

    @staticmethod
    def _references(values):
        descriptors, result = native_blast_database_fact_sources(), []
        for source, value in values.items():
            schema = descriptors[REFERENCE_SOURCE if source == _GENERIC else source]['report_schema']
            result.extend(ref for ref, _, kind in schema_references(value, schema) if kind == 'reference')
        return list(dict.fromkeys(result))

    def _received(self, context):
        self.authenticate(context, allow_unsaved=True)
        if context.role not in {'annotation', 'scientific_process'}:
            return {'groups': {}, 'references': []}
        groups, seen, references = {}, {}, []
        attempts = self.db.execute('SELECT decision_index,child_episode_id,contract FROM runtime_report_attempts '
            'WHERE run_id=? AND parent_episode_id=? AND form IS NOT NULL AND failure IS NULL ORDER BY decision_index',
            (self.run_id, context.episode_id))
        for row in attempts:
            schema = json.loads(row['contract']).get('measurements', {}).get('schema', {})
            if not requested_sources(schema) and not _generic(schema):
                continue
            child = self.context(row['child_episode_id'])
            if not self._handles(child, schema):
                continue
            child, form, schema = self._attempt(context, row['decision_index'])
            values = self._validate_historical(child, form, schema)
            references.extend(self._references(values))
            for source, value in values.items():
                source = REFERENCE_SOURCE if source == _GENERIC else source
                if source == ACQUISITION_SOURCE:
                    # This is the most recently received actual acquisition
                    # object, never an AND/OR aggregate invented by the host.
                    groups[source] = deepcopy(value)
                    continue
                items, identities = groups.setdefault(source, []), seen.setdefault(source, set())
                for item in value:
                    key = canonical(item)
                    if key not in identities:
                        items.append(deepcopy(item)); identities.add(key)
        return {'groups': groups, 'references': list(dict.fromkeys(references))}

    def _received_values(self, context):
        return form_validation_value((self, 'received', _binding_key(context)), lambda: self._received(context))

    def received_context(self, context):
        return [{'fact_source': source, 'facts': value} for source, value in self._received_values(context)['groups'].items()]

    def received_facts(self, context, schema):
        sources = requested_sources(schema)
        if not sources:
            return {}
        received = self._received_values(context)
        values = {}
        for source in sources:
            if source == ACQUISITION_SOURCE:
                self._require(source in received['groups'], 'acquisition_not_received')
            values[source] = deepcopy(received['groups'].get(source, []))
        return values

    def validate_received_report(self, context, form, schema):
        if not self._handles(context, schema):
            return
        self.authenticate(context, allow_unsaved=True)
        values = self._values(form, schema, generic=context.role == 'results')
        expected = self._own_facts(context, values) if context.role == 'results' else self.received_facts(context, schema)
        self._require(self._equal(values, expected), 'returned_facts_conflict')
        self._frozen(context, values)

    def record_admission(self, context, form, schema, operation_key):
        if not requested_sources(schema) and not _generic(schema):
            return []
        index = self._admission_index(context, operation_key)
        if not requested_sources(schema):
            row = self.db.execute('SELECT child_episode_id FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? AND decision_index=?',
                (self.run_id, context.episode_id, index)).fetchone()
            self._require(row is not None, 'successful_return_required')
            if not self._handles(self.context(row['child_episode_id']), schema):
                return []
        child, saved, declared = self._attempt(context, index)
        self._require(self._equal(form, saved) and self._equal(schema, declared), 'admitted_form_conflict')
        return self._references(self._validate_historical(child, saved, declared))

    def resolve_received(self, context, reference, namespace):
        if namespace not in (*IDENTIFIER_NAMESPACES, None, 'source', 'execution_result', 'subject'):
            return None
        received = self._received_values(context)
        if namespace in IDENTIFIER_NAMESPACES:
            descriptors = native_blast_database_fact_sources()
            return any(ref == reference and ns == namespace for source, rows in received['groups'].items()
                for ref, ns, kind in schema_references(rows, descriptors[source]['report_schema']) if kind == 'identifier')
        if reference in received['references']:
            kind = self.store.get(reference)['record_type']
            return kind == 'source' if namespace == 'source' else kind in {'input', 'feature', 'product', 'read_subject'} if namespace == 'subject' else True
        try:
            record = self.store.get(reference)
            source = record if record['record_type'] == 'source' else self.store.get(record['source_ref']) if record.get('source_ref') else {}
            if source.get('provider') == 'episode.execution_result' and source.get('version') == 'native_blast_database_bundle_v1':
                return False
        except (ValueError, KeyError):
            pass
        return None


__all__ = ['NativeBLASTDatabaseReturns', 'FACT_SOURCES', 'REFERENCE_SOURCE', 'requested_sources']
