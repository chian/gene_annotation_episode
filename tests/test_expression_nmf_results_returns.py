"""Real runtime/form records with a strict result-host double for custody tests.

These are boundary tests, not a second native run or a full Workflow claim.
"""
from copy import deepcopy
from dataclasses import replace
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest
from method_loop.episode import EpisodeGoal, EpisodeRequest
from method_loop.identities import EpisodeRef

from gene_annotation_episode.communication import plain, form_with_facts
from gene_annotation_episode.domain import obj
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.expression_nmf_return_views import (FACT_SOURCES, PROJECTION_SOURCE, SAVED_SOURCE,
    FAILURE_SOURCE, expression_nmf_fact_sources)
from gene_annotation_episode.expression_nmf_returns import ExpressionNMFReturns
from gene_annotation_episode.expression_nmf_result_receipts import ExpressionNMFResultReceipts
from gene_annotation_episode.native_file_capture import retained_native_file
from gene_annotation_episode.runtime import Record, TypedReportContract
from gene_annotation_episode.state import Store


def form_schema(*sources):
    declarations = expression_nmf_fact_sources()
    return obj({str('field_' + str(index)): deepcopy(declarations[source]['report_schema']) for index, source in enumerate(sources)})


class StrictHost:
    def __init__(self, store, run_id):
        self.store, self.run_id, self.originals = store, run_id, {}

    @staticmethod
    def applies(context):
        return context.role == 'results' and context.assignment.get('selector', {}).get('version') == 'expression_nmf_result_selector_v1'

    def register(self, context, facts):
        action = {'kind': 'tool', 'tool': 'execution.results.collect', 'arguments': {}}
        outcome = {'status': 'completed', 'boundary_fixture': deepcopy(facts)}
        self.originals[context.episode_id] = (plain(context.as_record()), action, outcome)
        Journal(self.store, self.run_id).save('runtime_actions', {'episode_id': context.episode_id, 'decision_index': 0,
            'action': canonical(action), 'result': canonical(outcome), 'credit': None})

    def own_fact_groups(self, context, *, verify_artifacts):
        original, selected, outcome = self.originals[context.episode_id]
        assert plain(context.as_record()) == original
        row = self.store.db.execute('SELECT action,result FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=0',
            (self.run_id, context.episode_id)).fetchone()
        if json.loads(row['action']) != selected or json.loads(row['result']) != outcome:
            raise ValueError('fixture_original_action_mismatch')
        result = deepcopy(outcome['boundary_fixture'])
        if verify_artifacts:
            for file in result[SAVED_SOURCE]:
                retained_native_file(self.store, file)
        return result


