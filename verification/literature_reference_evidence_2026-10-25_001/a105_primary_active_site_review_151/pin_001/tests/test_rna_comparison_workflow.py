"""Shared Workflow integration using labeled synthetic original RNA reports."""
import asyncio
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import shutil

import pytest

from gene_annotation_episode.communication import plain, validate_form
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.numerical import NumericBand
from gene_annotation_episode.rna_structure_comparison_views import PROJECTION_SOURCE
from test_native_rna_structure_results_integration import history

SPEC = importlib.util.spec_from_file_location('rna_shared372',
    Path(__file__).parent / 'fixtures/rna_comparison_shared_372/helpers.py')
F = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(F)


def forbidden(*args, **kwargs):
    raise AssertionError('retained comparison reached native execution/acquisition')


def measurements(projection):
    payload = projection['payload']
    rows = payload['measurements'] if 'measurements' in payload else payload['rows'][0]['measurements']
    return {cell['metric']: cell['value'] for cell in rows}


@pytest.fixture(scope='module')
def pair_case(tmp_path_factory):
    with pytest.MonkeyPatch.context() as patch:
        case = F.workflow_case(tmp_path_factory.mktemp('comparison-pair'), patch)
        yield case
        case.store.close()


def test_actual_pair_energy_selected_structures_sites_and_scientific_forwarding(pair_case):
    case = pair_case
    energy, structures, sites = case.returned['comparison']
    assert measurements(energy) == {'baseline_native_energy': -4.0, 'variant_native_energy': -5.0, 'energy_delta': -1.0}
    assert [row['member_id'] for row in structures['payload']['rows']] == ['WT', 'A']
    assert [row['values'] for row in structures['payload']['rows']] == [[{
        'field': 'dot_bracket', 'state': 'present', 'value': value, 'reason': None}]
        for value in ('(((...)))', '((.....))')]
    assert [(row['baseline_index'], row['variant_index'], row['baseline_partner']['local_index'],
        row['variant_partner']['local_index'], row['change_indicator']['value']) for row in sites['payload']['rows']] == [
            (0, 0, 8, 8, 0), (6, 6, 2, None, 1)]
    assert sites['payload']['rows'][1]['transition'] == 'lost_pairing'
    assert sites['payload']['rows'][1]['variant_partner'] == {
        'state': 'unpaired', 'local_index': None, 'column': None, 'counterpart_index': None}
    assert 'input_paths' not in json.dumps(case.returned)
    assert case.body['anchor_handoff_ref'] == case.seeds[1].handoff
    assert case.selection['question']['membership'][0]['saved_input']['handoff_ref'] == case.seeds[0].handoff
    assert case.body['delivery_complete'] and case.returned['completed']
    for context in (case.science_context, case.root_context):
        assert case.owner.rna_structure_comparison_returns.received_facts(context, F.comparison_form())[PROJECTION_SOURCE] == case.returned['comparison']
        assert case.owner.initial_decision_context(context)['received_rna_comparison_values'] == [
            {'fact_source': PROJECTION_SOURCE, 'facts': case.returned['comparison']}]
    assert len(case.original_observations) == 2
    expected_refs = {member['saved_input'][key]
        for member in case.selection['question']['membership']
        for key in ('handoff_ref', 'source_ref', 'bundle_artifact_ref', 'sheet_artifact_ref')}
    assert set(case.owner.initial_references(case.comparison_context)) == expected_refs


def test_one_completed_collect_zero_new_acquisition_and_exact_practical_expectation(pair_case):
    case, context = pair_case, pair_case.comparison_context
    record = next(row for row in case.records if row['episode_id'] == context.episode_id)
    assert history(record) == [0]
    assert record['units_consumed'] == 1
    assert record['controller_state']['estimate']['expected_next_gain'] == NumericBand.exact(0).as_record()
    for row in case.records:
        args = (F.RUN_ID, row['episode_id'])
        assert case.store.db.execute('SELECT count(*) FROM runtime_actions WHERE run_id=? AND episode_id=?', args).fetchone()[0] == row['units_consumed']
        assert case.store.db.execute('SELECT count(*) FROM runtime_observations WHERE run_id=? AND episode_id=?', args).fetchone()[0] == row['units_consumed']
    proof = case.owner.completion_for_action(context, case.body['operation_key'])
    assert proof['validation_keys'] == ['selected_original_operand_authority', 'retained_operand_custody',
        'requested_comparison_projection_or_explicit_unavailability']
    assert case.owner.verify_completion(context, proof)
    credit = case.owner.project_credit(context, case.owner._selection(context))
    assert credit['credit'] == credit['new_handoff_count'] == credit['new_acquired_record_count'] == 0
    assert credit['operational_credit_binding']['scientific_credit'] is False
    assert credit['operational_credit_binding']['monitoring_credit'] is False
    assert case.store.count('native_execution') == case.store.count('observation') == 0
    assert case.owner.facts(context, {})['execution_result_origin'] is None


