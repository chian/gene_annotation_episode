"""Infernal returns with real Store/Journal/form records and controlled facts.

Only the validated-results input port and numerical rows are controlled here.
Native receipts and actual Workflow execution are verified separately in
test_native_infernal_results_integration.py. These tests launch no native tool.
"""
from copy import deepcopy
from dataclasses import replace
import json
from types import SimpleNamespace

from method_loop.episode import EpisodeGoal, EpisodeRequest
from method_loop.identities import EpisodeRef
import pytest

from gene_annotation_episode.communication import form_with_facts, plain, validate_form
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.infernal_native_result_views import (
    FAMILY_SOURCES, IDENTIFIER_NAMESPACES, NATIVE_INFERNAL_METRICS, native_infernal_fact_sources)
from gene_annotation_episode.native_infernal_returns import (
    FACT_SOURCES, REFERENCE_SOURCE, NativeInfernalReturns, requested_sources)
from gene_annotation_episode.runtime import Record, TypedReportContract
from gene_annotation_episode.state import Store

GENERIC_REFS = 'execution_result_refs'
COMPLETE = 'execution_completed'


def schema_for(*sources):
    descriptors, fields = native_infernal_fact_sources(), {}
    for index, source in enumerate(sources):
        if source in FACT_SOURCES:
            node = deepcopy(descriptors[source]['report_schema'])
        elif source == COMPLETE:
            node = {'type': 'boolean', 'x-source': source}
        else:
            node = {'type': 'array', 'uniqueItems': True, 'items': {'type': 'string',
                'format': 'reference', 'x-reference-namespace': 'execution_result'}, 'x-source': source}
        fields['requested_' + str(index)] = node
    return {'type': 'object', 'properties': fields, 'required': list(fields), 'additionalProperties': False}


class ControlledResults:
    """Supplied validated-results port; production runtime custody is unchanged."""
    def __init__(self):
        self.saved, self.calls = {}, []

    def applies(self, context):
        return context.role == 'results' and context.assignment.get('provider') == 'infernal'

    def facts(self, context):
        self.calls.append(context.episode_id)
        result = deepcopy(self.saved[context.episode_id])
        wanted = requested_sources(context.request['report_contract']['measurements']['schema'])
        for source in FACT_SOURCES:
            if source not in wanted:
                result[source] = []
        return result


