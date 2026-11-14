"""Authenticate only requested Hmmer preparation facts at each child boundary.

Preparation measurements, validations and artifact associations are operational
facts. This reader neither opens a grading sheet nor manufactures scientific
records, actions, observations or permission to read unrequested child data.
"""
from __future__ import annotations

from copy import deepcopy
import json

from .communication import plain, validate_form
from .episode_return_records import EpisodeReturnRecords
from .execution_contracts import canonical
from .form_reference_validation import _binding_key, form_validation_value
from .hmmer_preparation_result_views import (
    IDENTIFIER_NAMESPACES, preparation_fact_sources,
)


ROW_SOURCE = 'execution_hmmer_preparation_rows'
ARTIFACT_SOURCE = 'execution_hmmer_preparation_artifacts'
POPULATION_SOURCE = 'execution_hmmer_preparation_population'
FAILURE_SOURCE = 'execution_hmmer_preparation_failures'
FACT_SOURCES = (ROW_SOURCE, ARTIFACT_SOURCE, POPULATION_SOURCE, FAILURE_SOURCE)
REFERENCE_SOURCE = 'execution_hmmer_preparation_result_refs'
_GENERIC_REFERENCE_SOURCE = 'execution_result_refs'
_REFERENCE_SOURCES = (REFERENCE_SOURCE, _GENERIC_REFERENCE_SOURCE)
_REFERENCE_SCHEMA = {'type': 'array', 'uniqueItems': True, 'items': {
    'type': 'string', 'format': 'reference', 'x-reference-namespace': 'execution_result'}}
_RECEIVING_ROLES = {'annotation', 'scientific_process'}


def requested_sources(schema):
    """Provider-specific requested fields; generic refs need an actual owner."""
    return tuple(dict.fromkeys(node['x-source']
        for node in plain(schema).get('properties', {}).values()
        if node.get('x-source') in (*FACT_SOURCES, REFERENCE_SOURCE)))


def _has_generic_references(schema):
    return any(node.get('x-source') == _GENERIC_REFERENCE_SOURCE
        for node in plain(schema).get('properties', {}).values())