def test_received_identifier_resolution_and_internal_artifact_nonexpansion(pair_case):
    case = pair_case
    row = case.returned['comparison'][0]
    for context in (case.comparison_context, case.science_context, case.root_context):
        resolver = case.flow.resolver(context.scope, grain=context.role, context=context)
        assert resolver(row['result_receipt_key'], 'rna_comparison_receipt')
        assert resolver(row['calculation_key'], 'rna_comparison_calculation')
        assert not resolver(row['result_receipt_key'], 'artifact')
        assert not resolver(row['result_receipt_key'], 'rna_comparison_calculation')
        assert not resolver(case.body['comparison_sheet_artifact_ref'], 'artifact')
        assert not resolver(case.body['components_artifact_ref'], 'artifact')
        known = set(EpisodeReceipts(case.store, F.RUN_ID).known(context.episode_id))
        assert row['result_receipt_key'] not in known and row['calculation_key'] not in known
        assert case.body['components_artifact_ref'] not in known
    comparison_resolver = case.flow.resolver(case.scope, grain='results', context=case.comparison_context)
    for member in case.selection['question']['membership']:
        descriptor = member['saved_input']
        assert comparison_resolver(descriptor['handoff_ref'], 'execution_handoff')
        assert not comparison_resolver(descriptor['handoff_ref'], 'artifact')
        for field in ('source_ref', 'bundle_artifact_ref', 'sheet_artifact_ref'):
            assert not comparison_resolver(descriptor[field], 'execution_handoff')
    # Scientific forwarding delivered only selected comparison values to root.
    root_resolver = case.flow.resolver(case.scope, context=case.root_context)
    original = case.original_forms[0]['saved'][0]
    assert not root_resolver(original['sheet_artifact_ref'], 'artifact')
    assert not root_resolver(original['source_ref'], 'execution_result')


def test_replay_without_producer_files_preserves_original_receipts_and_observations(pair_case, monkeypatch):
    case, context = pair_case, pair_case.comparison_context
    before = [dict(row) for row in case.store.db.execute('SELECT * FROM runtime_observations ORDER BY episode_id,unit_index')]
    for seed in case.seeds:
        shutil.rmtree(seed.root)
    monkeypatch.setattr('gene_annotation_episode.native_rna_structure_results.capture_local_rna_structure_bundle', forbidden)
    monkeypatch.setattr('gene_annotation_episode.native_rna_structure_local.local_rna_structure_plan', forbidden)
    monkeypatch.setattr(case.owner.job_progress_provider.targets, 'observe_target', forbidden)
    monkeypatch.setattr('gene_annotation_episode.rna_structure_comparison_publication.run_local_job', forbidden)
    outcome = asyncio.run(case.owner.execute(context, 'execution.results.collect', {}, case.body['operation_key']))
    assert outcome['result'] == case.body and outcome['record_refs'] == []
    assert [dict(row) for row in case.store.db.execute('SELECT * FROM runtime_observations ORDER BY episode_id,unit_index')] == before
    assert case.owner.verify_completion(context, case.owner.completion_for_action(context, case.body['operation_key']))


