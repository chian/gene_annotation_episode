"""Exact user-selected A105 sum/max rules and parent numerical custody."""
from copy import deepcopy
from dataclasses import replace
import json

import pytest

from gene_annotation_episode.domain import ContractError, identity, validate_schema
from gene_annotation_episode.literature_a105_aggregation import (
    COMPONENTS, aggregate_a105, aggregation_sheet_schema,
)
from gene_annotation_episode.literature_a105_aggregation_storage import (
    LiteratureA105AggregationRepository, aggregation_cells_schema, REQUESTED,
)
from gene_annotation_episode.literature_assay_grading import grade_assay
from gene_annotation_episode.literature_assay_grading_storage import LiteratureAssayGradingRepository, _rows
from gene_annotation_episode.state import Store
from test_literature_assay_grading import fixture
from test_literature_assay_experiment_instances_323 import two_experiments

MAPPING = dict(reliability='effect_precision', validity='recovery_deviation',
    relevance='assertion_prediction_error', attribution='attributed_fraction', overall='source_log_evidence_ratio')


def pure_inputs(values=(1, 2, 5, 4)):
    assertion = identity('hypothesis', 'synthetic_assertion325')
    args = {'assertion_ref': assertion, 'comparison_ref': None, 'experiments': []}
    rows = []
    for index, value in enumerate(values):
        inputs = fixture('endpoint_conversion')
        inputs['assertion_ref'] = assertion
        sheet = grade_assay(inputs)
        source = identity('source', ['synthetic_grade325', index])
        experiment = identity('reference', ['synthetic_experiment325', index])
        selected = _rows({'sheet': sheet,
            'selection': {'source_ref': identity('source', 'synthetic_source325'), 'experiment_ref': experiment}},
            source, list(MAPPING.values()))
        for row in selected:
            # Explicit synthetic scalar inputs exercise aggregation, not a new
            # interpretation of native measurements or a scientific estimate.
            row['value'] = value
            row['input_origins'] = ['synthetic']
        args['experiments'].append({'experiment_ref': experiment,
            'metrics': {metric: {'sheet_ref': source, 'component': component} for metric, component in MAPPING.items()}})
        rows.extend(selected)
    return args, rows


def test_exact_user_rules_sum_sum_max_max_sum():
    args, rows = pure_inputs()
    original = deepcopy((args, rows))
    sheet = aggregate_a105(args, rows)
    validate_schema(sheet, aggregation_sheet_schema())
    assert [sheet['cells'][name]['value'] for name in COMPONENTS] == [12, 12, 5, 5, 12]
    assert [sheet['cells'][name]['reducer'] for name in COMPONENTS] == ['sum', 'sum', 'max', 'max', 'sum']
    assert all(cell['status'] == 'complete' for cell in sheet['cells'].values())
    assert (args, rows) == original
    assert sheet['annotation_credit'] is None


def test_negative_max_is_ordinary_max_without_zero_floor_or_absolute_value():
    args, rows = pure_inputs((-5, -2, -7))
    cells = aggregate_a105(args, rows)['cells']
    assert cells['relevance']['value'] == -2
    assert cells['attribution']['value'] == -2
    assert cells['overall']['value'] == -14


def test_missing_values_are_not_zero_and_partial_available_result_is_distinct():
    args, rows = pure_inputs((1, 2, 5))
    missing = args['experiments'][1]['experiment_ref']
    for row in rows:
        if row['experiment_ref'] == missing:
            row.update(value=None, status='unavailable', reasons=['reported_uncertainty_missing'])
    cells = aggregate_a105(args, rows)['cells']
    for metric in COMPONENTS:
        assert cells[metric]['value'] is None
        assert cells[metric]['available_value'] == (6 if metric in ('reliability', 'validity', 'overall') else 5)
        assert cells[metric]['status'] == 'partial'
        assert cells[metric]['missing_experiment_refs'] == [missing]
        assert len(cells[metric]['selected_components']) == 3


