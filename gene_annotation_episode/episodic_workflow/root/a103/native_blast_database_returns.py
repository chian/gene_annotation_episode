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
from .native_blast_database_result_views import native_blast_database_fact_sources, SAVED_INPUT_SOURCE, _SAVED_INPUT_SCHEMA
from .native_blast_database_result_publication import _known, _original_commission
from .domain import ContractError, validate_schema
from .native_blast_database_results import (ACQUISITION_SOURCE, FAILURE_SOURCE, IDENTIFIER_NAMESPACES,
    REFERENCE_SOURCE, schema_references)

FACT_SOURCES = tuple(native_blast_database_fact_sources())
_ROW_SOURCES = frozenset(source for source in FACT_SOURCES if source.endswith('_rows'))
_GENERIC = 'execution_result_refs'
_REFERENCE_SOURCES = (REFERENCE_SOURCE, _GENERIC)
_HSP_PUBLICATION = ('observation_ref', 'subject_ref', 'reference_refs', 'publication_status')


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
                if source in _ROW_SOURCES:
                    # A closed ancestor keeps its original projection when a
                    # later child supplies more cells for the same frozen row.
                    valid = all(any(self._row_subset(row, saved) for saved in expected[source]) for row in value)
                else:
                    valid = (self._equal(value, expected[source]) if source == ACQUISITION_SOURCE else
                        all(any(self._equal(row, saved) for saved in expected[source]) for row in value))
                self._require(valid, 'returned_facts_conflict')
        else:
            self._require(False, 'unsupported_return_owner')
        return values

    @staticmethod
    def _row_context(row):
        return {key: value for key, value in row.items() if key not in {'measurements', 'booleans'}}

    def _row_subset(self, row, received):
        if not self._row_context_subset(row, received):
            return False
        return all(all(any(self._equal(cell, saved) for saved in received[kind]) for cell in row[kind])
            for kind in ('measurements', 'booleans'))

    def _row_context_subset(self, row, received):
        left, right = self._row_context(row), self._row_context(received)
        if row.get('family') != 'hsp' or received.get('family') != 'hsp':
            return self._equal(left, right)
        # Authority is checked against each child's original frozen facts
        # before this union. Only an empty HSP publication association adds no
        # information; scientific context and generation remain exact.
        for value in (row, received):
            if value['publication_status'] == 'source_only' and any((
                    value['observation_ref'] is not None, value['subject_ref'] is not None, value['reference_refs'] != [])):
                return False
        if not self._equal({k: v for k, v in left.items() if k not in _HSP_PUBLICATION},
                {k: v for k, v in right.items() if k not in _HSP_PUBLICATION}):
            return False
        if self._equal({k: row[k] for k in _HSP_PUBLICATION}, {k: received[k] for k in _HSP_PUBLICATION}):
            return True
        return (row['publication_status'] == 'source_only' and received['publication_status'] == 'published'
            and received['observation_ref'] is not None and received['subject_ref'] is not None)

    def _merge_received_row(self, accumulated, row):
        forward = self._row_context_subset(accumulated, row)
        backward = self._row_context_subset(row, accumulated)
        self._require(forward or backward, 'received_row_context_conflict')
        for kind in ('measurements', 'booleans'):
            cells = {cell['name']: cell for cell in accumulated[kind]}
            for cell in row[kind]:
                if cell['name'] in cells:
                    self._require(self._equal(cell, cells[cell['name']]), 'received_cell_conflict')
                else:
                    copied = deepcopy(cell)
                    accumulated[kind].append(copied)
                    cells[cell['name']] = copied
        if forward and not backward:
            for field in _HSP_PUBLICATION:
                accumulated[field] = deepcopy(row[field])

    @staticmethod
    def _references(values):
        descriptors, result = native_blast_database_fact_sources(), []
        for source, value in values.items():
            schema = descriptors[REFERENCE_SOURCE if source == _GENERIC else source]['report_schema']
            result.extend(ref for ref, _, kind in schema_references(value, schema) if kind == 'reference')
        return list(dict.fromkeys(result))

    def _received(self, context, *, before_index=None):
        self.authenticate(context, allow_unsaved=True)
        if context.role not in {'annotation', 'scientific_process'}:
            return {'groups': {}, 'references': []}
        groups, seen, row_groups, references, authorized = {}, {}, {}, [], set()
        descriptors = native_blast_database_fact_sources()
        attempts = self.db.execute('SELECT decision_index,child_episode_id,contract FROM runtime_report_attempts '
            'WHERE run_id=? AND parent_episode_id=? AND form IS NOT NULL AND failure IS NULL ORDER BY decision_index',
            (self.run_id, context.episode_id))
        for row in attempts:
            if before_index is not None and row['decision_index'] >= before_index:
                continue
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
                authorized.update((ref, namespace) for ref, namespace, _ in
                    schema_references(value, descriptors[source]['report_schema']))
                if source == ACQUISITION_SOURCE:
                    # This is the most recently received actual acquisition
                    # object, never an AND/OR aggregate invented by the host.
                    groups[source] = deepcopy(value)
                    continue
                if source in _ROW_SOURCES:
                    items, by_identity = groups.setdefault(source, []), row_groups.setdefault(source, {})
                    for item in value:
                        identity = (item['calculation_id'], item['record_key'])
                        if identity in by_identity:
                            self._merge_received_row(by_identity[identity], item)
                        else:
                            copied = deepcopy(item)
                            items.append(copied)
                            by_identity[identity] = copied
                    continue
                items, identities = groups.setdefault(source, []), seen.setdefault(source, set())
                for item in value:
                    key = canonical(item)
                    if key not in identities:
                        items.append(deepcopy(item)); identities.add(key)
        for source, rows in groups.items():
            if source in _ROW_SOURCES:
                validate_form({'rows': rows}, {'type': 'object', 'properties': {
                    'rows': descriptors[source]['report_schema']}, 'required': ['rows'], 'additionalProperties': False},
                    lambda ref, namespace: (ref, namespace) in authorized)
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
        if namespace not in (*IDENTIFIER_NAMESPACES, None, 'source', 'artifact', 'execution_result', 'subject'):
            return None
        received = self._received_values(context)
        if namespace in IDENTIFIER_NAMESPACES:
            descriptors = native_blast_database_fact_sources()
            return any(ref == reference and ns == namespace for source, rows in received['groups'].items()
                for ref, ns, kind in schema_references(rows, descriptors[source]['report_schema']) if kind == 'identifier')
        if reference in received['references']:
            kind = self.store.get(reference)['record_type']
            return (kind == namespace if namespace in {'source', 'artifact'} else
                kind in {'input', 'feature', 'product', 'read_subject'} if namespace == 'subject' else True)
        try:
            record = self.store.get(reference)
            if record['record_type'] == 'artifact':
                owns = self.db.execute("SELECT 1 FROM records r WHERE r.record_type='source' "
                    "AND json_extract(r.data,'$.provider')='episode.execution_result' "
                    "AND json_extract(r.data,'$.version')='native_blast_database_bundle_v1' "
                    "AND (json_extract(r.data,'$.artifact_ref')=? OR EXISTS "
                    "(SELECT 1 FROM json_each(r.data,'$.auxiliary_artifact_refs') a WHERE a.value=?)) LIMIT 1",
                    (reference, reference)).fetchone() is not None
                if owns:
                    # Retained source custody and old expanded receipt rows do
                    # not establish requested delivery. Shared content may be
                    # independently supplied or returned by an actual action.
                    if reference in self.store._refs(plain(context.assignment)):
                        return None
                    for subject in context.scope['subject_refs']:
                        if reference in self.store._refs(self.store.get(subject)):
                            return None
                    explicit = self.db.execute("SELECT 1 FROM runtime_actions a "
                        "JOIN json_each(a.result,'$.record_refs') refs "
                        "WHERE a.run_id=? AND a.episode_id=? "
                        "AND json_extract(a.result,'$.status') IN ('completed','partial') "
                        "AND refs.value=? LIMIT 1",
                        (self.run_id, context.episode_id, reference)).fetchone()
                    return None if explicit else False
            source = record if record['record_type'] == 'source' else self.store.get(record['source_ref']) if record.get('source_ref') else {}
            if source.get('provider') == 'episode.execution_result' and source.get('version') == 'native_blast_database_bundle_v1':
                return False
        except (ValueError, KeyError):
            pass
        return None

    def resolve_saved_function_input(self, context, descriptor: dict) -> dict:
        """Require this exact descriptor in a real earlier return or inheritance.

        The original commission's prefix excludes the new child's own return and
        every later sibling. Source/artifact possession alone is insufficient.
        """
        from method_loop.identities import EpisodeRef
        validate_schema(descriptor, _SAVED_INPUT_SCHEMA)
        self.authenticate(context, allow_unsaved=True)
        refs = self._references({SAVED_INPUT_SOURCE: [descriptor]})
        if not set(refs) <= _known(self.store, context):
            raise ContractError('native_blast_database_return_unauthorized')
        current, before_index = context, None
        if context.role == 'results':
            _original_commission(self.store, context)
        while True:
            if current.role in {'annotation', 'scientific_process'}:
                values = self._received(current, before_index=before_index)['groups'].get(SAVED_INPUT_SOURCE, [])
                if any(self._equal(descriptor, value) for value in values):
                    body = self.results.read_saved_function_input(descriptor, plain(context.scope))
                    if context.role == 'results' and body['target'] != self.owner._target(context):
                        raise ContractError('native_blast_database_return_unauthorized')
                    return body
            if len(current.path) < 2:
                break
            label = current.path[-1][1]
            index = label.removeprefix('child_')
            if not label.startswith('child_') or not index.isdecimal() or str(int(index)) != index:
                break
            before_index = int(index)
            current = self.context(EpisodeRef(self.run_id, current.path[:-1]).episode_id)
            if not set(refs) <= _known(self.store, current):
                break
        raise ContractError('native_blast_database_return_unauthorized')


__all__ = ['NativeBLASTDatabaseReturns', 'FACT_SOURCES', 'REFERENCE_SOURCE', 'requested_sources']
