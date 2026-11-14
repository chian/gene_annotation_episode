"""Only requested Infernal facts cross each authenticated immediate-child form.

This module reads saved publications and original runtime returns. It never
parses an output, recalculates a score, acquires data or creates an observation.
Possession of a source does not expose unrequested numerical rows to an ancestor.
"""
from __future__ import annotations

from copy import deepcopy
import json

from .communication import plain, validate_form
from .episode_return_records import EpisodeReturnRecords
from .execution_contracts import canonical
from .form_reference_validation import _binding_key, form_validation_value
from .infernal_native_result_views import (FAMILY_SOURCES, IDENTIFIER_NAMESPACES,
    native_infernal_fact_sources)


FACT_SOURCES = tuple(FAMILY_SOURCES.values())
REFERENCE_SOURCE = 'execution_infernal_result_refs'
_GENERIC_REFERENCE_SOURCE = 'execution_result_refs'
_REFERENCE_SOURCES = (REFERENCE_SOURCE, _GENERIC_REFERENCE_SOURCE)
_REFERENCE_SCHEMA = {'type': 'array', 'uniqueItems': True, 'items': {
    'type': 'string', 'format': 'reference', 'x-reference-namespace': 'execution_result'}}


def requested_sources(schema):
    return tuple(dict.fromkeys(node['x-source']
        for node in plain(schema).get('properties', {}).values()
        if node.get('x-source') in (*FACT_SOURCES, REFERENCE_SOURCE)))


def _has_generic_references(schema):
    return any(node.get('x-source') == _GENERIC_REFERENCE_SOURCE
        for node in plain(schema).get('properties', {}).values())