class SavedReturns:
    def __init__(self, store):
        self.store, self.run_id = store, 'native-infernal-return-fixture'
        self.journal = Journal(store, self.run_id)
        self.receipts = EpisodeReceipts(store, self.run_id)
        self.scope = {'subject_refs': store.create_problem(raw_sequence='ACGT', molecule='dna')['subject_refs']}
        self.results = ControlledResults()
        self.boundary = NativeInfernalReturns(SimpleNamespace(
            store=store, run_id=self.run_id, native_infernal_results=self.results))
        self.root = self.context((('annotation', 'root'),), {}, None)

    def context(self, path, assignment, contract, parent=None):
        episode_id = EpisodeRef(self.run_id, path).episode_id
        self.receipts.bind(episode_id, None if parent is None else parent.episode_id)
        goal = (EpisodeGoal.root(objective='Verify supplied Infernal returns', result_contract={'role': path[-1][0]})
            if parent is None else EpisodeGoal.child(EpisodeGoal.from_record(plain(parent.request)['goal']),
                objective='Verify supplied Infernal returns', result_contract=contract.schema))
        message = {'scope': deepcopy(self.scope), 'initial_report': {}, 'episode_assignment': deepcopy(assignment)}
        request = EpisodeRequest(goal, Record(message), contract).as_record()
        context = BindingContext(self.run_id, episode_id, path[-1][0], path, self.scope, assignment, request)
        self.journal.save('runtime_episodes', {'episode_id': episode_id, 'path': canonical(path),
            'request': canonical(request), 'initial_credit': 0, 'state': 'active', 'completion': None, 'archive': None})
        return context

    def child(self, parent, schema, *, index=0, role='results', provider='infernal'):
        contract = TypedReportContract('Return requested original values', schema, lambda *_: True)
        assignment = {'provider': provider} if role == 'results' else {}
        child = self.context((*parent.path, (role, 'child_' + str(index))), assignment, contract, parent)
        selection = {'kind': 'episode_child', 'role': role, 'assignment': deepcopy(assignment),
            'scope': deepcopy(self.scope), 'purpose': contract.decision, 'schema_json': canonical(schema)}
        self.journal.save('runtime_actions', {'episode_id': parent.episode_id, 'decision_index': index,
            'action': canonical(selection), 'result': None, 'credit': None})
        return child

    def source(self, label, *, native=True):
        artifact = self.store.artifact(canonical({'controlled': label}).encode(), 'application/json')
        return self.store.put('source', {'provider': 'episode.execution_result' if native else 'other.provider',
            'accession': None, 'uri': None, 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None,
            'version': 'native_infernal_bundle_v1' if native else None,
            'retrieved_at': '2026-10-26T00:00:00+00:00'}, origin='tool')['id']

    def publication(self, child, family='search_hit', *, unbound=False):
        source = self.source(child.episode_id)
        model = self.store.put('reference', {'reference_type': 'family', 'source_ref': source,
            'accession': 'controlled_model', 'label': 'Controlled model', 'sequence_ref': None,
            'molecule': None, 'length': None, 'term_refs': [], 'context_refs': []}, origin='tool', scope=self.scope)['id']
        metric, missing = NATIVE_INFERNAL_METRICS[family][:2]
        value = {'search_sequence': 0, 'alignment_column': 3, 'alignment_pair': 3}.get(family, 1.25)
        measurement = {'name': metric, 'value': value}
        subject = self.scope['subject_refs'][0]
        observation = None if unbound else self.store.put('observation', {
            'subject_refs': [subject], 'source_subject_refs': [model], 'kind': 'profile_match',
            'source_ref': source, 'measurements': [{'name': metric, 'value': {
                'type': 'number', 'value': measurement['value'], 'unit_ref': None}}],
            'dependencies': [source, subject, model], 'anchor': None, 'operand_intervals': []},
            origin='tool', scope=self.scope)['id']
        row = {'record_key': 'controlled-' + family, 'source_ref': source, 'observation_ref': observation,
            'subject_ref': None if unbound else subject, 'reference_refs': [model],
            'sequence_name': 'controlled_sequence', 'model_name': 'controlled_model',
            'strand': 'plus', 'origin': None, 'population': None, 'column_index': None, 'pair_columns': None,
            'status': 'unbound' if unbound else 'published', 'measurements': [measurement],
            'unavailable': [{'name': missing, 'reason': 'not_measured'}]}
        references = sorted(ref for ref in [source, model, observation] if ref is not None)
        facts = {source: [] for source in FACT_SOURCES}
        facts.update({FAMILY_SOURCES[family]: [row], GENERIC_REFS: references,
            REFERENCE_SOURCE: references, COMPLETE: True})
        self.results.saved[child.episode_id] = facts
        self.receipts.receive(child.episode_id, references, kind='own_action', source_index=0)
        return deepcopy(row)

    def returned(self, parent, child, facts=None):
        contract = plain(child.request)['report_contract']
        schema = contract['measurements']['schema']
        facts = self.results.facts(child) if facts is None else deepcopy(facts)
        form = form_with_facts({}, schema, facts)
        self.journal.save('runtime_forms', {'episode_id': child.episode_id,
            'facts': canonical(facts), 'form': canonical(form)})
        index = int(child.path[-1][1].removeprefix('child_'))
        self.journal.save('runtime_report_attempts', {'parent_episode_id': parent.episode_id,
            'decision_index': index, 'delivery_ref': 'delivery_' + digest([parent.episode_id, index])[:24],
            'child_episode_id': child.episode_id, 'contract': canonical(contract),
            'form': canonical(form), 'failure': None})
        return form

    def operation(self, context, index=0):
        return f'{self.run_id}:{context.episode_id}:{index}:typed_form'

    def redeliver(self, parent, child, schema, *, index=1):
        original_index = int(child.path[-1][1].removeprefix('child_'))
        original = self.store.db.execute('SELECT * FROM runtime_report_attempts WHERE '
            'run_id=? AND parent_episode_id=? AND decision_index=?',
            (self.run_id, parent.episode_id, original_index)).fetchone()
        contract = TypedReportContract('Return selected frozen facts', schema, lambda *_: True).as_record()
        facts = json.loads(self.journal.row('runtime_forms', child.episode_id)['facts'])
        form = form_with_facts({}, schema, facts)
        selection = {'kind': 'redeliver_report', 'delivery_ref': original['delivery_ref'],
            'schema_json': canonical(schema), 'purpose': contract['decision']}
        self.journal.save('runtime_model_calls', {'episode_id': parent.episode_id, 'call_index': index,
            'purpose': 'decision', 'request': '{}', 'response': canonical({'selection': selection})})
        self.journal.save('runtime_report_attempts', {'parent_episode_id': parent.episode_id,
            'decision_index': index, 'delivery_ref': original['delivery_ref'], 'child_episode_id': child.episode_id,
            'contract': canonical(contract), 'form': canonical(form), 'failure': None})
        return form


