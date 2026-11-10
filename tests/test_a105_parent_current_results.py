"""Retained A105 parent failure: current science without historical form copies."""
from copy import deepcopy

from gene_annotation_episode.decision_context import state_frame
from gene_annotation_episode.domain import canonical
from gene_annotation_episode.literature_current_results import (
    current_findings_view, current_scoring_view,
)
from inspect_a105_parent_prompt import (
    recomputed_completed_work, replay_input, retained_input, retained_work_receipts,
    scientific_inventory, validate_scientific_presentation,
)


def test_original_rejected_frame_preserves_current_results_in_actual_provider_presentation():
    trace = retained_input()
    before = deepcopy(trace)
    prompt, _instructions = replay_input(trace)
    inventory = validate_scientific_presentation(prompt, trace)
    assert trace == before
    assert trace['original_input_matches_sent']
    assert len(trace['sent_text']) == 1052431
    assert len(trace['state']['child_reports']) == 30
    assert inventory['current_main_sheets'] == 16
    assert inventory['current_subscoring_sheets'] == 10
    assert inventory['received_typed_findings'] == 6
    assert 'Admitted requested child returns' not in prompt
    # The task may still advertise an existing legal return-source name. Its
    # cumulative visibility inventories must not be retransmitted as steering.
    assert 'interpretation_basis_refs' not in prompt.partition('\nSTEERING\n')[2]
    # This measures the corrected presentation against the observed failure;
    # it does not introduce any runtime or scientific continuation cutoff.
    assert len(prompt) < len(trace['sent_text'])


def test_current_sheet_view_preserves_every_exact_cell_and_distinct_owner_use():
    trace = retained_input()
    main, subscoring, _findings = scientific_inventory(trace)
    original = trace['state']['literature_current_scoring_sheets']
    before = deepcopy(original)
    view = current_scoring_view(original)
    assert original == before
    assert len(view) == len(main) + len(subscoring) == 26
    by_ref = {sheet['sheet_ref']: sheet for sheet in view}
    for reference, sheet in {**main, **subscoring}.items():
        assert {canonical(cell) for cell in by_ref[reference]['cells']} == {
            canonical(cell) for cell in sheet['cells']}
    for reference, sheet in subscoring.items():
        actual_uses = {main_sheet['sheet_ref'] for main_sheet in main.values()
                       if reference in {grade['sheet_ref'] for grade in main_sheet['subscoring_sheets']}}
        assert set(by_ref[reference]['main_sheet_refs']) == actual_uses


def test_parent_completed_work_uses_all_original_actions_and_credit_receipts():
    receipts = retained_work_receipts()
    before = deepcopy(receipts)
    work = recomputed_completed_work()
    assert receipts == before
    assert len(receipts['tables']['runtime_actions']) == 31
    assert len(receipts['tables']['runtime_observations']) == 31
    assert len(receipts['tables']['runtime_report_attempts']) == 30
    assert sum(row['original_action_count'] for row in work) == 31
    assert sum(row['credit_receipts'] for row in work) == 31
    assert sum(row['earned_credit'] for row in work) == 4
    children = [row for row in work if row['operation'].startswith('Receive child investigation:')]
    assert len(children) == 30
    assert all(row['inputs'].get('question') for row in children)
    assert all(row['returned_result'] for row in children)


def test_source_finding_replacement_is_preserved_without_rejudging_revision_validity():
    working = retained_input()['state']['working_state']
    records = working['assessments']
    before = deepcopy(records)
    findings = current_findings_view(records, working['received_revision_status'])
    assert records == before
    assert len(findings) == len(records) == 6
    by_ref = {row['id']: row for row in findings}
    for record in records:
        assert all(by_ref[record['id']][key] == value for key, value in record.items())
    old = by_ref['assessment_8920799fb9e8b323926d7b42']
    new = by_ref['assessment_4b9bd87c0917d635ae4c203e']
    assert old['received_revision_status'] is True and new['received_revision_status'] is True
    assert old['replaced_by_refs'] == [new['id']]
    assert new['investigation_finding']['replaces_refs'] == [old['id']]
    assert old['investigation_finding']['qualification']['kind'] == 'different_source_subject'
    assert new['investigation_finding']['qualification']['kind'] == 'measurement_does_not_establish_claim'


def test_repeated_old_reference_inventories_do_not_change_current_parent_message():
    trace = deepcopy(retained_input())
    original, _ = replay_input(trace)
    for report in trace['state']['child_reports']:
        report['interpretation_basis_refs'] = report.get('interpretation_basis_refs', []) * 3
    last = trace['state']['last_local_outcome']
    if isinstance(last.get('record_refs'), list):
        last['record_refs'] *= 3
    if isinstance(last.get('result'), dict) and isinstance(last['result'].get('record_refs'), list):
        last['result']['record_refs'] *= 3
    trace['context'] = state_frame(trace['state'])
    repeated, _ = replay_input(trace)
    assert repeated == original
    validate_scientific_presentation(repeated, trace)