def test_null_selection_stays_missing_and_does_not_require_other_metric_inputs():
    args, rows = pure_inputs((1,))
    args['experiments'][0]['metrics']['validity'] = None
    rows = [row for row in rows if row['component'] != MAPPING['validity']]
    cells = aggregate_a105(args, rows)['cells']
    assert cells['validity']['value'] is None
    assert cells['validity']['available_value'] is None
    assert cells['validity']['missing_inputs'][0]['reason'] == 'metric_component_not_selected'
    assert cells['overall']['value'] == 1


def test_empty_roster_does_not_fabricate_zero_evidence():
    args, rows = pure_inputs(())
    cells = aggregate_a105(args, rows)['cells']
    assert all(cell['value'] is None and cell['available_value'] is None for cell in cells.values())
    assert all(cell['status'] == 'unavailable' for cell in cells.values())


def test_shared_measurements_and_mixed_native_units_are_preserved_without_extra_gates():
    args, rows = pure_inputs((1, 2))
    for row in rows:
        row['measurement_keys'] = ['same_shared_measurement']
        row['conditions'].append('physical_measurement_identity_unknown')
    rows[-1]['unit'] = 'explicit_other_native_unit'
    cells = aggregate_a105(args, rows)['cells']
    assert cells['overall']['value'] == 3
    assert cells['overall']['unit'] == 'mixed_native_units'
    assert cells['overall']['input_units'] == ['dimensionless', 'explicit_other_native_unit']
    assert cells['overall']['measurement_keys'] == ['same_shared_measurement']
    assert 'physical_measurement_identity_unknown' in cells['overall']['conditions']


@pytest.mark.parametrize('mutation,reason', [
    ('duplicate_experiment', 'duplicate_experiment'),
    ('wrong_experiment', 'experiment_binding_mismatch'),
    ('wrong_assertion', 'assertion_binding_mismatch'),
    ('wrong_dimension', 'metric_dimension_mismatch'),
    ('missing_component', 'selected_components_not_received'),
    ('duplicate_component', 'duplicate_source_component'),
])
def test_unrelated_or_duplicate_rows_are_not_silently_combined(mutation, reason):
    args, rows = pure_inputs((1, 2))
    if mutation == 'duplicate_experiment':
        args['experiments'].append(deepcopy(args['experiments'][0]))
    elif mutation == 'wrong_experiment':
        rows[0]['experiment_ref'] = rows[-1]['experiment_ref']
    elif mutation == 'wrong_assertion':
        rows[0]['assertion_ref'] = identity('hypothesis', 'unrelated_assertion325')
    elif mutation == 'wrong_dimension':
        rows[0]['dimension'] = 'validity'
    elif mutation == 'missing_component':
        rows.pop()
    else:
        rows.append(deepcopy(rows[0]))
    with pytest.raises(ContractError, match=reason):
        aggregate_a105(args, rows)


def parent_fixture(store):
    context, first, second = two_experiments(store)
    native = LiteratureAssayGradingRepository(store, context.run_id)
    outcomes = [native.populate(context, data, key) for data, key in ((first, 'A'), (second, 'B'))]
    refs = [outcome['result']['sheet_ref'] for outcome in outcomes]
    parent = replace(context, episode_id='parent325', role='literature',
        path=(('literature', 'parent325'),),
        assignment={**dict(context.assignment), REQUESTED: list(COMPONENTS)},
        received_record_refs=[*context.received_record_refs, *refs])
    selected = []
    for index, ref in enumerate(refs):
        rows = native.project_cells([ref], permitted_record_refs=refs, components=list(MAPPING.values()))
        native.receive_cells(parent, rows, 'trusted-child-return-' + str(index))
        selected.extend(rows)
    args = {'assertion_ref': first['assertion_ref'], 'comparison_ref': None,
        'experiments': [{'experiment_ref': data['experiment_ref'], 'metrics': {
            metric: {'sheet_ref': ref, 'component': component} for metric, component in MAPPING.items()}}
            for data, ref in zip((first, second), refs)]}
    return parent, args, native, selected