class NativeHmmerPreparationReturns(EpisodeReturnRecords):
    def __init__(self, owner):
        super().__init__(owner.store, owner.run_id,
            failure_prefix='native_hmmer_preparation_return_')
        self.owner, self.results = owner, owner.native_hmmer_preparation_results

    def authenticate(self, context, *, allow_unsaved=False):
        super().authenticate(context, allow_unsaved=allow_unsaved)
        self._require(context.role == context.path[-1][0], 'context_role_conflict')
        return context

    def _handles(self, context, schema):
        # Other providers also own generic execution_result_refs. Their forms
        # must remain theirs, including scientific forwarding of those refs.
        return bool(requested_sources(schema) or (_has_generic_references(schema)
            and context.role == 'results' and self.results.applies(context)))

    def _values(self, form, schema, *, generic=False):
        try:
            validate_form(form, schema, lambda *_: True)
        except ValueError as error:
            raise ValueError(self.failure_prefix + 'returned_form_invalid') from error
        descriptors, values = preparation_fact_sources(), {}
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
        return row is not None

    def _own_facts(self, context, sources):
        self.authenticate(context)
        self._require(self.results.applies(context), 'original_results_owner_required')
        actual = self.results.facts(context)
        self._require(all(source in actual for source in sources), 'original_facts_required')
        return {source: actual[source] for source in sources}

    def _attempts(self, context):
        self.authenticate(context, allow_unsaved=True)
        return self.db.execute('SELECT decision_index,child_episode_id,contract FROM runtime_report_attempts '
            'WHERE run_id=? AND parent_episode_id=? AND form IS NOT NULL AND failure IS NULL '
            'ORDER BY decision_index', (self.run_id, context.episode_id)).fetchall()

    def _attempt(self, context, index):
        child, form, schema = super()._attempt(context, index)
        try:
            self.store.validate_scope(plain(child.scope), parent_scope=plain(context.scope))
        except ValueError as error:
            raise ValueError(self.failure_prefix + 'commission_scope_conflict') from error
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
            # Scientific construction materializes its selected tool information;
            # an original results assignment is copied exactly from selection.
            if child.role == 'results':
                self._require(self._equal(selected.get('assignment'), child.assignment),
                    'commission_assignment_conflict')
        if self._equal(schema, original['measurements']['schema']):
            frozen = self.db.execute('SELECT form FROM runtime_forms WHERE run_id=? AND episode_id=?',
                (self.run_id, child.episode_id)).fetchone()
            self._require(frozen is not None and frozen['form'] is not None
                and self._equal(json.loads(frozen['form']), form), 'frozen_form_conflict')
        return child, form, schema

    def _subset(self, values, expected):
        # Frozen forms can precede later descendant deliveries. Check each
        # actual old fact without replacing it with today's expanded facts.
        # Consuming a match also rejects fabricated duplicate population rows.
        for source, rows in values.items():
            remaining = list(expected.get(source, []))
            for row in rows:
                position = next((i for i, saved in enumerate(remaining)
                    if self._equal(row, saved)), None)
                if position is None:
                    return False
                remaining.pop(position)
        return True

    def _validate_historical(self, context, form, schema):
        self.authenticate(context)
        values = self._values(form, schema, generic=context.role == 'results')
        self._frozen(context, values)
        if context.role == 'results':
            expected = self._own_facts(context, values)
            self._require(self._equal(values, expected), 'returned_facts_conflict')
        elif context.role in _RECEIVING_ROLES:
            expected = self.received_facts(context, schema)
            self._require(self._subset(values, expected), 'returned_facts_conflict')
        else:
            self._require(False, 'unsupported_return_owner')
        self._validate_references(values)
        return values

    @staticmethod
    def _reference_pairs(values):
        for source, rows in values.items():
            if source in _REFERENCE_SOURCES:
                yield from ((reference, 'execution_result') for reference in rows)
                continue
            for row in rows:
                if source == FAILURE_SOURCE:
                    yield row['handoff_ref'], 'execution_handoff'
                if row['source_ref'] is not None:
                    yield row['source_ref'], 'source'
                if source in {ROW_SOURCE, ARTIFACT_SOURCE} and row['artifact_ref'] is not None:
                    yield row['artifact_ref'], 'artifact'
                if source == ROW_SOURCE:
                    for check in row['checks']:
                        yield from ((occurrence['artifact_ref'], 'artifact')
                            for occurrence in check['occurrences'])

    @classmethod
    def _references(cls, values):
        return list(dict.fromkeys(reference for reference, _ in cls._reference_pairs(values)))

    def _validate_references(self, values):
        # A valid Store ID alone grants nothing. Values have already been
        # matched to original own facts or exact authenticated child forms.
        for reference, namespace in self._reference_pairs(values):
            try:
                kind = self.store.get(reference)['record_type']
            except (ValueError, KeyError) as error:
                raise ValueError(self.failure_prefix + 'returned_reference_missing') from error
            self._require(kind in {'source', 'artifact'} if namespace == 'execution_result'
                else kind == ('source' if namespace == 'execution_handoff' else namespace),
                'returned_reference_kind_conflict')

    def _received(self, context):
        if context.role not in _RECEIVING_ROLES:
            return {'groups': {}, 'references': [], 'handoffs': []}
        grouped, seen, references, handoffs = {}, {}, [], []
        for attempt in self._attempts(context):
            schema = json.loads(attempt['contract']).get('measurements', {}).get('schema', {})
            if not requested_sources(schema) and not _has_generic_references(schema):
                continue
            child = self.context(attempt['child_episode_id'])
            if not self._handles(child, schema):
                continue
            child, form, schema = self._attempt(context, attempt['decision_index'])
            values = self._validate_historical(child, form, schema)
            for reference, namespace in self._reference_pairs(values):
                (handoffs if namespace == 'execution_handoff' else references).append(reference)
            for source, rows in values.items():
                if source not in FACT_SOURCES:
                    continue
                group, identities = grouped.setdefault(source, []), seen.setdefault(source, set())
                for row in rows:
                    # Each complete fact includes its original source_ref.
                    # Distinct producers stay distinct even for equal bytes or
                    # counts; an identical fact redelivered by the same source
                    # supplies no additional population or selected artifact.
                    key = canonical(row)
                    if key not in identities:
                        group.append(deepcopy(row))
                        identities.add(key)
        return {'groups': grouped, 'references': list(dict.fromkeys(references)),
            'handoffs': list(dict.fromkeys(handoffs))}

    def _received_values(self, context):
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
        frozen = self._frozen(context, values)
        if context.role == 'results':
            expected = self._own_facts(context, values)
            valid = self._equal(values, expected)
        elif context.role in _RECEIVING_ROLES:
            expected = self.received_facts(context, schema)
            valid = self._subset(values, expected) if frozen else self._equal(values, expected)
        else:
            self._require(False, 'unsupported_return_owner')
        self._require(valid, 'returned_facts_conflict')
        self._validate_references(values)

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

    def resolve_received_reference_metadata(self, context, reference, namespace):
        """Reference delivery from original compact forms, without artifact reads.

        Numerical authentication remains in validate_received_report and the
        normal received-facts path. This membership check uses the original
        commission, successful delivery and frozen child form; it does not
        reinterpret source custody as delivery of a source's auxiliary files.
        """
        if context.role not in _RECEIVING_ROLES or namespace not in {
                None, 'source', 'artifact', 'execution_result', 'execution_handoff'}:
            return None
        for attempt in self._attempts(context):
            schema = json.loads(attempt['contract']).get('measurements', {}).get('schema', {})
            if not requested_sources(schema) and not _has_generic_references(schema):
                continue
            child = self.context(attempt['child_episode_id'])
            if not self._handles(child, schema):
                continue
            child, form, schema = self._attempt(context, attempt['decision_index'])
            values = self._values(form, schema, generic=child.role == 'results')
            self._frozen(child, values)
            self._validate_references(values)
            for delivered, declared_namespace in self._reference_pairs(values):
                if delivered != reference:
                    continue
                if declared_namespace == 'execution_handoff':
                    return namespace in {None, 'source', 'execution_handoff'}
                kind = self.store.get(reference)['record_type']
                return (kind in {'source', 'artifact'} if namespace in {None, 'execution_result'}
                    else kind == namespace)
        return None

    @staticmethod
    def _identifier_in_values(values, reference, namespace):
        """The existing preparation identifier grammar over retained fact rows."""
        if namespace in {'native_hmmer_preparation_failure_code', 'native_hmmer_preparation_failure_record'}:
            field = 'code' if namespace.endswith('_code') else 'record_key'
            return any(row[field] == reference for row in values.get(FAILURE_SOURCE, []))
        identifier_field = {'native_hmmer_preparation_row': 'record_key',
            'native_hmmer_preparation_name': 'name',
            'native_hmmer_preparation_accession': 'accession'}
        if namespace in identifier_field:
            if any(row[identifier_field[namespace]] == reference
                    for row in values.get(ROW_SOURCE, [])):
                return True
            return bool(namespace == 'native_hmmer_preparation_row' and any(
                reference in row['missing_record_keys']
                for row in values.get(POPULATION_SOURCE, [])))
        if namespace == 'native_hmmer_preparation_sha256':
            return any(row['sha256'] == reference
                for row in values.get(ARTIFACT_SOURCE, []))
        return None

    def frozen_reference(self, context, reference, namespace):
        """Resolve frozen literal identifiers without native or Artifact reads.

        This authenticates form/fact membership, not a Store record grant. The
        closed commission owner separately authenticates the original child,
        delivery, archived forms and its actual Source/Artifact admission.
        """
        if namespace not in IDENTIFIER_NAMESPACES:
            return None
        self.authenticate(context)
        if type(reference) is not str or not reference:
            return False
        with self.store.read_snapshot():
            row = self.db.execute('SELECT form FROM runtime_forms WHERE run_id=? AND episode_id=?',
                (self.run_id, context.episode_id)).fetchone()
            if row is None or row['form'] is None:
                return False
            contract = plain(context.request).get('report_contract')
            if contract is None:
                return False
            schema = contract['measurements']['schema']
            values = self._values(json.loads(row['form']), schema, generic=context.role == 'results')
            self._require(self._frozen(context, values), 'frozen_facts_required')
            return self._identifier_in_values(values, reference, namespace)

    def resolve_received(self, context, reference, namespace):
        if namespace not in (*IDENTIFIER_NAMESPACES, None, 'source', 'artifact', 'execution_result', 'execution_handoff'):
            return None
        received = self._received_values(context)
        if namespace in IDENTIFIER_NAMESPACES:
            return self._identifier_in_values(received['groups'], reference, namespace)
        if reference in received['handoffs']:
            return namespace in {None, 'source', 'execution_handoff'}
        if reference in received['references']:
            kind = self.store.get(reference)['record_type']
            return kind in {'source', 'artifact'} if namespace in {None, 'execution_result'} else kind == namespace
        return None


__all__ = ['NativeHmmerPreparationReturns', 'FACT_SOURCES', 'REFERENCE_SOURCE', 'requested_sources']
