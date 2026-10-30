"""One explicitly requested retained structure through the actual Workflow.

The original supplied-structure execution and provider action choices are
declared engineering fixtures. Retention, authorization, calculation, typed
delivery, accounting and provider presentation use production paths.
"""
import asyncio
from copy import deepcopy
import importlib.util
import json
from pathlib import Path

import pytest

from gene_annotation_episode.communication import plain
from gene_annotation_episode.decision_context import state_frame
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.execution_contracts import digest
from gene_annotation_episode.numerical import NumericBand
from gene_annotation_episode.rna_structure_comparison_contracts import validate_rna_comparison_selector
from gene_annotation_episode.rna_structure_comparison_prompt import rna_comparison_results_instructions
from gene_annotation_episode.rna_structure_comparison_views import PROJECTION_SOURCE
from test_native_rna_structure_results_integration import history, RUN_ID
from test_scientific_process_prompt_delivery import ScientificWire, OUTPUT_SCHEMA

ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / 'verification/tool_graders_rna_one_structure_workflow_2026-10-27_385'


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


F = module('rna_one_structure_385', PACKET / 'helpers.py')
baseline = module('gene_annotation_episode._rna_prompt_baseline_385',
    PACKET / 'baseline_rna_structure_comparison_prompt.py')


def parts(text):
    assert text.startswith('TASK\n\n') and text.count('\n\nSTEERING\n') == 1
    return text.split('\n\nSTEERING\n', 1)


@pytest.fixture(scope='module')
def one_case(tmp_path_factory):
    with pytest.MonkeyPatch.context() as patch:
        case = F.workflow_case(tmp_path_factory.mktemp('one-structure'), patch)
    yield case
    case.store.close()


def test_exact_single_saved_assignment_was_received_before_commission(one_case):
    case, evidence = one_case, one_case.evidence
    descriptor, = evidence.original_form['saved']
    assert descriptor == evidence.descriptor
    assert case.selection == F.selected_structure(descriptor)
    question = case.selection['question']
    assert question['kind'] == 'scan' and question['baseline_member_id'] == F.MEMBER
    assert question['membership'] == [{'member_id': F.MEMBER, 'kind': 'saved_sheet', 'saved_input': descriptor}]
    assert question['comparisons'] == []
    assert question['scan']['energy'] is None and question['scan']['topology_selection_ids'] == []
    assert case.selection['projections'] == [{'projection_id': 'requested-structure', 'family': 'structures',
        'member_ids': [F.MEMBER], 'fields': ['original_sequence', 'dot_bracket']}]
    parent = case.science_contexts[-1].episode_id
    row = case.store.db.execute('SELECT * FROM runtime_report_attempts WHERE run_id=? '
        'AND parent_episode_id=? AND decision_index=1', (RUN_ID, parent)).fetchone()
    assert json.loads(row['form']) == evidence.original_form and row['failure'] is None
    prefix = EpisodeReceipts(case.store, RUN_ID).manifest(case.comparison_context.episode_id)
    assert prefix['parent_episode_id'] == parent
    received, = [entry for entry in prefix['received_report_prefix']['attempts'] if entry['decision_index'] == 1]
    assert received == {'decision_index': 1, 'delivery_ref': row['delivery_ref'],
        'child_episode_id': row['child_episode_id'], 'contract_sha256': digest(json.loads(row['contract'])),
        'form_sha256': digest(evidence.original_form)}
    assert set(case.owner.initial_references(case.comparison_context)) == {
        descriptor[key] for key in ('handoff_ref', 'source_ref', 'bundle_artifact_ref', 'sheet_artifact_ref')}