def test_parent_combines_actual_possessed_grades_and_cold_replay_keeps_exact_subset(tmp_path, monkeypatch):
    with Store(tmp_path) as store:
        store.create_problem(raw_sequence='ATGGCT', molecule='dna')
        context, args, native, original_rows = parent_fixture(store)
        repo = LiteratureA105AggregationRepository(store, context.run_id,
            read_cells=lambda ctx, ref, components: native.fact_cells(ctx, [ref], components=components))
        outcome = repo.populate(context, args, 'combine')
        ref = outcome['result']['sheet_ref']
        native_outcome = json.loads(store.db.execute(
            f'SELECT outcome FROM {repo.operations_table} WHERE operation_key=?',
            ('combine',)).fetchone()['outcome'])
        assert native_outcome['record_refs'] == [ref]
        assert set(outcome['record_refs']) > {ref}
        rows = outcome['result']['cells']
        validate_schema(rows, aggregation_cells_schema())
        by_metric = {row['component']: row for row in rows}
        assert by_metric['reliability']['value'] == pytest.approx(25 + 1/.09)
        assert by_metric['validity']['value'] == pytest.approx(-.2)
        assert by_metric['relevance']['value'] == pytest.approx(-.2)
        assert by_metric['attribution']['value'] == pytest.approx(.75)
        assert by_metric['overall']['value'] == pytest.approx(7.5 - .3/.09)
        assert {row['sheet_ref'] for row in by_metric['overall']['selected_components']} == {
            row['sheet_ref'] for row in original_rows}
        outer = replace(context, episode_id='annotation325', role='annotation',
            path=(('annotation', 'annotation325'),), assignment={},
            received_record_refs=repo.cell_record_refs([by_metric['overall']]))
        repo.receive_cells(outer, [by_metric['overall']], 'trusted-aggregate-return')
        changes = store.db.total_changes
        assert repo.populate(context, args, 'combine') == outcome
        assert store.db.total_changes == changes
    def forbidden(*args, **kwargs):
        raise AssertionError('restoration must not calculate an aggregate or reread scientific inputs')
    monkeypatch.setattr('gene_annotation_episode.literature_a105_aggregation_storage.aggregate_a105', forbidden)
    monkeypatch.setattr('gene_annotation_episode.literature_assay_grading_storage.grade_assay', forbidden)
    monkeypatch.setattr('gene_annotation_episode.literature_assay_grading_storage.read_assay_grading_inputs', forbidden)
    with Store(tmp_path) as cold:
        cold.db.execute('PRAGMA query_only=ON')
        changes = cold.db.total_changes
        monkeypatch.setattr(cold, 'transaction', forbidden)
        for name in ('_register', '_refresh_dependents', '_refresh_main'):
            monkeypatch.setattr('gene_annotation_episode.literature_sheet_updates.' + name, forbidden)
        repo = LiteratureA105AggregationRepository(cold, context.run_id)
        assert repo.fact_cells(outer, [ref], components=list(COMPONENTS)) == [by_metric['overall']]
        assert repo.populate(context, args, 'combine') == outcome
        assert cold.db.total_changes == changes
        altered = deepcopy(by_metric['overall']); altered['value'] = 99
        with pytest.raises(ContractError, match='differs_from_saved'):
            repo.validate_fact_values(outer, [altered])
        changed = deepcopy(args)
        changed['experiments'][0]['metrics']['validity'] = None
        with pytest.raises(ContractError, match='operation_key_reused_for_different_work'):
            repo.populate(context, changed, 'combine')
        restricted = replace(context, received_record_refs=tuple(
            ref for ref in context.received_record_refs if ref != args['assertion_ref']))
        with pytest.raises(ContractError, match='record_not_received'):
            repo.populate(restricted, args, 'combine')


