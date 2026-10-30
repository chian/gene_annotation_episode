"""Exact schemas, routing description, authority and typed-return negatives."""
from copy import deepcopy
from dataclasses import replace
import json

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode.communication import plain
from gene_annotation_episode.execution_progress import describe_execution_target
from gene_annotation_episode.rna_structure_comparison_contracts import RNA_COMPARISON_SELECTOR_SCHEMA
from gene_annotation_episode.rna_structure_result_views import RESULT_SELECTOR_SCHEMA
from test_rna_comparison_workflow import F, forbidden, pair_case


def test_aggregate_schema_preserves_old_variants_and_rejects_bad_new_shape(pair_case):
    schema = pair_case.owner.assignment_schema('results')['properties']['selector']
    branches = schema['allOf'][0]['then']['oneOf']
    assert branches == [*RESULT_SELECTOR_SCHEMA['oneOf'], RNA_COMPARISON_SELECTOR_SCHEMA]
    Draft202012Validator(schema).validate(pair_case.selection)
    bad = deepcopy(pair_case.selection)
    bad['unrequested'] = True
    assert not Draft202012Validator(schema).is_valid(bad)
    bad['version'] = 'native_rna_structure_comparison_selector_unknown'
    with pytest.raises(ValueError):
        pair_case.owner._selector({'selector': bad}, pair_case.owner._target(pair_case.comparison_context))


def test_retained_descriptor_is_exact_and_never_observes_or_calls_old_selector(pair_case, monkeypatch):
    case = pair_case
    reader = case.owner.job_progress_provider.targets
    monkeypatch.setattr(reader, 'observe_target', forbidden)
    monkeypatch.setattr('gene_annotation_episode.rna_structure_result_views.validate_rna_structure_result_selector', forbidden)
    actual = reader.describe_target(case.seeds[1].handoff, case.scope, selector=case.selection)
    assert set(actual) == {'resource_kind', 'service_or_program', 'operation', 'mode', 'output_format',
        'called_operation', 'routing_anchor', 'result_selector_schema', 'result_selection', 'status_operations',
        'acquisition_operations', 'status_meanings', 'extractors'}
    assert actual['called_operation'] is None and actual['mode'] == 'pairwise'
    assert actual['result_selection'] == case.selection
    assert actual['routing_anchor'] == {'handoff_ref': case.seeds[1].handoff,
        'original_operation': describe_execution_target(reader.read_target(case.seeds[1].handoff, case.scope))}
    assert actual['status_meanings'] == {'observation_basis': 'selected_retained_inputs_and_original_receipts',
        'fresh_native_observation': False, 'anchor_is_baseline': False,
        'scientific_result_validation': 'authenticated_inputs_and_recomputed_projection'}
    assert actual['extractors'][1]['return_fact_sources'] == ['execution_rna_structure_comparison_projections']
    assert actual['extractors'][1]['calculation_basis'] == 'authenticated_multiple_saved_inputs'
    assert [row['name'] for row in case.owner.catalog(case.comparison_context)] == ['execution.results.status', 'execution.results.collect']


@pytest.mark.parametrize('field', ['number', 'receipt', 'selection', 'namespace'])
def test_forged_forwarding_fails_against_original_comparison_receipt(pair_case, field):
    case = pair_case
    form = {'comparison': deepcopy(case.returned['comparison'])}
    row = form['comparison'][0]
    if field == 'number':
        row['payload']['rows'][0]['measurements'][2]['value'] = 900
    elif field == 'receipt':
        row['result_receipt_key'] = 'rna_comparison_receipt:' + '0' * 64
    elif field == 'selection':
        row['selection']['metrics'] = ['energy_delta']
    else:
        row['calculation_key'] = row['result_receipt_key']
    with pytest.raises(ValueError):
        case.owner.validate_received_report(case.root_context, form, F.comparison_form(completed=False))