def test_actual_compact_scan_rank_ties_gap_received_failure_absence_alias(tmp_path, monkeypatch):
    case = F.workflow_case(tmp_path, monkeypatch, scan=True)
    try:
        projection, = case.returned['comparison']
        assert measurements(projection) == {'baseline_rank_start': 2, 'baseline_rank_end': 3,
            'lowest_energy_tie_count': 1, 'baseline_energy_above_minimum': 1.0}
        population = projection['qualification']['population']
        assert population['declared_variant_count'] == 6 and population['comparable_variant_count'] == 3
        assert population['rank_population_count'] == 4 and population['alias_entry_count'] == 1
        assert population['received_failure_variant_count'] == population['not_tested_variant_count'] == population['not_supplied_variant_count'] == 1
        assert projection['qualification']['member_ids'] == ['WT']
        assert 'dot_bracket' not in json.dumps(case.returned) and 'input_paths' not in json.dumps(case.returned)
        assert len(json.dumps(case.returned).encode()) < 12000
        assert case.original_forms[-1]['failure'][0]['source_ref'] is None
        assert case.body['delivery_complete']
    finally:
        case.store.close()


def test_qualified_incompatible_result_completes_after_status_without_extra_turn(tmp_path, monkeypatch):
    case = F.workflow_case(tmp_path, monkeypatch, incompatible=True, status=True)
    try:
        context = case.comparison_context
        assert measurements(case.returned['comparison'][0])['energy_delta'] is None
        assert case.returned['comparison'][0]['delivery'] == 'qualified_unavailability'
        status = json.loads(case.flow.journal.row('runtime_actions', context.episode_id, 0)['result'])['result']
        assert status['tool_name'] == 'execution.results.status' and not status['delivery_complete']
        assert status['projection_rows'] == [] and status['components_artifact_ref'] is None
        assert case.owner.completion_for_action(context, status['operation_key']) is None
        assert case.owner.completion_for_action(context, case.body['operation_key'])
        record = next(row for row in case.records if row['episode_id'] == context.episode_id)
        assert history(record) == [0, 0] and record['units_consumed'] == 2
        assert record['controller_state']['estimate']['expected_next_gain'] == NumericBand.exact(0).as_record()
        assert len([call for call in case.calls if call['episode_id'] == context.episode_id]) == 2
    finally:
        case.store.close()


@pytest.mark.parametrize('custody', ['changed', 'missing'])
def test_changed_retained_sheet_records_one_failed_collect_without_native_retry(tmp_path, monkeypatch, custody):
    def forbid_native(case):
        monkeypatch.setattr('gene_annotation_episode.native_rna_structure_results.capture_local_rna_structure_bundle', forbidden)
        monkeypatch.setattr(case.owner.job_progress_provider.targets, 'observe_target', forbidden)
        monkeypatch.setattr('gene_annotation_episode.rna_structure_comparison_publication.run_local_job', forbidden)
    case = F.workflow_case(tmp_path, monkeypatch, corrupt=custody, before_comparison=forbid_native)
    try:
        assert case.body['delivery_complete'] is False
        assert case.body['projection_rows'] == case.body['selected_input_digests'] == []
        assert case.body['issues'][0]['code'] == ('retained_sheet_missing' if custody == 'missing' else 'retained_sheet_digest_mismatch')
        assert case.returned == {'comparison': [], 'completed': False}
        assert case.owner.completion_for_action(case.comparison_context, case.body['operation_key']) is None
        record = next(row for row in case.records if row['episode_id'] == case.comparison_context.episode_id)
        assert history(record) == [0] and record['units_consumed'] == 1
    finally:
        case.store.close()


def test_actual_earlier_child_cannot_use_later_received_descriptors(tmp_path, monkeypatch):
    case = F.workflow_case(tmp_path, monkeypatch, early=True)
    try:
        earlier = next(ctx for ctx in case.contexts.values() if ctx.path ==
            (('annotation', 'root'), ('scientific_process', 'child_0')))
        assignment = plain(case.comparison_context.assignment)
        assert case.owner.prepare_assignment(case.root_context, 'results', assignment, case.scope, 'future-selection') == assignment
        with pytest.raises(ValueError, match='saved_input_not_received|saved_operand_not_received|prefix'):
            case.owner.prepare_assignment(earlier, 'results', assignment, case.scope, 'earlier-selection')
        row = next(row for row in case.records if row['episode_id'] == earlier.episode_id)
        assert row['units_consumed'] == 0 and history(row) == []
        assert case.forms[earlier.episode_id] == {'comparison': [], 'saved': []}
    finally:
        case.store.close()
