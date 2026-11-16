"""Actual nested forms, retained-custody boundaries and saved RNA calculations."""
import asyncio
from copy import deepcopy
from dataclasses import replace
import json

import pytest

from gene_annotation_episode.episodic_workflow.root.communication import plain, validate_form
from gene_annotation_episode.episodic_workflow.root.episode_receipts import EpisodeReceipts
from gene_annotation_episode.episodic_workflow.root.library.rna_structure_result_views import FAMILY_SOURCES
from test_native_rna_structure_results_integration import (
    RUN_ID, assert_accounting, history, result_form, selector, values, workflow_case)


def forbid(*args, **kwargs):
    raise AssertionError('saved-sheet calculation attempted native execution, acquisition, parsing or network access')


def test_failed_native_energy_keeps_exact_topology_and_qualified_delivery(tmp_path):
    chosen = selector(metrics=['pair_count', 'paired_fraction', 'evaluated_energy_kcal_mol'])
    case = workflow_case(tmp_path, prediction=False, energy=True, failed=True, selection=chosen, terminal_status=True,
        results_fields=('summary', 'failure', 'references', 'saved'), parent_fields=('summary', 'failure'))
    try:
        body = case.outcomes[0]['result']
        assert not body['native_success'] and body['capture_complete'] and body['delivery_complete']
        assert body['observation']['state'] == 'failed'
        targets = case.owner.job_progress_provider.targets
        assert targets.returnable_handoff(body['target']) and not targets.usable_handoff(body['target'])
        assert case.owner.completion_for_action(case.contexts[case.by_role['launch_local'][0]['episode_id']],
            case.plan['identity']['operation_key']) is None
        returned, = case.returned
        row, = returned['summary']
        assert returned['completed'] and values(row) == {'pair_count': 1, 'paired_fraction': 2 / 3}
        unavailable, = row['unavailable']
        assert unavailable['name'] == 'evaluated_energy_kcal_mol'
        assert unavailable['state'] == 'failed' and unavailable['reason'] == 'rna_native_failed'
        assert any(failure['issue']['code'] == 'rna_native_failed' for failure in returned['failure'])
        sheet = json.loads(case.store.get_artifact(body['prepared']['sheet_artifact_ref']))
        assert [(pair['i'], pair['j']) for pair in sheet['topology']['pairs']] == [(0, 2)]
        assert sheet['original_input']['dot_bracket'] == '(.)'
        bundle = json.loads(case.store.get_artifact(body['capture']['bundle_artifact_ref']))
        assert bundle['native_status'] == 'partial' and bundle['returncode'] == 1
        stdout = next(item for item in body['capture']['artifacts'] if item['role'] == 'stdout')
        raw = [json.loads(line) for line in case.store.get_artifact(stdout['artifact_ref']).decode().splitlines()]
        assert next(item for item in raw if item['schema'] == 'rna_raw_native_return_v1')['energy_repr'] == '100000.0'
        assert case.owner.facts(case.result_contexts[0], None)['execution_result_origin'] is None
        proof = case.owner.completion_for_action(case.result_contexts[0], body['operation_key'])
        assert proof and case.owner.verify_completion(case.result_contexts[0], proof)
        assert case.forwarded == [{key: returned[key] for key in ('summary', 'failure')}]
        assert_accounting(case)
    finally:
        case.store.close()


@pytest.fixture(scope='module')
def nested_case(tmp_path_factory):
    case = workflow_case(tmp_path_factory.mktemp('nested-rna-boundaries'), prediction=False, nested=True,
        results_fields=('summary', 'references', 'saved'), parent_fields=('summary',))
    yield case
    case.store.close()


def test_nested_forwarding_preserves_exact_requested_numbers_and_closed_histories(nested_case):
    case = nested_case
    original = case.returned[0]['summary']
    assert case.forwarded == [{'summary': original}, {'summary': original}]
    for context in [*case.science_contexts, case.root_context]:
        groups = case.owner.native_rna_structure_returns.received_context(context)
        assert next(row['facts'] for row in groups if row['fact_source'] == FAMILY_SOURCES['summary']) == original
        case.owner.validate_received_report(context, {'summary': original}, result_form(('summary',), completed=False))
        assert case.owner.initial_decision_context(context)['received_rna_structure_values'] == groups
    assert history(case.by_role['scientific_process'][0]) == [0]
    assert_accounting(case)