def test_exact_two_requested_strings_and_no_other_scientific_outputs(one_case):
    case = one_case
    projection, = case.projections
    assert projection['family'] == 'structures'
    row, = projection['payload']['rows']
    assert row['member_id'] == F.MEMBER
    assert row['structure_origin'] == 'supplied_unknown'
    assert row['values'] == [
        {'field': 'original_sequence', 'state': 'present', 'value': 'GGGAAACCC', 'reason': None},
        {'field': 'dot_bracket', 'state': 'present', 'value': '(((...)))', 'reason': None}]
    assert set(case.returned[-1]) == {F.FIELD, 'completed'} and case.returned[-1]['completed'] is True
    assert case.forwarded == [{F.FIELD: case.projections}]
    assert case.owner.rna_structure_comparison_returns.received_facts(
        case.root_context, F.parent_form(completed=False))[PROJECTION_SOURCE] == case.projections
    assert case.body['delivery_complete']
    sheet = json.loads(case.store.get_artifact(case.body['comparison_sheet_artifact_ref']))
    components = json.loads(case.store.get_artifact(case.body['components_artifact_ref']))
    assert sheet['selected_question'] == case.selection['question']
    assert len(sheet['operands']) == 1 and sheet['comparisons'] == []
    assert sheet['operands'][0]['original_sheet']['original_input']['energy_mode'] == 'none'
    assert sheet['operands'][0]['original_sheet']['model'] is None
    assert components['comparisons'] == []
    assert components['scan']['energy_components'] == components['scan']['site_components'] == []
    assert components['scan']['baseline_rank_class'] == 'not_requested'
    member, = components['scan']['members']
    assert member['energy_state'] == 'not_requested'
    assert member['energy'] is member['delta'] is member['exact_rank_start'] is member['exact_rank_end'] is None
    (case.directory / 'retained-comparison-sheet.json').write_text(json.dumps(sheet, indent=2) + '\n')
    (case.directory / 'retained-comparison-components.json').write_text(json.dumps(components, indent=2) + '\n')


def test_one_collect_one_observation_no_new_native_work_or_source_credit(one_case):
    case, context, evidence = one_case, one_case.comparison_context, one_case.evidence
    record = next(row for row in case.records if row['episode_id'] == context.episode_id)
    assert history(record) == [0] and record['units_consumed'] == 1
    assert record['controller_state']['estimate']['expected_next_gain'] == NumericBand.exact(0).as_record()
    assert len(evidence.calls) == 1
    for item in case.records:
        for table in ('runtime_actions', 'runtime_observations'):
            count = case.store.db.execute(f'SELECT count(*) FROM {table} WHERE run_id=? AND episode_id=?',
                (RUN_ID, item['episode_id'])).fetchone()[0]
            assert count == item['units_consumed']
    assert case.store.count('source') == evidence.source_count
    assert case.store.count('native_execution') == evidence.native_count
    assert case.store.count('observation') == case.store.count('annotation') == 0
    assert not Path(case.plan['identity']['execution_id']).exists()
    assert not Path(case.job['operands'][0]['path']).exists()
    assert evidence.original_receipt_path.read_bytes() == evidence.original_receipt
    assert case.store.get_artifact(evidence.descriptor['sheet_artifact_ref']) == evidence.original_sheet
    observed = [dict(row) for row in case.store.db.execute(
        'SELECT * FROM runtime_observations ORDER BY episode_id,unit_index')
        if row['episode_id'] in evidence.original_episode_ids]
    assert observed == evidence.old_observations
    proof = case.owner.completion_for_action(context, case.body['operation_key'])
    assert proof['validation_keys'] == ['selected_original_operand_authority', 'retained_operand_custody',
        'requested_comparison_projection_or_explicit_unavailability']
    assert case.owner.verify_completion(context, proof)
    credit = case.owner.project_credit(context, case.owner._selection(context))
    assert credit['credit'] == credit['new_handoff_count'] == credit['new_acquired_record_count'] == 0
    assert credit['operational_credit_binding']['scientific_credit'] is False
    assert credit['operational_credit_binding']['monitoring_credit'] is False
    assert case.owner.facts(context, {})['execution_result_origin'] is None
    F.write_json(case.directory / 'ACCOUNTING_AND_COMPLETION.json', {'record': record,
        'proof': proof, 'credit': credit, 'source_count_before': evidence.source_count,
        'source_count_after': case.store.count('source'), 'native_count_before': evidence.native_count,
        'native_count_after': case.store.count('native_execution'), 'original_observations': observed})


