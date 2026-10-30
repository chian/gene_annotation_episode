"""Real runtime/form records and a labelled synthetic FBA result-host port.

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

from gene_annotation_episode.communication import (
    plain, form_with_facts, validate_closed_schema, validate_form, ReportBoundaryError,
)
from gene_annotation_episode.domain import obj
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.flux_balance_return_views import fba_fact_sources
from gene_annotation_episode.flux_balance_returns import FACT_SOURCES, PROJECTION_SOURCE, SAVED_SOURCE
from gene_annotation_episode.flux_balance_returns import FluxBalanceReturns
from gene_annotation_episode.native_file_capture import retained_native_file
from gene_annotation_episode.runtime import Record, TypedReportContract
from gene_annotation_episode.state import Store


FAILURE_SOURCE = "flux_balance_failures"
pytestmark = pytest.mark.skipif('HMMER529_ATTEMPT' not in os.environ, reason='requires bounded529')


def form_schema(*sources):
    declarations = fba_fact_sources()
    return obj({str('field_' + str(index)): deepcopy(declarations[source]['report_schema']) for index, source in enumerate(sources)})


class StrictHost:
    def __init__(self, store, run_id):
        self.store, self.run_id, self.originals = store, run_id, {}
        self.verification_requests = []

    @staticmethod
    def applies(context):
        return context.role == 'results' and context.assignment.get('selector', {}).get('version') == 'flux_balance_result_selector_v1'

    def register(self, context, facts):
        action = {'kind': 'tool', 'tool': 'execution.results.collect', 'arguments': {}}
        outcome = {'status': 'completed', 'boundary_fixture': deepcopy(facts)}
        self.originals[context.episode_id] = (plain(context.as_record()), action, outcome)
        Journal(self.store, self.run_id).save('runtime_actions', {'episode_id': context.episode_id, 'decision_index': 0,
            'action': canonical(action), 'result': canonical(outcome), 'credit': None})

    def own_fact_groups(self, context, *, verify_artifacts):
        self.verification_requests.append(verify_artifacts)
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
        self.store, self.run_id = store, 'fba709-return'
        self.journal, self.ledger = Journal(store, self.run_id), EpisodeReceipts(store, self.run_id)
        self.scope = {'subject_refs': store.create_problem(raw_sequence='ACGT', molecule='dna')['subject_refs']}
        self.host = StrictHost(store, self.run_id)
        self.boundary = FluxBalanceReturns(SimpleNamespace(store=store, run_id=self.run_id, native_flux_balance_results=self.host))
        self.root = self.context((('annotation', 'root'),), {}, None)
        root = Path(__file__).resolve().parents[1]
        core = json.loads((root / 'verification/tool_graders_flux_balance_core_2026-10-29_679/VERIFIED_NUMERICAL_EXAMPLE_001.json').read_text())
        raw = canonical(core['sheet']).encode()
        reference = store.artifact(raw, 'application/json')
        self.sheet = {'artifact_ref': reference, 'sha256': reference[9:], 'size_bytes': len(raw), 'format': 'flux_balance_sheet_v1'}
        self.parameters = core['calculations']['parameters']
        self.projection = json.loads((root / 'verification/tool_graders_flux_balance_result_projection_2026-10-29_693/RECORDED_679_PROJECTION_001.json').read_text())['run']
        self.failures = [deepcopy(self.projection['qualification_issues'][0]['issue'])]

    def persist(self, context):
        self.journal.save('runtime_episodes', {'episode_id': context.episode_id, 'path': canonical(context.path),
            'request': canonical(plain(context.request)), 'initial_credit': 0, 'state': 'active', 'completion': None, 'archive': None})

    def context(self, path, assignment, contract, parent=None):
        episode_id = EpisodeRef(self.run_id, path).episode_id
        manifest = self.ledger.bind(episode_id, None if parent is None else parent.episode_id)
        goal = (EpisodeGoal.root(objective='Verify FBA return custody', result_contract={}) if parent is None else
            EpisodeGoal.child(EpisodeGoal.from_record(plain(parent.request)['goal']), objective='Verify FBA return custody', result_contract=contract.schema))
        message = dict(scope=self.scope, initial_report={}, episode_assignment=deepcopy(assignment), knowledge_inheritance=manifest)
        request = EpisodeRequest(goal, Record(message), contract).as_record()
        result = BindingContext(self.run_id, episode_id, path[-1][0], path, self.scope, assignment, request)
        self.persist(result)
        return result

    def child(self, parent, schema, *, index=0, role='results', saved=None):
        contract = TypedReportContract('Return the selected FBA data', schema, lambda *_: True)
        selected = {'version': 'flux_balance_result_selector_v1', 'mode': 'native_result' if saved is None else 'saved_sheet_recalculation',
            'projection': self.projection['selector'], 'saved_sheet_file': deepcopy(saved),
            'calculation_parameters': deepcopy(self.parameters)}
        assignment = {'version': 'execution_results_assignment_v1', 'handoff_ref': 'fixture-handoff', 'selector': selected} if role == 'results' else {}
        child = self.context((*parent.path, (role, 'child_' + str(index))), assignment, contract, parent)
        action = dict(kind='episode_child', role=role, assignment=plain(child.assignment), scope=self.scope,
            goal='Verify FBA return custody', initial_report_json='{}',
            purpose=contract.decision, schema_json=canonical(schema))
        self.journal.save('runtime_actions', {'episode_id': parent.episode_id, 'decision_index': index, 'action': canonical(action), 'result': None, 'credit': None})
        return child

    def own(self, child):
        self.host.register(child, {PROJECTION_SOURCE: [self.projection], SAVED_SOURCE: [self.sheet], FAILURE_SOURCE: self.failures})

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
            'gene_annotation_episode.flux_balance_result_worker.execute_flux_balance_worker',
            'gene_annotation_episode.flux_balance_calculations.calculate_flux_balance_sheet',
            'gene_annotation_episode.flux_balance_sheet.populate_flux_balance_sheet',
            'gene_annotation_episode.flux_balance_readers.parse_fba_capture'):
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
    facts['flux_balance_received_report_prefix']['attempts'][0]['form_sha256'] = '0' * 64
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
    facts = {child.role: fba_fact_sources()}
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


def test_exact_normalized_measurements_and_failures_reach_requested_parent_fields(fixture):
    f = fixture
    schema = form_schema(*FACT_SOURCES)
    child = f.child(f.root, schema)
    f.own(child)
    form = f.returned(f.root, child)
    received = f.boundary.received_facts(f.root, schema)
    assert received[PROJECTION_SOURCE] == [f.projection]
    assert received[FAILURE_SOURCE] == f.failures
    assert form['field_0'] == received[PROJECTION_SOURCE]
    objective = next(row['value']['check'] for row in form['field_0'][0]['rows'] if row['field'] == 'objective')
    assert objective['native_basis_calculated']['value'] == -4.25
    assert objective['full_calculated']['value'] == -2.75
    assert objective['full_calculated']['unit']['basis'] == 'unknown'
    received[PROJECTION_SOURCE][0]['rows'].clear()
    assert f.boundary.received_facts(f.root, schema)[PROJECTION_SOURCE] == [f.projection]


def test_projection_origins_deduplicate_and_keep_original_results_owners(fixture):
    f = fixture
    science = f.child(f.root, form_schema(PROJECTION_SOURCE), role='scientific_process')
    for index in (0, 1):
        child = f.child(science, form_schema(PROJECTION_SOURCE), index=index)
        f.own(child)
        f.returned(science, child)
    groups, origins, witnesses = f.boundary._received(science, (PROJECTION_SOURCE,))
    assert groups == {PROJECTION_SOURCE: [f.projection]}
    original_ids = [f.host.originals[key][0]['episode_id'] for key in f.host.originals]
    assert origins[canonical(f.projection)] == original_ids
    assert len(witnesses) == 2
    f.returned(f.root, science)
    received, received_origins, _ = f.boundary._received(f.root, (PROJECTION_SOURCE,))
    assert received == groups and received_origins == origins
    assert not f.boundary.resolve_received(f.root, f.sheet['artifact_ref'], 'artifact')


@pytest.mark.parametrize('fault', ['selected_goal', 'selected_initial', 'selected_assignment',
    'selected_scope', 'tool_commission', 'goal', 'initial', 'assignment', 'inheritance'])
def test_changed_original_commission_is_not_a_return_authority(fixture, fault):
    f = fixture
    child = f.child(f.root, form_schema(SAVED_SOURCE))
    f.own(child)
    f.returned(f.root, child)
    if fault.startswith('selected_') or fault == 'tool_commission':
        row = f.journal.row('runtime_actions', f.root.episode_id, 0)
        action = json.loads(row['action'])
        if fault == 'selected_goal': action['goal'] = 'Different original goal'
        elif fault == 'selected_initial': action['initial_report_json'] = '{"invented":1}'
        elif fault == 'selected_assignment': action['assignment']['handoff_ref'] = 'other-handoff'
        elif fault == 'selected_scope': action['scope'] = {'subject_refs': []}
        else: action = {'kind': 'tool', 'tool': 'process.revise', 'arguments': {}}
        f.store.db.execute('UPDATE runtime_actions SET action=? WHERE episode_id=? AND decision_index=0',
            (canonical(action), f.root.episode_id))
    else:
        request = plain(child.request)
        if fault == 'goal': request['goal']['objective'] = 'Changed child objective'
        elif fault == 'initial': request['message']['initial_report'] = {'invented': 1}
        elif fault == 'assignment': request['message']['episode_assignment']['handoff_ref'] = 'other-handoff'
        else: request['message']['knowledge_inheritance']['through_receipt_index'] = 999
        f.persist(replace(child, request=request,
            assignment=request['message']['episode_assignment']))
    with pytest.raises(ValueError):
        f.boundary.authenticate_received_saved_sheet(f.root, f.sheet)


@pytest.mark.parametrize('fault', ['nonimmediate', 'failed_report', 'missing_form', 'forged_host_action'])
def test_only_actual_successful_immediate_closed_result_return_contributes(fixture, fault):
    f = fixture
    science = f.child(f.root, form_schema(SAVED_SOURCE), role='scientific_process')
    child = f.child(science, form_schema(SAVED_SOURCE))
    f.own(child)
    f.returned(science, child)
    f.returned(f.root, science)
    if fault == 'nonimmediate':
        f.store.db.execute('UPDATE runtime_report_attempts SET child_episode_id=? WHERE parent_episode_id=?',
            (child.episode_id, f.root.episode_id))
    elif fault == 'failed_report':
        f.store.db.execute('UPDATE runtime_report_attempts SET failure=? WHERE parent_episode_id=?',
            ('{"code":"failed"}', science.episode_id))
    elif fault == 'missing_form':
        f.store.db.execute('DELETE FROM runtime_forms WHERE episode_id=?', (child.episode_id,))
    else:
        f.store.db.execute("UPDATE runtime_actions SET result='{}' WHERE episode_id=?", (child.episode_id,))
    with pytest.raises(ValueError):
        f.boundary.authenticate_received_saved_sheet(f.root, f.sheet)


def test_open_result_checks_artifact_but_closed_historical_delivery_uses_only_frozen_records(fixture, monkeypatch):
    f = fixture
    schema = form_schema(SAVED_SOURCE, PROJECTION_SOURCE)
    child = f.child(f.root, schema); f.own(child)
    form = f.returned(f.root, child)
    assert True in f.host.verification_requests
    f.host.verification_requests.clear()
    monkeypatch.setattr(f.store, 'get_artifact', lambda *_: pytest.fail('historical read scientific bytes'))
    retained_native_file(f.store, f.sheet).unlink()
    f.boundary.validate_received_report(child, form, schema)
    assert f.boundary.authenticate_received_saved_sheet(f.root, f.sheet) == (child.episode_id,)
    assert f.host.verification_requests and not any(f.host.verification_requests)


@pytest.mark.parametrize('fault', ['different_value', 'extra_row', 'wrong_number_type'])
def test_frozen_measurements_cannot_be_forged_from_schema_valid_values(fixture, fault):
    f = fixture
    schema = form_schema(PROJECTION_SOURCE)
    child = f.child(f.root, schema); f.own(child)
    form = f.returned(f.root, child)
    changed = deepcopy(form)
    if fault == 'different_value': changed['field_0'][0]['rows'][0]['value']['solve_call_count'] += 1
    elif fault == 'extra_row': changed['field_0'].append(deepcopy(changed['field_0'][0]))
    else: changed['field_0'][0]['rows'][0]['value']['solve_call_count'] = 1.0
    with pytest.raises(ValueError): f.boundary.validate_received_report(child, changed, schema)


def test_duplicate_requested_source_fields_must_agree_and_unrelated_fields_grant_nothing(fixture):
    f = fixture
    schema = form_schema(SAVED_SOURCE, SAVED_SOURCE)
    child = f.child(f.root, schema); f.own(child)
    form = f.returned(f.root, child)
    assert form['field_0'] == form['field_1']
    form['field_1'] = []
    with pytest.raises(ValueError, match='conflicting_fields'):
        f.boundary.validate_received_report(child, form, schema)
    assert f.boundary.record_admission(f.root, {}, obj({}), 'not-an-operation') == []
    assert f.boundary.received_facts(f.root, obj({})) == {}
    assert not f.boundary.resolve_received(f.root, f.sheet['artifact_ref'], 'source')


@pytest.mark.parametrize('fault', ['missing_prefix', 'deleted_witness', 'changed_contract'])
def test_frozen_forwarding_cannot_rebuild_a_missing_original_prefix(fixture, fault):
    f = fixture
    schema = form_schema(SAVED_SOURCE)
    science = f.child(f.root, schema, role='scientific_process')
    child = f.child(science, schema); f.own(child)
    f.returned(science, child); f.returned(f.root, science)
    if fault == 'missing_prefix':
        row = f.journal.row('runtime_forms', science.episode_id)
        facts = json.loads(row['facts']); del facts['flux_balance_received_report_prefix']
        f.store.db.execute('UPDATE runtime_forms SET facts=? WHERE episode_id=?', (canonical(facts), science.episode_id))
    elif fault == 'deleted_witness':
        f.store.db.execute('DELETE FROM runtime_report_attempts WHERE parent_episode_id=?', (science.episode_id,))
    else:
        f.store.db.execute("UPDATE runtime_report_attempts SET contract='{}' WHERE parent_episode_id=?", (science.episode_id,))
    with pytest.raises(ValueError): f.boundary.authenticate_received_saved_sheet(f.root, f.sheet)


def test_readers_make_no_persistent_changes_or_observations(fixture):
    f = fixture
    schema = form_schema(*FACT_SOURCES)
    child = f.child(f.root, schema); f.own(child); f.returned(f.root, child)
    before = list(f.store.db.iterdump())
    f.boundary.authenticate_received_saved_sheet(f.root, f.sheet)
    f.boundary.received_facts(f.root, schema)
    f.boundary.validate_received_report(child,
        form_with_facts({}, schema, f.host.own_fact_groups(child, verify_artifacts=False)), schema)
    assert list(f.store.db.iterdump()) == before


def test_saved_selector_and_received_reference_permission_are_independent_requirements(fixture):
    f = fixture
    schema = form_schema(SAVED_SOURCE)
    child = f.child(f.root, schema); f.own(child); f.returned(f.root, child)
    saved = f.child(f.root, form_schema(PROJECTION_SOURCE), index=1, saved=f.sheet)
    assert f.boundary.authenticate_received_saved_sheet(saved, f.sheet) == (child.episode_id,)
    f.store.db.execute('DELETE FROM runtime_record_receipts WHERE episode_id=? AND record_ref=?',
        (f.root.episode_id, f.sheet['artifact_ref']))
    with pytest.raises(ValueError, match='not_received'):
        f.boundary.authenticate_received_saved_sheet(saved, f.sheet)


@pytest.mark.parametrize('profile', ['SBML', 'JSON'])
def test_original688_projection_numbers_are_forwarded_verbatim_without_new_science(fixture, profile):
    f = fixture
    path = (Path(__file__).resolve().parents[1] /
        ('verification/tool_graders_flux_balance_result_projection_2026-10-29_693/AUTHENTIC_688_' + profile + '_CHAIN_001.json'))
    f.projection = json.loads(path.read_text())['projection']
    child = f.child(f.root, form_schema(PROJECTION_SOURCE)); f.own(child)
    form = f.returned(f.root, child)
    assert form['field_0'] == [f.projection]
    assert [row['reaction_position'] for row in form['field_0'][0]['rows']] == [2, 0]
    assert [row['values']['flux']['flux']['value'] for row in form['field_0'][0]['rows']] == [10.0, 10.0]
    assert all(row['values']['flux']['unit']['basis'] == 'unknown' for row in form['field_0'][0]['rows'])
    assert not f.boundary.resolve_received(f.root, f.sheet['artifact_ref'], 'artifact')


@pytest.mark.parametrize('fault', [None, 'filled_selection', 'assignment_digest', 'invocation_digest',
    'invocation_identity', 'selected_assignment'])
def test_materialized_scientific_parent_retains_selected_slots_and_filled_invocation(fixture, fault):
    from gene_annotation_episode.scientific_process_records import scientific_digest, scientific_invocation_ref, selector_selection
    f = fixture
    science = f.child(f.root, form_schema(SAVED_SOURCE), role='scientific_process')
    def option(slot, name):
        return {'version': 'scientific_process_option_ref_v1', 'library_id': 'a' * 64,
            'slot': slot, 'option_id': name, 'entry_sha256': 'b' * 64}
    selection = {'version': 'scientific_process_selection_v3', 'evidence_axis': option('evidence_axis', 'A01'),
        'thought_pattern': option('thought_pattern', 'P01'), 'child_tool_info': [{
            'name': 'fixture.inspect', 'resources': 'local', 'description': 'Synthetic authority metadata.',
            'instructions': 'This is a fixture instruction, never invoked.'}]}
    assignment = {'selection': selection, 'evidence_refs': []}
    request = plain(science.request); request['message']['episode_assignment'] = deepcopy(assignment)
    schema = request['report_contract']['measurements']['schema']
    invocation = {'objective': request['goal']['objective'], 'scope': f.scope,
        'purpose': request['report_contract']['decision'], 'report_schema': schema, 'initial_report': {}}
    filled = {'version': 'filled_scientific_process_v1', 'selection': deepcopy(selection),
        'assignment_sha256': scientific_digest(assignment), 'invocation_sha256': scientific_digest(invocation),
        'mechanics_binding': {'fixture': 'not an executing scientific binding'}}
    request['message']['scientific_process'] = filled
    request['message']['scientific_invocation_ref'] = scientific_invocation_ref(f.run_id, science.path)
    science = replace(science, request=request, assignment=assignment); f.persist(science)
    action = json.loads(f.journal.row('runtime_actions', f.root.episode_id, 0)['action'])
    action['assignment'] = {**assignment, 'selection': selector_selection(selection)}
    f.store.db.execute('UPDATE runtime_actions SET action=? WHERE episode_id=? AND decision_index=0',
        (canonical(action), f.root.episode_id))
    child = f.child(science, form_schema(SAVED_SOURCE)); f.own(child)
    f.returned(science, child); f.returned(f.root, science)
    if fault == 'filled_selection': filled['selection']['thought_pattern']['option_id'] = 'P02'
    elif fault == 'assignment_digest': filled['assignment_sha256'] = '0' * 64
    elif fault == 'invocation_digest': filled['invocation_sha256'] = '0' * 64
    elif fault == 'invocation_identity': request['message']['scientific_invocation_ref'] = 'scientific_invocation_' + '0' * 24
    elif fault == 'selected_assignment':
        action['assignment']['evidence_refs'] = ['unselected']
        f.store.db.execute('UPDATE runtime_actions SET action=? WHERE episode_id=? AND decision_index=0',
            (canonical(action), f.root.episode_id))
    f.persist(replace(science, request=request))
    if fault is None:
        assert f.boundary.authenticate_received_saved_sheet(f.root, f.sheet) == (child.episode_id,)
    else:
        with pytest.raises(ValueError): f.boundary.authenticate_received_saved_sheet(f.root, f.sheet)


@pytest.mark.parametrize('source', FACT_SOURCES)
def test_exact_registered693_fact_forms_validate_and_unknown_values_do_not_escape(fixture, source):
    f = fixture
    schema = form_schema(source)
    assert validate_closed_schema(schema) == schema
    values = {PROJECTION_SOURCE: [f.projection], SAVED_SOURCE: [f.sheet], FAILURE_SOURCE: f.failures}
    form = {'field_0': values[source]}
    assert validate_form(form, schema, lambda *_: True) == form
    with pytest.raises(ReportBoundaryError): validate_form({'field_0': [{}]}, schema, lambda *_: True)


@pytest.mark.parametrize('fault', ['changed_shape', 'unknown_source', 'nested_binding'])
def test_registered693_fact_forms_reject_replacement_or_nested_contracts(fixture, fault):
    schema = form_schema(SAVED_SOURCE)
    if fault == 'changed_shape':
        schema['properties']['field_0']['items']['properties']['size_bytes']['type'] = 'number'
    elif fault == 'unknown_source': schema['properties']['field_0']['x-source'] = 'flux_balance_fabricated_confidence'
    else: schema = obj({'outer': schema})
    with pytest.raises(ReportBoundaryError): validate_closed_schema(schema)


def test_registered_saved_File_still_requires_actual_artifact_reference_resolution(fixture):
    f = fixture
    calls = []
    def unavailable(reference, namespace):
        calls.append((reference, namespace)); return False
    with pytest.raises(ReportBoundaryError):
        validate_form({'field_0': [f.sheet]}, form_schema(SAVED_SOURCE), unavailable)
    assert calls == [(f.sheet['artifact_ref'], 'artifact')]
