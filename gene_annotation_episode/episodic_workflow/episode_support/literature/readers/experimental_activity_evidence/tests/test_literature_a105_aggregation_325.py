"""Exact user-selected A105 sum/max rules and parent numerical custody."""
from copy import deepcopy
from dataclasses import replace
import json
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.domain import ContractError, identity, validate_schema
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_aggregation import COMPONENTS, aggregate_a105, aggregation_sheet_schema
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_aggregation_storage import LiteratureA105AggregationRepository, aggregation_cells_schema, REQUESTED
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_assay_grading_storage import LiteratureAssayGradingRepository, _rows
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.test_literature_assay_grading import fixture
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.tests.test_literature_assay_experiment_instances_323 import two_experiments
MAPPING = dict(reliability='effect_precision', validity='recovery_deviation', relevance='assertion_prediction_error', attribution='attributed_fraction', overall='source_log_evidence_ratio')

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
        selected = _rows({'sheet': sheet, 'selection': {'source_ref': identity('source', 'synthetic_source325'), 'experiment_ref': experiment}}, source, list(MAPPING.values()))
        for row in selected:
            row['value'] = value
            row['input_origins'] = ['synthetic']
        args['experiments'].append({'experiment_ref': experiment, 'metrics': {metric: {'sheet_ref': source, 'component': component} for metric, component in MAPPING.items()}})
        rows.extend(selected)
    return (args, rows)

def test_exact_user_rules_sum_sum_max_max_sum():
    args, rows = pure_inputs()
    original = deepcopy((args, rows))
    sheet = aggregate_a105(args, rows)
    validate_schema(sheet, aggregation_sheet_schema())
    assert [sheet['cells'][name]['value'] for name in COMPONENTS] == [12, 12, 5, 5, 12]
    assert [sheet['cells'][name]['reducer'] for name in COMPONENTS] == ['sum', 'sum', 'max', 'max', 'sum']
    assert all((cell['status'] == 'complete' for cell in sheet['cells'].values()))
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
    assert all((cell['value'] is None and cell['available_value'] is None for cell in cells.values()))
    assert all((cell['status'] == 'unavailable' for cell in cells.values()))

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

@pytest.mark.parametrize('mutation,reason', [('duplicate_experiment', 'duplicate_experiment'), ('wrong_experiment', 'experiment_binding_mismatch'), ('wrong_assertion', 'assertion_binding_mismatch'), ('wrong_dimension', 'metric_dimension_mismatch'), ('missing_component', 'selected_components_not_received'), ('duplicate_component', 'duplicate_source_component')])
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
    parent = replace(context, episode_id='parent325', role='literature', path=(('literature', 'parent325'),), assignment={**dict(context.assignment), REQUESTED: list(COMPONENTS)}, received_record_refs=[*context.received_record_refs, *refs])
    selected = []
    for index, ref in enumerate(refs):
        rows = native.project_cells([ref], permitted_record_refs=refs, components=list(MAPPING.values()))
        native.receive_cells(parent, rows, 'trusted-child-return-' + str(index))
        selected.extend(rows)
    args = {'assertion_ref': first['assertion_ref'], 'comparison_ref': None, 'experiments': [{'experiment_ref': data['experiment_ref'], 'metrics': {metric: {'sheet_ref': ref, 'component': component} for metric, component in MAPPING.items()}} for data, ref in zip((first, second), refs)]}
    return (parent, args, native, selected)