def test_replay_preserves_receipt_and_adds_no_worker_or_observation(one_case, monkeypatch):
    case = one_case
    before = [dict(row) for row in case.store.db.execute('SELECT * FROM runtime_observations ORDER BY episode_id,unit_index')]
    monkeypatch.setattr('gene_annotation_episode.native_rna_structure_results.capture_local_rna_structure_bundle', F.denied)
    monkeypatch.setattr('gene_annotation_episode.native_rna_structure_local.local_rna_structure_plan', F.denied)
    monkeypatch.setattr(case.owner.job_progress_provider.targets, 'observe_target', F.denied)
    monkeypatch.setattr('gene_annotation_episode.rna_structure_comparison_publication.run_local_job', F.denied)
    result = asyncio.run(case.owner.execute(case.comparison_context, 'execution.results.collect', {}, case.body['operation_key']))
    assert result['result'] == case.body and result['record_refs'] == result['changed_record_refs'] == []
    assert [dict(row) for row in case.store.db.execute('SELECT * FROM runtime_observations ORDER BY episode_id,unit_index')] == before


def test_actual_provider_task_truthfully_requests_one_retained_structure(one_case):
    case = one_case
    call, = case.evidence.calls
    turn, = case.evidence.wire.turns_sent()
    task, steering = parts(turn['input'][0]['text'])
    assert F.OPENING in task
    assert "Compare the retained RNA inputs against" not in task
    assert '0 baseline-to-canonical-variant comparisons' in task
    assert 'original sequence' in task and 'dot-bracket' in task
    assert F.FIELD in task and 'execution.results.collect' in task and 'execution.results.status' in task
    assert turn['outputSchema'] == call['schema']
    assert call['context']['execution_assignment'] == case.evidence.assignment
    request = json.loads((case.directory / 'actual-provider-wire/call-00001/request.json').read_text())
    assert request['context'] == call['context'] and request['instructions'] == call['instructions']
    assert request['input'] == turn['input']
    assert 'GGGAAACCC' not in steering and '(((...)))' not in steering
    for private in (case.evidence.descriptor['sheet_sha256'], case.projections[0]['result_receipt_key'], 'input_paths'):
        assert private not in task + steering


def test_actual_status_update_and_provider_frames_keep_full_task(tmp_path, monkeypatch):
    case = F.workflow_case(tmp_path / 'status-then-collect', monkeypatch, status=True)
    try:
        first, second = case.evidence.calls
        actual = case.evidence.wire.turns_sent()
        assert len(actual) == 2 and parts(actual[0]['input'][0]['text'])[0] == parts(actual[1]['input'][0]['text'])[0]
        assert '| execution.results.status | completed | false |' in parts(actual[1]['input'][0]['text'])[1]
        update = state_frame(second['context'], first['context'])
        assert 'execution_assignment' not in update['fields']
        reply = {'status': 'completed', 'result': case.body}
        lookup = {'version': 'decision_context_v1', 'kind': 'decision_lookup_result', 'result': reply}
        restored = state_frame(second['context'])
        restored.update(restored_pending_decision_index=1, restored_public_exchanges=[{'lookup_result': reply}])
        wire, fresh = ScientificWire(tmp_path / 'framed-wire'), ScientificWire(tmp_path / 'restored-wire')
        async def exercise():
            for frame in (state_frame(first['context']), update, lookup):
                await wire.complete('one-structure-frame', 'REASONING', first['instructions'], frame, OUTPUT_SCHEMA)
            await fresh.complete('one-structure-frame', 'REASONING', second['instructions'], restored, OUTPUT_SCHEMA)
        asyncio.run(exercise())
        turns = wire.turns_sent() + fresh.turns_sent()
        assert len({parts(turn['input'][0]['text'])[0] for turn in turns}) == 1
        assert all(F.OPENING in parts(turn['input'][0]['text'])[0] for turn in turns)
        assert turns[2]['input'] == turns[3]['input']
        assert all(turn['outputSchema'] == OUTPUT_SCHEMA for turn in turns)
        assert 'GGGAAACCC' in turns[2]['input'][0]['text'] and '(((...)))' in turns[2]['input'][0]['text']
        assert sum(method == 'thread/start' for method, _ in wire.sent) == 1
        record = next(row for row in case.records if row['episode_id'] == case.comparison_context.episode_id)
        assert history(record) == [0, 0] and record['units_consumed'] == 2
        assert record['controller_state']['estimate']['expected_next_gain'] == NumericBand.exact(0).as_record()
        for index, turn in enumerate(turns):
            (case.directory / f'FRAMED_PROVIDER_TURN_{index:03d}.txt').write_text(turn['input'][0]['text'] + '\n')
    finally:
        case.store.close()