def test_numerical_source_does_not_grant_retained_artifacts_or_unrequested_fields(nested_case):
    case = nested_case
    body = case.outcomes[0]['result']
    source, sheet = body['source_ref'], body['prepared']['sheet_artifact_ref']
    for context in (case.root_context, case.science_contexts[0]):
        resolver = case.flow.resolver(context.scope, grain=context.role, context=context)
        assert resolver(source, 'execution_result')
        assert not resolver(sheet, 'artifact')
        assert not resolver(body['capture']['bundle_artifact_ref'], 'artifact')
        assert sheet not in EpisodeReceipts(case.store, RUN_ID).known(context.episode_id)
        bad = deepcopy(case.forwarded[0])
        bad['summary'][0]['measurements'][0]['value'] += 1
        with pytest.raises(ValueError, match='returned_facts_conflict'):
            case.owner.validate_received_report(context, bad, case.science_form)
        with pytest.raises(ValueError):
            validate_form({**case.forwarded[0], 'saved': case.returned[0]['saved']}, case.science_form, resolver)
        with pytest.raises(ValueError, match='saved_input_not_received'):
            case.owner.native_rna_structure_returns.resolve_saved_rna_input(context, case.returned[0]['saved'][0])
    # The immediate scientific parent did explicitly request the descriptor.
    assert case.owner.resolve_received_reference(case.science_contexts[1], sheet, 'artifact')


def test_actual_original_commission_scope_and_receipt_forgery_are_rejected(nested_case):
    case = nested_case
    context = case.result_contexts[0]
    descriptor = deepcopy(case.returned[0]['saved'][0])
    descriptor['sheet_sha256'] = '0' * 64
    with pytest.raises(ValueError, match='saved_descriptor_conflict'):
        case.owner.native_rna_structure_returns.resolve_saved_rna_input(case.science_contexts[-1], descriptor)
    wrong = plain(context.assignment)
    wrong['selector']['projection']['metrics'] = ['pair_count']
    with pytest.raises(ValueError):
        case.owner.native_rna_structure_returns.authenticate(replace(context, assignment=wrong))
    with pytest.raises(ValueError):
        case.owner.native_rna_structure_returns.authenticate(replace(context, scope={'subject_refs': []}))
    body = deepcopy(case.outcomes[0]['result'])
    body['operation_key'] += ':forged'
    with pytest.raises((ValueError, TypeError, OSError)):
        case.owner.native_rna_structure_results._validate_body(body, case.scope)


def test_original_action_replay_keeps_receipt_and_observation_history(nested_case, monkeypatch):
    case = nested_case
    body = case.outcomes[0]['result']
    directory = case.owner.native_rna_structure_results._saved_directory(body['episode_id'], body['operation_key'])
    original = (directory / 'receipt.json').read_bytes()
    history_before = [dict(row) for row in case.store.db.execute('SELECT * FROM runtime_observations ORDER BY episode_id,unit_index')]
    monkeypatch.setattr('gene_annotation_episode.episodic_workflow.root.native_rna_structure_results.capture_local_rna_structure_bundle', forbid)
    monkeypatch.setattr(type(case.owner.job_progress_provider.targets), 'observe_target', forbid)
    replay = asyncio.run(case.owner.execute(case.result_contexts[0], 'execution.results.collect', {}, body['operation_key']))
    assert replay['result'] == body
    assert (directory / 'receipt.json').read_bytes() == original
    assert [dict(row) for row in case.store.db.execute('SELECT * FROM runtime_observations ORDER BY episode_id,unit_index')] == history_before
    assert_accounting(case)


def test_later_actual_sibling_cannot_supply_an_earlier_frozen_child(tmp_path):
    case = workflow_case(tmp_path, prediction=False, early_sibling=True,
        results_fields=('summary', 'saved'), parent_fields=('summary', 'saved'))
    try:
        early, later = case.science_contexts
        descriptor, = case.returned[0]['saved']
        assert case.forwarded[0] == {'summary': [], 'saved': []}
        assert case.forwarded[1]['summary'] == case.returned[0]['summary']
        assert case.owner.native_rna_structure_returns.resolve_saved_rna_input(case.root_context, descriptor)
        with pytest.raises(ValueError, match='saved_input_not_received'):
            case.owner.native_rna_structure_returns.resolve_saved_rna_input(early, descriptor)
        resolver = case.flow.resolver(early.scope, grain=early.role, context=early)
        assert not resolver(descriptor['source_ref'], 'execution_result')
        assert not resolver(descriptor['sheet_artifact_ref'], 'artifact')
        assert history(case.by_role['scientific_process'][0]) == []
        assert case.store.db.execute('SELECT count(*) FROM runtime_actions WHERE episode_id=?', (early.episode_id,)).fetchone()[0] == 0
        assert case.store.db.execute('SELECT count(*) FROM runtime_observations WHERE episode_id=?', (early.episode_id,)).fetchone()[0] == 0
        assert history(case.by_role['scientific_process'][1]) == [0, 0]
        assert history(case.by_role['annotation'][0]) == [0, 0]
    finally:
        case.store.close()