@pytest.fixture(autouse=True)
def no_scientific_work(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('Return authentication attempted scientific work or acquisition')
    monkeypatch.setattr('socket.create_connection', forbidden)
    monkeypatch.setattr('subprocess.Popen', forbidden)
    for module, names in (
        ('native_infernal_results', ['capture_local_bundle', 'prepare_native_infernal_grading',
                                    'publish_selected_native_infernal_rows']),
        ('native_infernal_result_worker', ['run', 'populate_cmalign_sheet', 'populate_infernal_search_sheet',
                                         'calculate_cmalign_scores', 'calculate_infernal_search_scores'])):
        for name in names:
            monkeypatch.setattr('gene_annotation_episode.' + module + '.' + name, forbidden)


@pytest.fixture
def saved(tmp_path):
    with Store(tmp_path / 'state') as store:
        yield SavedReturns(store)


@pytest.mark.parametrize('family,unbound', [
    (family, unbound) for family in ('search_hit', 'search_sequence', 'alignment_sequence')
    for unbound in (False, True)] + [('alignment_column', True), ('alignment_pair', True)])
def test_five_families_keep_exact_numbers_and_missing_states(saved, family, unbound):
    source = FAMILY_SOURCES[family]
    schema = schema_for(source)
    child = saved.child(saved.root, schema)
    row = saved.publication(child, family, unbound=unbound)
    form = saved.returned(saved.root, child)
    before = list(saved.store.db.iterdump())
    saved.boundary.validate_received_report(child, form, schema)
    assert saved.boundary.received_context(saved.root) == [{'fact_source': source, 'facts': [row]}]
    assert saved.boundary.received_facts(saved.root, schema) == {source: [row]}
    for namespace, value in zip(IDENTIFIER_NAMESPACES,
            [row['record_key'], row['sequence_name'], row['model_name']]):
        assert saved.boundary.resolve_received(saved.root, value, namespace) is True
        assert saved.boundary.resolve_received(saved.root, 'unreceived', namespace) is False
    refs = saved.boundary.record_admission(saved.root, form, schema, saved.operation(saved.root))
    assert refs == [ref for ref in [row['source_ref'], row['observation_ref'], *row['reference_refs']] if ref is not None]
    assert saved.boundary.received_facts(saved.root, schema_for(REFERENCE_SOURCE)) == {REFERENCE_SOURCE: refs}
    assert list(saved.store.db.iterdump()) == before


def test_reference_only_receives_exact_refs_without_numerical_access(saved):
    schema = schema_for(GENERIC_REFS)
    child = saved.child(saved.root, schema)
    row = saved.publication(child)
    form = saved.returned(saved.root, child)
    before = list(saved.store.db.iterdump())
    saved.boundary.validate_received_report(child, form, schema)
    refs = saved.boundary.record_admission(saved.root, form, schema, saved.operation(saved.root))
    assert refs == form['requested_0']
    assert saved.boundary.received_context(saved.root) == []
    assert saved.boundary.received_facts(saved.root, schema_for(*FACT_SOURCES)) == {source: [] for source in FACT_SOURCES}
    assert saved.boundary.received_facts(saved.root, schema_for(REFERENCE_SOURCE)) == {REFERENCE_SOURCE: refs}
    for ref in refs:
        assert saved.boundary.resolve_received(saved.root, ref, 'execution_result') is True
    assert saved.boundary.resolve_received(saved.root, row['source_ref'], 'source') is True
    assert saved.boundary.resolve_received(saved.root, row['observation_ref'], 'source') is False
    for namespace, value in zip(IDENTIFIER_NAMESPACES,
            [row['record_key'], row['sequence_name'], row['model_name']]):
        assert saved.boundary.resolve_received(saved.root, value, namespace) is False
    assert list(saved.store.db.iterdump()) == before


@pytest.mark.parametrize('forward_source', [REFERENCE_SOURCE, COMPLETE])
def test_scientific_boundary_forwards_only_its_requested_received_information(saved, forward_source):
    schema = schema_for(forward_source)
    science = saved.child(saved.root, schema, role='scientific_process')
    leaf_schema = schema_for(GENERIC_REFS)
    leaf = saved.child(science, leaf_schema)
    row = saved.publication(leaf)
    returned = saved.returned(science, leaf)
    facts = saved.boundary.received_facts(science, schema)
    facts[COMPLETE] = True
    form = saved.returned(saved.root, science, facts)
    saved.boundary.validate_received_report(science, form, schema)
    refs = saved.boundary.record_admission(saved.root, form, schema, saved.operation(saved.root))
    assert refs == (returned['requested_0'] if forward_source == REFERENCE_SOURCE else [])
    assert saved.boundary.received_context(saved.root) == []
    assert saved.boundary.received_facts(saved.root, schema_for(REFERENCE_SOURCE)) == {REFERENCE_SOURCE: refs}
    assert saved.boundary.resolve_received(saved.root, row['record_key'], 'native_infernal_row') is False


def test_completion_only_and_store_possession_do_not_deliver_records(saved):
    schema = schema_for(COMPLETE)
    child = saved.child(saved.root, schema)
    row = saved.publication(child)
    form = saved.returned(saved.root, child)
    saved.receipts.receive(saved.root.episode_id, [row['source_ref']], kind='own_action', source_index=3)
    before = list(saved.store.db.iterdump())
    assert form == {'requested_0': True}
    assert saved.boundary.record_admission(saved.root, form, schema, saved.operation(saved.root)) == []
    assert saved.boundary.received_context(saved.root) == []
    assert saved.boundary.received_facts(saved.root, schema_for(REFERENCE_SOURCE)) == {REFERENCE_SOURCE: []}
    assert saved.boundary.resolve_received(saved.root, row['record_key'], 'native_infernal_row') is False
    assert list(saved.store.db.iterdump()) == before


def test_other_provider_generic_refs_remain_unhandled(saved):
    schema = schema_for(GENERIC_REFS)
    child = saved.child(saved.root, schema, provider='other')
    reference = saved.source('other', native=False)
    form = saved.returned(saved.root, child, {GENERIC_REFS: [reference]})
    saved.boundary.validate_received_report(child, form, schema)
    assert saved.boundary.record_admission(saved.root, form, schema, saved.operation(saved.root)) == []
    assert saved.boundary.received_context(saved.root) == []
    assert saved.boundary.received_facts(saved.root, schema) == {}
    assert saved.boundary.received_facts(saved.root, schema_for(REFERENCE_SOURCE)) == {REFERENCE_SOURCE: []}
    assert saved.boundary.resolve_received(saved.root, reference, 'execution_result') is None
    assert saved.boundary.resolve_received(saved.root, reference, 'unrelated_namespace') is None
    assert saved.results.calls == []


@pytest.mark.parametrize('source', [GENERIC_REFS, REFERENCE_SOURCE])
def test_results_owner_aliases_validate_exact_reference_set(saved, source):
    schema = schema_for(source)
    child = saved.child(saved.root, schema)
    saved.publication(child)
    form = saved.returned(saved.root, child)
    saved.boundary.validate_received_report(child, form, schema)
    for changed in ([*form['requested_0'], saved.source('forged')], form['requested_0'][:-1]):
        with pytest.raises(ValueError, match='native_infernal_return_returned_facts_conflict'):
            saved.boundary.validate_received_report(child, {'requested_0': changed}, schema)


@pytest.mark.parametrize('field', ['measurements', 'unavailable', 'source_ref', 'record_key', 'sequence_name', 'subject_ref'])
def test_forged_rows_fail_even_when_frozen_forms_and_attempts_agree(saved, field):
    source = FAMILY_SOURCES['search_hit']
    schema = schema_for(source)
    child = saved.child(saved.root, schema)
    saved.publication(child)
    facts = saved.results.facts(child)
    row = facts[source][0]
    if field == 'measurements':
        row[field][0]['value'] += 1
    elif field == 'unavailable':
        row[field][0]['reason'] = 'missing_input'
    elif field == 'subject_ref':
        row[field] = None
    elif field == 'source_ref':
        row[field] = saved.source('wrong-source')
    else:
        row[field] = 'forged'
    form = saved.returned(saved.root, child, facts)
    with pytest.raises(ValueError, match='native_infernal_return_returned_facts_conflict'):
        saved.boundary.received_context(saved.root)
    with pytest.raises(ValueError, match='native_infernal_return_returned_facts_conflict'):
        saved.boundary.record_admission(saved.root, form, schema, saved.operation(saved.root))


def test_sibling_records_cannot_be_forwarded_by_source_possession(saved):
    forward = schema_for(REFERENCE_SOURCE)
    science = saved.child(saved.root, forward, role='scientific_process')
    sibling = saved.child(saved.root, schema_for(GENERIC_REFS), index=1)
    row = saved.publication(sibling)
    saved.returned(saved.root, sibling)
    saved.receipts.receive(science.episode_id, [row['source_ref']], kind='own_action', source_index=0)
    with pytest.raises(ValueError, match='native_infernal_return_returned_facts_conflict'):
        saved.boundary.validate_received_report(science, {'requested_0': [row['source_ref']]}, forward)


@pytest.mark.parametrize('alteration', ['scope', 'assignment', 'role', 'purpose', 'schema'])
@pytest.mark.parametrize('redelivery', [False, True])
def test_original_commission_is_checked_on_delivery_and_redelivery(saved, alteration, redelivery):
    schema = schema_for(GENERIC_REFS)
    child = saved.child(saved.root, schema)
    saved.publication(child)
    form = saved.returned(saved.root, child)
    index = 0
    if redelivery:
        schema = schema_for(REFERENCE_SOURCE)
        form = saved.redeliver(saved.root, child, schema)
        index = 1
    action = json.loads(saved.journal.row('runtime_actions', saved.root.episode_id, 0)['action'])
    if alteration == 'scope':
        action['scope'] = {'subject_refs': []}
    elif alteration == 'assignment':
        action['assignment'] = {'provider': 'other'}
    elif alteration == 'role':
        action['role'] = 'annotation'
    elif alteration == 'purpose':
        action['purpose'] = 'changed purpose'
    else:
        action['schema_json'] = canonical(schema_for(COMPLETE))
    saved.store.db.execute('UPDATE runtime_actions SET action=? WHERE run_id=? AND episode_id=? AND decision_index=0',
        (canonical(action), saved.run_id, saved.root.episode_id))
    with pytest.raises(ValueError, match='native_infernal_return_.*conflict'):
        saved.boundary.record_admission(saved.root, form, schema, saved.operation(saved.root, index))


@pytest.mark.parametrize('kind', ['frozen_form', 'frozen_facts', 'request', 'child', 'delivery', 'closure'])
def test_saved_ownership_and_closure_changes_are_rejected(saved, kind):
    schema = schema_for(GENERIC_REFS)
    child = saved.child(saved.root, schema)
    saved.publication(child)
    form = saved.returned(saved.root, child)
    if kind in {'frozen_form', 'frozen_facts'}:
        column = 'form' if kind == 'frozen_form' else 'facts'
        saved.store.db.execute(f'UPDATE runtime_forms SET {column}=? WHERE run_id=? AND episode_id=?',
            ('{}', saved.run_id, child.episode_id))
    elif kind == 'request':
        changed = plain(child.request)
        changed['message']['scope'] = {'subject_refs': []}
        forged = replace(child, request=changed)
        with pytest.raises(ValueError, match='native_infernal_return_context_conflict'):
            saved.boundary.validate_received_report(forged, form, schema)
        return
    elif kind == 'child':
        sibling_parent = saved.child(saved.root, schema_for(COMPLETE), index=1, role='scientific_process')
        sibling = saved.child(sibling_parent, schema)
        saved.publication(sibling)
        saved.returned(sibling_parent, sibling)
        saved.store.db.execute('UPDATE runtime_report_attempts SET child_episode_id=? WHERE run_id=? '
            'AND parent_episode_id=? AND decision_index=0', (sibling.episode_id, saved.run_id, saved.root.episode_id))
    elif kind == 'closure':
        saved.store.db.execute('DELETE FROM runtime_forms WHERE run_id=? AND episode_id=?',
            (saved.run_id, child.episode_id))
    else:
        form = saved.redeliver(saved.root, child, schema, index=1)
        saved.store.db.execute('UPDATE runtime_report_attempts SET delivery_ref=? WHERE run_id=? '
            'AND parent_episode_id=? AND decision_index=1', ('delivery_changed', saved.run_id, saved.root.episode_id))
    with pytest.raises(ValueError, match='native_infernal_return_'):
        saved.boundary.record_admission(saved.root, form, schema, saved.operation(saved.root, int(kind == 'delivery')))


def test_exact_redelivery_deduplicates_without_new_action_or_observation(saved):
    schema = schema_for(FAMILY_SOURCES['search_hit'])
    child = saved.child(saved.root, schema)
    row = saved.publication(child)
    saved.returned(saved.root, child)
    again = deepcopy(schema)
    again['properties']['redelivered'] = again['properties'].pop('requested_0')
    again['required'] = ['redelivered']
    form = saved.redeliver(saved.root, child, again)
    before = list(saved.store.db.iterdump())
    refs = saved.boundary.record_admission(saved.root, form, again, saved.operation(saved.root, 1))
    assert refs == [row['source_ref'], row['observation_ref'], *row['reference_refs']]
    assert saved.boundary.received_context(saved.root) == [{'fact_source': FAMILY_SOURCES['search_hit'], 'facts': [row]}]
    assert saved.boundary.record_admission(saved.root, form, again, saved.operation(saved.root, 1)) == refs
    assert list(saved.store.db.iterdump()) == before
    assert saved.journal.row('runtime_actions', saved.root.episode_id, 1) is None
    assert saved.store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 0


def test_reference_redelivery_cannot_recover_unrequested_numerical_rows(saved):
    schema = schema_for(GENERIC_REFS)
    child = saved.child(saved.root, schema)
    row = saved.publication(child)
    saved.returned(saved.root, child)
    numeric = schema_for(FAMILY_SOURCES['search_hit'])
    form = saved.redeliver(saved.root, child, numeric)
    assert form == {'requested_0': []}
    assert saved.boundary.record_admission(saved.root, form, numeric, saved.operation(saved.root, 1)) == []
    assert saved.boundary.resolve_received(saved.root, row['record_key'], 'native_infernal_row') is False


def test_reference_redelivery_deduplicates_exact_received_references(saved):
    schema = schema_for(GENERIC_REFS)
    child = saved.child(saved.root, schema)
    saved.publication(child)
    original = saved.returned(saved.root, child)
    alias = schema_for(REFERENCE_SOURCE)
    repeated = saved.redeliver(saved.root, child, alias)
    before = list(saved.store.db.iterdump())
    assert saved.boundary.record_admission(saved.root, repeated, alias, saved.operation(saved.root, 1)) == original['requested_0']
    assert saved.boundary.received_facts(saved.root, alias) == {REFERENCE_SOURCE: original['requested_0']}
    assert saved.boundary.received_context(saved.root) == []
    assert list(saved.store.db.iterdump()) == before


def test_changed_live_context_role_and_conflicting_reference_fields_reject(saved):
    schema = schema_for(GENERIC_REFS, GENERIC_REFS)
    child = saved.child(saved.root, schema)
    saved.publication(child)
    form = saved.returned(saved.root, child)
    with pytest.raises(ValueError, match='binding_context_path_must_match_role'):
        replace(child, role='scientific_process')
    form['requested_1'] = []
    with pytest.raises(ValueError, match='native_infernal_return_conflicting_fields'):
        saved.boundary.validate_received_report(child, form, schema)


def test_authentication_snapshot_is_reused_only_within_one_form_validation(saved):
    schema = schema_for(FAMILY_SOURCES['search_hit'])
    child = saved.child(saved.root, schema)
    row = saved.publication(child)
    form = saved.returned(saved.root, child)
    saved.results.calls.clear()
    resolver = lambda ref, namespace: (True if namespace == 'subject'
        else saved.boundary.resolve_received(saved.root, ref, namespace))
    assert validate_form(form, schema, resolver) == form
    assert saved.results.calls == [child.episode_id]
    saved.results.saved[child.episode_id][FAMILY_SOURCES['search_hit']][0]['measurements'][0]['value'] += 1
    with pytest.raises(ValueError, match='native_infernal_return_returned_facts_conflict'):
        validate_form(form, schema, resolver)
    assert saved.results.calls == [child.episode_id, child.episode_id]
    assert row['measurements'][0]['value'] == 1.25