@pytest.mark.parametrize('fields', [
    ['original_sequence', 'dot_bracket'], ['dot_bracket', 'original_sequence'], ['dot_bracket'],
    ['original_sequence'], ['pairs'], ['analysis_sequence', 'pairs', 'dot_bracket', 'original_sequence']])
def test_structure_only_opening_accepts_any_valid_field_subset_and_order(one_case, fields):
    assignment = deepcopy(one_case.evidence.assignment)
    assignment['selector'] = F.selected_structure(one_case.evidence.descriptor, fields)
    text = rna_comparison_results_instructions(assignment)
    assert text.startswith(F.OPENING + '\n')
    old = baseline.rna_comparison_results_instructions(assignment)
    assert text.split('\n', 1)[1] == old.split('\n', 1)[1]


@pytest.mark.parametrize('kind', ['pair', 'scan'])
def test_existing_actual_pair_and_scan_task_are_byte_identical(kind):
    file = ROOT / 'verification/tool_graders_rna_comparison_shared_integration_2026-10-26_372' / (
        'FILLED_ACTUAL_PAIR_001.json' if kind == 'pair' else 'FILLED_ACTUAL_SCAN_001.json')
    case = json.loads(file.read_text())['workflow_case']
    assignment = {'version': 'execution_results_assignment_v1', 'handoff_ref': case['body']['anchor_handoff_ref'],
        'selector': case['selector']}
    assert rna_comparison_results_instructions(assignment) == baseline.rna_comparison_results_instructions(assignment)


@pytest.mark.parametrize('change', ['energy', 'alias', 'non_structure_projection', 'second_structure_projection'])
def test_narrow_mode_boundary_preserves_other_scan_wording(one_case, change):
    assignment = deepcopy(one_case.evidence.assignment)
    selected = assignment['selector']
    if change == 'energy':
        selected['question']['scan']['energy'] = F.shared372.b.energy_request()
    elif change == 'alias':
        selected['question']['membership'].append({'member_id': 'alias', 'kind': 'alias', 'canonical_member_id': F.MEMBER})
    elif change == 'non_structure_projection':
        selected['projections'].append({'projection_id': 'eligibility', 'family': 'scan_members',
            'scan_id': selected['question']['scan']['scan_id'], 'members': {'kind': 'explicit', 'member_ids': [F.MEMBER]},
            'fields': ['eligibility'], 'order': 'declared', 'limit': None})
    else:
        selected['projections'].append({'projection_id': 'second-explicit-projection', 'family': 'structures',
            'member_ids': [F.MEMBER], 'fields': ['dot_bracket']})
    validate_rna_comparison_selector(selected)
    actual = rna_comparison_results_instructions(assignment)
    if change == 'second_structure_projection':
        assert actual.startswith(F.OPENING)
    else:
        assert actual == baseline.rna_comparison_results_instructions(assignment)