def test_publication_replay_keeps_original_return_after_later_publication(tmp_path, monkeypatch):
    from gene_annotation_episode.literature_sheet_updates import current_sheet_refs, current_scoring_sheets
    with Store(tmp_path) as store:
        store.create_problem(raw_sequence='ATGGCT', molecule='dna')
        context, args, native, _ = parent_fixture(store)
        repo = LiteratureA105AggregationRepository(store, context.run_id,
            read_cells=lambda ctx, ref, components: native.fact_cells(ctx, [ref], components=components))
        original = repo.populate(context, args, 'combine')
        changed = deepcopy(args)
        changed['experiments'][0]['metrics']['validity'] = None
        later = repo.populate(context, changed, 'combine-later')
        heads = current_sheet_refs(store, context)
        assert set(heads) - set(original['record_refs'])
        assert later != original
        assert all('returned_record_refs' not in row['dependency_receipt']
            for row in current_scoring_sheets(store, context))
        before = list(store.db.iterdump())
        def forbidden(*args, **kwargs):
            raise AssertionError('saved publication must not publish or refresh')
        monkeypatch.setattr(store, 'transaction', forbidden)
        assert repo.populate(context, args, 'combine') == original
        assert current_sheet_refs(store, context) == heads
        assert list(store.db.iterdump()) == before


@pytest.mark.parametrize('registered', [True, False])
def test_old_publication_missing_return_is_not_reconstructed_or_written(tmp_path, monkeypatch, registered):
    from gene_annotation_episode.literature_sheet_updates import TABLE
    with Store(tmp_path) as store:
        store.create_problem(raw_sequence='ATGGCT', molecule='dna')
        context, args, native, _ = parent_fixture(store)
        repo = LiteratureA105AggregationRepository(store, context.run_id,
            read_cells=lambda ctx, ref, components: native.fact_cells(ctx, [ref], components=components))
        outcome = repo.populate(context, args, 'combine')
        key = (context.run_id, context.episode_id, outcome['result']['sheet_ref'])
        where = 'WHERE run_id=? AND episode_id=? AND sheet_ref=?'
        if registered:
            receipt = json.loads(store.db.execute(f'SELECT receipt FROM {TABLE} ' + where, key).fetchone()[0])
            del receipt['returned_record_refs']
            store.db.execute(f'UPDATE {TABLE} SET receipt=? ' + where, (json.dumps(receipt), *key))
        else:
            store.db.execute(f'DELETE FROM {TABLE} ' + where, key)
        native_outcome = json.loads(store.db.execute(
            f'SELECT outcome FROM {repo.operations_table} WHERE operation_key=?',
            ('combine',)).fetchone()['outcome'])
        store.db.execute('PRAGMA query_only=ON')
        before = list(store.db.iterdump())
        def forbidden(*args, **kwargs):
            raise AssertionError('old saved publication must not open a transaction')
        monkeypatch.setattr(store, 'transaction', forbidden)
        if registered:
            with pytest.raises(ContractError, match='literature_publication_return_not_retained'):
                repo.populate(context, args, 'combine')
        else:
            assert repo.populate(context, args, 'combine') == native_outcome
        assert list(store.db.iterdump()) == before


def test_new_publication_still_rolls_back_native_sheet_if_update_fails(tmp_path, monkeypatch):
    with Store(tmp_path) as store:
        store.create_problem(raw_sequence='ATGGCT', molecule='dna')
        context, args, native, _ = parent_fixture(store)
        repo = LiteratureA105AggregationRepository(store, context.run_id,
            read_cells=lambda ctx, ref, components: native.fact_cells(ctx, [ref], components=components))
        before = list(store.db.iterdump())
        def failed_update(*args, **kwargs):
            raise RuntimeError('publication update failed')
        monkeypatch.setattr('gene_annotation_episode.literature_sheet_updates._refresh_main', failed_update)
        with pytest.raises(RuntimeError, match='publication update failed'):
            repo.populate(context, args, 'combine')
        assert list(store.db.iterdump()) == before


def test_source_identifier_alone_does_not_authorize_parent_to_aggregate_private_cells(tmp_path):
    with Store(tmp_path) as store:
        store.create_problem(raw_sequence='ATGGCT', molecule='dna')
        context, args, native, _ = parent_fixture(store)
        outsider = replace(context, episode_id='outsider325', path=(('literature', 'outsider325'),))
        repo = LiteratureA105AggregationRepository(store, context.run_id,
            read_cells=lambda ctx, ref, components: native.fact_cells(ctx, [ref], components=components))
        with pytest.raises(ContractError, match='component_not_received'):
            repo.populate(outsider, args, 'not-authorized-by-reference-possession')