class NativeInfernalReturns(EpisodeReturnRecords):
    def __init__(self, owner):
        super().__init__(owner.store, owner.run_id, failure_prefix='native_infernal_return_')
        self.owner, self.results = owner, owner.native_infernal_results

    def authenticate(self, context, *, allow_unsaved=False):
        super().authenticate(context, allow_unsaved=allow_unsaved)
        self._require(context.role == context.path[-1][0], 'context_role_conflict')
        return context

    def _handles(self, context, schema):
        # The generic source belongs to many providers. Only an actual Infernal
        # results owner gives it Infernal meaning. Scientific forwarding uses
        # the separate provider-specific source, never another provider's refs.
        return bool(requested_sources(schema) or (_has_generic_references(schema)
            and context.role == 'results' and self.results.applies(context)))

    def _values(self, form, schema, *, generic=False):
        try:
            validate_form(form, schema, lambda *_: True)
        except ValueError as error:
            raise ValueError(self.failure_prefix + 'returned_form_invalid') from error
        descriptors, values = native_infernal_fact_sources(), {}
        for name, node in plain(schema)['properties'].items():
            source = node.get('x-source')
            if source not in (*FACT_SOURCES, REFERENCE_SOURCE) and not (
                    generic and source == _GENERIC_REFERENCE_SOURCE):
                continue
            rows = plain(form[name])
            expected = (_REFERENCE_SCHEMA if source in _REFERENCE_SOURCES
                else descriptors[source]['report_schema'])
            try:
                validate_form({'rows': rows}, {'type': 'object', 'additionalProperties': False,
                    'properties': {'rows': expected}, 'required': ['rows']}, lambda *_: True)
            except ValueError as error:
                raise ValueError(self.failure_prefix + 'returned_facts_invalid') from error
            self._require(source not in values or self._equal(values[source], rows), 'conflicting_fields')
            values[source] = rows
        return values

    def _frozen(self, context, values):
        row = self.db.execute('SELECT facts FROM runtime_forms WHERE run_id=? AND episode_id=?',
            (self.run_id, context.episode_id)).fetchone()
        if row is not None:
            facts = json.loads(row['facts'])
            self._require(all(source in facts and self._equal(facts[source], value)
                for source, value in values.items()), 'frozen_facts_conflict')

    def _own_facts(self, context, sources):
        self.authenticate(context)
        self._require(self.results.applies(context), 'original_results_owner_required')
        actual = self.results.facts(context)
        return {source: actual[_GENERIC_REFERENCE_SOURCE if source == REFERENCE_SOURCE else source]
                for source in sources}

    def _attempts(self, context):
        self.authenticate(context, allow_unsaved=True)
        return self.db.execute('SELECT decision_index,child_episode_id,contract FROM runtime_report_attempts '
            'WHERE run_id=? AND parent_episode_id=? AND form IS NOT NULL AND failure IS NULL '
            'ORDER BY decision_index', (self.run_id, context.episode_id)).fetchall()

    def _attempt(self, context, index):
        child, form, schema = super()._attempt(context, index)
        self.store.validate_scope(plain(child.scope), parent_scope=plain(context.scope))
        original = plain(child.request)['report_contract']
        original_index = int(child.path[-1][1].removeprefix('child_'))
        row = self.db.execute('SELECT action FROM runtime_actions WHERE run_id=? AND episode_id=? '
            'AND decision_index=?', (self.run_id, context.episode_id, original_index)).fetchone()
        self._require(row is not None, 'original_commission_required')
        selected = json.loads(row['action'])
        self._require(selected.get('kind') in {'episode_child', 'child', 'job_child'}
            or selected.get('kind') == 'tool' and selected.get('tool') == 'process.revise',
            'original_commission_conflict')
        if selected.get('kind') in {'episode_child', 'child', 'job_child'}:
            self._require(self._equal(selected.get('scope'), child.scope)
                and self._equal(json.loads(selected['schema_json']), original['measurements']['schema'])
                and selected.get('purpose') == original['decision'], 'original_commission_conflict')
            if selected.get('kind') in {'episode_child', 'job_child'}:
                self._require(selected.get('role') == child.role, 'commission_role_conflict')
            # Scientific construction materializes selected tool information in
            # the immutable assignment. Results assignments are copied exactly.
            if child.role == 'results':
                self._require(self._equal(selected.get('assignment'), child.assignment),
                    'commission_assignment_conflict')
        if self._equal(schema, original['measurements']['schema']):
            frozen = self.db.execute('SELECT form FROM runtime_forms WHERE run_id=? AND episode_id=?',
                (self.run_id, child.episode_id)).fetchone()
            self._require(frozen is not None and frozen['form'] is not None
                and self._equal(json.loads(frozen['form']), form), 'frozen_form_conflict')
        return child, form, schema

    def _validate_historical(self, context, form, schema):
        self.authenticate(context)
        values = self._values(form, schema, generic=context.role == 'results')
        self._frozen(context, values)
        if context.role == 'results':
            expected = self._own_facts(context, values)
            self._require(self._equal(values, expected), 'returned_facts_conflict')
        elif context.role in {'annotation', 'scientific_process'}:
            expected = self.received_facts(context, schema)
            self._require(all(all(any(self._equal(row, saved) for saved in expected[source])
                for row in rows) for source, rows in values.items()), 'returned_facts_conflict')
        else:
            self._require(False, 'unsupported_return_owner')
        return values

    @staticmethod
    def _references(values):
        references = []
        for source, rows in values.items():
            if source in _REFERENCE_SOURCES:
                references.extend(rows)
            else:
                references.extend(reference for row in rows for reference in
                    [row['source_ref'], row['observation_ref'], *row['reference_refs']]
                    if reference is not None)
        return list(dict.fromkeys(references))

    def _received(self, context):
        if context.role not in {'annotation', 'scientific_process'}:
            return {'groups': {}, 'references': []}
        grouped, seen, references = {}, {}, []
        for attempt in self._attempts(context):
            schema = json.loads(attempt['contract']).get('measurements', {}).get('schema', {})
            if not requested_sources(schema) and not _has_generic_references(schema):
                continue
            # Inspect only the owner of a generic reference form before using
            # its source. Other providers keep their own return implementation.
            child = self.context(attempt['child_episode_id'])
            if not self._handles(child, schema):
                continue
            child, form, schema = self._attempt(context, attempt['decision_index'])
            values = self._validate_historical(child, form, schema)
            references.extend(self._references(values))
            for source, rows in values.items():
                if source not in FACT_SOURCES:
                    continue
                group, identities = grouped.setdefault(source, []), seen.setdefault(source, set())
                for row in rows:
                    key = canonical(row)
                    if key not in identities:
                        group.append(deepcopy(row))
                        identities.add(key)
        return {'groups': grouped, 'references': list(dict.fromkeys(references))}

    def _received_values(self, context):
        # Existing synchronous form frames discard this authenticated snapshot
        # at the end of validation. No successful verdict survives into a later
        # call, and callers cannot mutate the private snapshot.
        return form_validation_value((self, 'received', _binding_key(context)),
            lambda: self._received(context))

    def received_context(self, context):
        return [{'fact_source': source, 'facts': rows}
                for source, rows in self._received_values(context)['groups'].items()]

    def received_facts(self, context, schema):
        sources = requested_sources(schema)
        result = {source: [] for source in sources}
        if sources:
            received = self._received_values(context)
            for source in sources:
                result[source] = (received['references'] if source == REFERENCE_SOURCE
                    else received['groups'].get(source, []))
        return result

    def validate_received_report(self, context, form, schema):
        if not self._handles(context, schema):
            return
        self.authenticate(context, allow_unsaved=True)
        values = self._values(form, schema, generic=context.role == 'results')
        expected = (self._own_facts(context, values) if context.role == 'results'
                    else self.received_facts(context, schema))
        self._require(self._equal(values, expected), 'returned_facts_conflict')
        self._frozen(context, values)

    def record_admission(self, context, form, schema, operation_key):
        if not requested_sources(schema) and not _has_generic_references(schema):
            return []
        index = self._admission_index(context, operation_key)
        if not requested_sources(schema):
            row = self.db.execute('SELECT child_episode_id FROM runtime_report_attempts '
                'WHERE run_id=? AND parent_episode_id=? AND decision_index=?',
                (self.run_id, context.episode_id, index)).fetchone()
            self._require(row is not None, 'successful_return_required')
            if not self._handles(self.context(row['child_episode_id']), schema):
                return []
        child, saved, declared = self._attempt(context, index)
        self._require(self._equal(form, saved) and self._equal(schema, declared), 'admitted_form_conflict')
        return self._references(self._validate_historical(child, saved, declared))

    def resolve_received(self, context, reference, namespace):
        if namespace not in (*IDENTIFIER_NAMESPACES, None, 'source', 'execution_result'):
            return None
        received = self._received_values(context)
        identifier_field = {'native_infernal_row': 'record_key',
            'native_infernal_sequence_name': 'sequence_name', 'native_infernal_model_name': 'model_name'}
        if namespace in identifier_field:
            for rows in received['groups'].values():
                for row in rows:
                    if row[identifier_field[namespace]] == reference:
                        return True
            return False
        if reference in received['references']:
            return namespace != 'source' or self.store.get(reference)['record_type'] == 'source'
        return None


__all__ = ['NativeInfernalReturns', 'FACT_SOURCES', 'REFERENCE_SOURCE', 'requested_sources']