class Fixture:
    def __init__(self, store):
        self.store, self.run_id = store, 'nmf489-return'
        self.journal, self.ledger = Journal(store, self.run_id), EpisodeReceipts(store, self.run_id)
        self.scope = {'subject_refs': store.create_problem(raw_sequence='ACGT', molecule='dna')['subject_refs']}
        self.host = StrictHost(store, self.run_id)
        self.boundary = ExpressionNMFReturns(SimpleNamespace(store=store, run_id=self.run_id, native_expression_nmf_results=self.host))
        self.root = self.context((('annotation', 'root'),), {}, None)
        raw = (Path(os.environ['NMF489_REPO']) / 'verification/tool_graders_expression_nmf_native_grader_2026-10-27_484/check003/native-none/sheet-example.json').read_bytes()
        reference = store.artifact(raw, 'application/json')
        self.sheet = {'artifact_ref': reference, 'sha256': reference[9:], 'size_bytes': len(raw), 'format': 'expression_nmf_sheet_v1'}
        self.projection = dict(schema='expression_nmf_result_view_v1', view='fit_diagnostics', selector={
            'view': 'fit_diagnostics', 'fields': ['sse'], 'row_window': {'offset': 0, 'limit': 1}}, status='calculated',
            native_outcome='complete', total_available_rows=10, selected_row_count=1, filtered_row_count=1,
            row_offset=0, returned_row_count=1, has_more=False, rows=[{'field': 'sse', 'value': 0.0, 'units': 'counts^2',
            'denominator': None}], qualifications=[], failures=[], warning_codes=[])

    def persist(self, context):
        self.journal.save('runtime_episodes', {'episode_id': context.episode_id, 'path': canonical(context.path),
            'request': canonical(plain(context.request)), 'initial_credit': 0, 'state': 'active', 'completion': None, 'archive': None})

    def context(self, path, assignment, contract, parent=None):
        episode_id = EpisodeRef(self.run_id, path).episode_id
        manifest = self.ledger.bind(episode_id, None if parent is None else parent.episode_id)
        goal = (EpisodeGoal.root(objective='Verify NMF result custody', result_contract={}) if parent is None else
            EpisodeGoal.child(EpisodeGoal.from_record(plain(parent.request)['goal']), objective='Verify NMF result custody', result_contract=contract.schema))
        message = dict(scope=self.scope, initial_report={}, episode_assignment=deepcopy(assignment), knowledge_inheritance=manifest)
        request = EpisodeRequest(goal, Record(message), contract).as_record()
        result = BindingContext(self.run_id, episode_id, path[-1][0], path, self.scope, assignment, request)
        self.persist(result)
        return result

    def child(self, parent, schema, *, index=0, role='results', saved=None):
        contract = TypedReportContract('Return the selected NMF data', schema, lambda *_: True)
        selected = {'version': 'expression_nmf_result_selector_v1', 'mode': 'native_result' if saved is None else 'saved_sheet_recalculation',
            'projection': self.projection['selector'], 'saved_sheet_file': deepcopy(saved)}
        assignment = {'version': 'execution_results_assignment_v1', 'handoff_ref': 'fixture-handoff', 'selector': selected} if role == 'results' else {}
        child = self.context((*parent.path, (role, 'child_' + str(index))), assignment, contract, parent)
        action = dict(kind='episode_child', role=role, assignment=plain(child.assignment), scope=self.scope,
            purpose=contract.decision, schema_json=canonical(schema))
        self.journal.save('runtime_actions', {'episode_id': parent.episode_id, 'decision_index': index, 'action': canonical(action), 'result': None, 'credit': None})
        return child

    def own(self, child):
        self.host.register(child, {PROJECTION_SOURCE: [self.projection], SAVED_SOURCE: [self.sheet], FAILURE_SOURCE: []})

    def returned(self, parent, child):
        contract = plain(child.request)['report_contract']
        schema = contract['measurements']['schema']
        facts = (self.host.own_fact_groups(child, verify_artifacts=True) if child.role == 'results' else
            self.boundary.facts_for_closure(child, schema))
        form = form_with_facts({}, schema, facts)
        self.boundary.validate_received_report(child, form, schema)
        self.journal.save('runtime_forms', {'episode_id': child.episode_id, 'facts': canonical(facts), 'form': canonical(form)})
        index = int(child.path[-1][1][6:])
        self.journal.save('runtime_report_attempts', {'parent_episode_id': parent.episode_id, 'decision_index': index,
            'delivery_ref': 'delivery_' + digest([parent.episode_id, index]), 'child_episode_id': child.episode_id,
            'contract': canonical(contract), 'form': canonical(form), 'failure': None})
        references = self.boundary.record_admission(parent, form, schema, f'{self.run_id}:{parent.episode_id}:{index}:typed_form')
        self.ledger.receive(parent.episode_id, references, kind='child_form', source_index=index)
        return form