@pytest.mark.parametrize('field', ['assignment', 'scope', 'descriptor', 'handoff'])
def test_parent_selection_and_child_context_tampering_do_not_gain_authority(pair_case, field):
    case = pair_case
    assignment = plain(case.comparison_context.assignment)
    if field == 'assignment':
        assignment['selector']['projections'][0]['metrics'] = ['energy_delta']
        with pytest.raises(ValueError):
            case.owner.initialize(replace(case.comparison_context, assignment=assignment))
    elif field == 'scope':
        with pytest.raises(ValueError):
            case.owner.initialize(replace(case.comparison_context, scope={'subject_refs': []}))
    else:
        if field == 'descriptor':
            assignment['selector']['question']['membership'][0]['saved_input']['sheet_sha256'] = '0' * 64
        else:
            assignment['handoff_ref'] = case.original_forms[0]['saved'][0]['source_ref']
        with pytest.raises(ValueError):
            case.owner.prepare_assignment(case.science_context, 'results', assignment, case.scope, 'not-an-action')


def test_root_source_possession_is_not_received_descriptor_authority(pair_case):
    case = pair_case
    assignment = plain(case.comparison_context.assignment)
    # Root knows original handoffs as caller inputs, and Store retains all bytes.
    # Its child's original descriptor forms were never forwarded to root.
    with pytest.raises(ValueError, match='saved_input_not_received'):
        case.owner.prepare_assignment(case.root_context, 'results', assignment, case.scope, 'not-an-action')


def test_old_single_saved_selector_still_rejects_different_handoff(pair_case):
    case = pair_case
    descriptor = deepcopy(case.original_forms[0]['saved'][0])
    with pytest.raises(ValueError, match='saved_assignment_conflict'):
        case.owner.native_rna_structure_returns.resolve_saved_rna_input(case.comparison_context, descriptor)


def test_rehashed_forged_numerical_result_is_recomputed_at_actual_receipt_read(pair_case):
    from test_rna_structure_comparison_publication import rehash_output_chain
    case = pair_case
    adapter, context = case.owner.rna_structure_comparison_results, case.comparison_context
    directory = adapter._saved_directory(context.episode_id, case.body['operation_key'])
    receipt_path, prepared_path = directory / 'receipt.json', directory / 'grading/prepared.json'
    old_receipt, old_prepared = receipt_path.read_bytes(), prepared_path.read_bytes()
    saved_action = case.flow.journal.row('runtime_actions', context.episode_id, 0)['result']
    prepared = json.loads(old_prepared)
    def change(rows):
        rows[0]['payload']['rows'][0]['measurements'][2]['value'] = 600.0
    forged = rehash_output_chain(case.store, prepared, role='projections', transform=change)
    body = deepcopy(case.body)
    body['projection_rows'] = forged['projection_rows']
    outcome = json.loads(saved_action)
    outcome['result'] = body
    try:
        receipt_path.write_bytes(F.encoded(body))
        prepared_path.write_bytes(F.encoded(forged))
        case.store.db.execute('UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? AND decision_index=0',
            (F.canonical(outcome), F.RUN_ID, context.episode_id))
        with pytest.raises(ValueError):
            adapter.read_result(context, body)
    finally:
        receipt_path.write_bytes(old_receipt)
        prepared_path.write_bytes(old_prepared)
        case.store.db.execute('UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? AND decision_index=0',
            (saved_action, F.RUN_ID, context.episode_id))
    assert adapter.read_result(context, case.body) == case.body


def test_actual_source_only_returns_cannot_authorize_saved_operands(tmp_path, monkeypatch):
    holder = {}
    def before(case):
        holder['case'] = case
        assert all(set(form) == {'references', 'completed'} for form in case.original_forms)
    try:
        with pytest.raises(AssertionError, match='saved_input_not_received|saved_operand_not_received'):
            F.workflow_case(tmp_path, monkeypatch, source_only=True, before_comparison=before)
        case = holder['case']
        assert not list((tmp_path / 'run').glob('execution-results/*/rna-structure-comparison-actions/*/receipt.json'))
        assert all('saved' not in form for form in case.original_forms)
    finally:
        if holder:
            holder['case'].store.close()


def test_repeated_typed_admission_has_no_new_references_or_observations(pair_case):
    case = pair_case
    before = [dict(row) for row in case.store.db.execute('SELECT * FROM runtime_observations ORDER BY episode_id,unit_index')]
    index = int(case.comparison_context.path[-1][1].removeprefix('child_'))
    key = f'{F.RUN_ID}:{case.science_context.episode_id}:{index}:typed_form'
    for _ in range(2):
        assert case.owner.received_form_references(case.science_context, case.returned, F.comparison_form(), key) == []
    assert [dict(row) for row in case.store.db.execute('SELECT * FROM runtime_observations ORDER BY episode_id,unit_index')] == before