@pytest.fixture
def fixture(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('Typed return authority attempted acquisition or calculation')
    for target in ('socket.socket', 'subprocess.Popen',
            'gene_annotation_episode.expression_nmf_result_worker.execute_expression_nmf_worker'):
        monkeypatch.setattr(target, forbidden)
    with Store(tmp_path / 'store') as store:
        f = Fixture(store)
        yield f
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 0


def test_requested_projection_grants_no_saved_sheet(fixture):
    f = fixture
    child = f.child(f.root, form_schema(PROJECTION_SOURCE))
    f.own(child)
    f.returned(f.root, child)
    assert not f.boundary.resolve_received(f.root, f.sheet['artifact_ref'], 'artifact')
    with pytest.raises(ValueError, match='not_received'):
        f.boundary.authenticate_received_saved_sheet(f.root, f.sheet)


def population_reader(f, monkeypatch):
    """Use real frozen return ancestry and explicit result population fixtures."""
    reader = ExpressionNMFResultReceipts(SimpleNamespace(store=f.store, run_id=f.run_id,
        native_expression_nmf_returns=f.boundary))
    monkeypatch.setattr(reader, '_context', lambda context, **kw: f.boundary.authenticate(context, **kw))
    def receipts(context):
        facts = f.host.own_fact_groups(context, verify_artifacts=False)
        return [{'acquired_population': 'population_' + context.episode_id, 'facts': facts,
            'intent': {'assignment': plain(context.assignment)}}]
    monkeypatch.setattr(reader, 'completed_receipts', receipts)
    return reader


def test_projection_only_population_is_inherited_without_an_artifact_grant(fixture, monkeypatch):
    f = fixture
    first = f.child(f.root, form_schema(PROJECTION_SOURCE))
    f.own(first)
    before = f.child(f.root, form_schema(PROJECTION_SOURCE), index=1)
    f.returned(f.root, first)
    after = f.child(f.root, form_schema(PROJECTION_SOURCE), index=2)
    reader = population_reader(f, monkeypatch)
    assert reader.baseline_populations(before, []) == set()
    assert reader.baseline_populations(after, []) == {'population_' + first.episode_id}
    assert not f.boundary.resolve_received(f.root, f.sheet['artifact_ref'], 'artifact')


def test_forwarded_projection_population_preserves_its_frozen_origin(fixture, monkeypatch):
    f = fixture
    science = f.child(f.root, form_schema(PROJECTION_SOURCE), role='scientific_process')
    first = f.child(science, form_schema(PROJECTION_SOURCE))
    f.own(first)
    f.returned(science, first)
    f.returned(f.root, science)
    later = f.child(science, form_schema(PROJECTION_SOURCE), index=1)
    f.own(later)
    f.returned(science, later)
    new = f.child(f.root, form_schema(PROJECTION_SOURCE), index=1)
    reader = population_reader(f, monkeypatch)
    assert reader.baseline_populations(new, []) == {'population_' + first.episode_id}


def test_sheet_possession_requires_original_immediate_child_return(fixture):
    f = fixture
    science = f.child(f.root, form_schema(SAVED_SOURCE), role='scientific_process')
    sibling = f.child(f.root, form_schema(SAVED_SOURCE), index=1, role='scientific_process')
    result = f.child(science, form_schema(SAVED_SOURCE))
    f.own(result)
    f.returned(science, result)
    with pytest.raises(ValueError, match='not_received'):
        f.boundary.authenticate_received_saved_sheet(f.root, f.sheet)
    with pytest.raises(ValueError, match='not_received'):
        f.boundary.authenticate_received_saved_sheet(sibling, f.sheet)
    f.returned(f.root, science)
    assert f.boundary.authenticate_received_saved_sheet(f.root, f.sheet) == (result.episode_id,)
    for field, changed in (('size_bytes', f.sheet['size_bytes']+1), ('format', 'unrelated')):
        with pytest.raises(ValueError):
            f.boundary.authenticate_received_saved_sheet(f.root, {**f.sheet, field: changed})


def test_frozen_forwarding_prefix_excludes_later_identical_origin(fixture):
    f = fixture
    science = f.child(f.root, form_schema(SAVED_SOURCE), role='scientific_process')
    result = f.child(science, form_schema(SAVED_SOURCE))
    f.own(result)
    f.returned(science, result)
    f.returned(f.root, science)
    later = f.child(science, form_schema(SAVED_SOURCE), index=1)
    f.own(later)
    f.returned(science, later)
    assert f.boundary.authenticate_received_saved_sheet(science, f.sheet) == (result.episode_id, later.episode_id)
    assert f.boundary.authenticate_received_saved_sheet(f.root, f.sheet) == (result.episode_id,)
    facts = json.loads(f.journal.row('runtime_forms', science.episode_id)['facts'])
    facts['expression_nmf_received_report_prefix']['attempts'][0]['form_sha256'] = '0' * 64
    f.store.db.execute('UPDATE runtime_forms SET facts=? WHERE episode_id=?', (canonical(facts), science.episode_id))
    with pytest.raises(ValueError, match='prefix_conflict'):
        f.boundary.authenticate_received_saved_sheet(f.root, f.sheet)


def test_saved_child_inherits_only_original_receipt_prefix(fixture):
    f = fixture
    first = f.child(f.root, form_schema(SAVED_SOURCE))
    f.own(first)
    selected = f.child(f.root, form_schema(PROJECTION_SOURCE), index=1, saved=f.sheet)
    f.returned(f.root, first)
    with pytest.raises(ValueError, match='not_received'):
        f.boundary.authenticate_received_saved_sheet(selected, f.sheet)
    new = f.child(f.root, form_schema(PROJECTION_SOURCE), index=2, saved=f.sheet)
    assert f.boundary.authenticate_received_saved_sheet(new, f.sheet) == (first.episode_id,)


def test_historical_return_survives_scientific_file_loss(fixture):
    f = fixture
    child = f.child(f.root, form_schema(SAVED_SOURCE))
    f.own(child)
    form = f.returned(f.root, child)
    retained_native_file(f.store, f.sheet).unlink()
    assert f.boundary.authenticate_received_saved_sheet(f.root, f.sheet) == (child.episode_id,)
    f.boundary.validate_received_report(child, form, form_schema(SAVED_SOURCE))


def frame(f, parent, child, *, index, schema, selection):
    from gene_annotation_episode.composition_information import CONTRACT_INFORMATION_PROFILE, CONTRACT_INFORMATION_OPERATIONS
    from gene_annotation_episode.episode_contract_information import expand_fact_form
    compact = obj({name: {'$ref': 'episode-fact:' + node['x-source']} for name, node in schema['properties'].items()})
    selection = {**deepcopy(selection), 'schema_json': canonical(compact)}
    facts = {child.role: expression_nmf_fact_sources()}
    expanded = expand_fact_form(selection['schema_json'], child_role=child.role,
        facts_by_role=facts, permitted_child_roles=[child.role])
    branch = obj({key: {'const': value} for key, value in selection.items()})
    action_schema = obj({'selection': {'anyOf': [branch]}, 'report_update': obj({})})
    lookup = [{'properties': {'view': {'const': 'child_options'}, 'role': {'enum': [None, child.role]}}},
        *[{'properties': {'operation': {'const': name}}} for name in CONTRACT_INFORMATION_OPERATIONS]]
    select = obj({'response_type': {'type': 'string', 'const': 'select_action'}, **action_schema['properties']})
    saved = {'context': {'tools': [], 'contract_information_profile': CONTRACT_INFORMATION_PROFILE}, 'schema': action_schema,
        'contract_information': {'version': CONTRACT_INFORMATION_PROFILE, 'permitted_child_roles': [child.role],
            'fact_sources_by_role': facts, 'fact_sources_sha256': digest(facts), 'catalog_sha256': digest([]),
            'action_schema_sha256': digest(action_schema), 'instructions': 'Explicit boundary test frame.',
            'exchange_schema': {'properties': {'response': {'anyOf': [{'properties': {'lookup': {'anyOf': lookup}}}, select]}}}}}
    f.journal.save('runtime_model_calls', {'episode_id': parent.episode_id, 'call_index': index, 'purpose': 'decision',
        'request': canonical(saved), 'response': canonical({'selection': selection, 'report_update': {}})})
    return selection, expanded


@pytest.mark.parametrize('tamper', [None, 'declaration', 'frame', 'empty_request'])
def test_full_and_compact_original_contract_validation(fixture, tamper):
    f = fixture
    schema = form_schema(SAVED_SOURCE)
    child = f.child(f.root, schema)
    action = json.loads(f.journal.row('runtime_actions', f.root.episode_id, 0)['action'])
    selected, expanded = frame(f, f.root, child, index=0, schema=schema, selection=action)
    request = plain(child.request)
    request['message']['report_contract_declaration'] = expanded['declaration']
    child = replace(child, request=request)
    f.persist(child)
    f.store.db.execute('UPDATE runtime_actions SET action=? WHERE episode_id=?', (canonical(selected), f.root.episode_id))
    f.own(child)
    f.returned(f.root, child)
    if tamper == 'declaration':
        request['message']['report_contract_declaration']['expanded_schema_sha256'] = '0' * 64
        f.persist(replace(child, request=request))
    elif tamper == 'frame':
        f.store.db.execute("UPDATE runtime_model_calls SET request='{}'")
    elif tamper == 'empty_request':
        f.store.db.execute("UPDATE runtime_episodes SET request='{}' WHERE episode_id=?", (child.episode_id,))
    if tamper is None:
        assert f.boundary.authenticate_received_saved_sheet(f.root, f.sheet) == (child.episode_id,)
    else:
        with pytest.raises((ValueError, KeyError)):
            f.boundary.authenticate_received_saved_sheet(f.root, f.sheet)


def test_compact_redelivery_reads_frozen_facts_without_an_observation(fixture):
    f = fixture
    child = f.child(f.root, form_schema(PROJECTION_SOURCE))
    f.own(child)
    f.returned(f.root, child)
    before = f.store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0]
    schema = form_schema(SAVED_SOURCE)
    original = f.store.db.execute('SELECT delivery_ref FROM runtime_report_attempts').fetchone()[0]
    selection = dict(kind='redeliver_report', delivery_ref=original, purpose='Read the explicitly requested saved sheet', schema_json=canonical(schema))
    frame(f, f.root, child, index=1, schema=schema, selection=selection)
    contract = TypedReportContract(selection['purpose'], schema, lambda *_: True)
    form = form_with_facts({}, schema, json.loads(f.journal.row('runtime_forms', child.episode_id)['facts']))
    f.journal.save('runtime_report_attempts', {'parent_episode_id': f.root.episode_id, 'decision_index': 1,
        'delivery_ref': original, 'child_episode_id': child.episode_id, 'contract': canonical(contract.as_record()), 'form': canonical(form), 'failure': None})
    refs = f.boundary.record_admission(f.root, form, schema, f'{f.run_id}:{f.root.episode_id}:1:typed_form')
    f.ledger.receive(f.root.episode_id, refs, kind='report_redelivery', source_index=1)
    assert f.boundary.authenticate_received_saved_sheet(f.root, f.sheet) == (child.episode_id,)
    assert f.store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0] == before
