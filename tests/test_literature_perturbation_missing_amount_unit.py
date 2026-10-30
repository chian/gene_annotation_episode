"""Absent amount units preserve useful endpoints without concealing measurements."""
import asyncio
from copy import deepcopy
from dataclasses import replace
from unittest.mock import patch

import pytest

from gene_annotation_episode.communication import form_with_facts
from gene_annotation_episode.domain import canonical, obj
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.literature_perturbation_inputs import read_perturbation_inputs
from gene_annotation_episode.literature_perturbation_summary import populate_summary_restoration
from gene_annotation_episode.literature_perturbation_summary_storage import (
    LiteraturePerturbationSummaryProjection, perturbation_summary_cells_schema,
)
from test_literature_perturbation_summary import source_data, extract, calculate, figure_fixture, IMAGE, DATA, SOURCE, TEXT, arguments
from test_literature_perturbation_summary_integration import fixture, source, binding_for


def missing_amount_data():
    data = source_data()
    data['exposure_unit'] = 'unreported'
    return data


def test_absent_amount_unit_preserves_every_nonamount_numerical_cell():
    old = calculate(source_data())['cells']
    data = missing_amount_data()
    extraction, _ = extract(data)
    new = populate_summary_restoration(extraction, origin='synthetic')['cells']
    assert extraction['exposure_unit'] == 'unreported'
    assert extraction['values']['A_reference'] is None and extraction['values']['A_restored'] is None
    for name in old:
        if not name.startswith(('A_reference_', 'A_restored_')):
            assert new[name] == old[name]
    for name in ('A_reference_summary_value', 'A_restored_summary_value'):
        assert new[name]['value'] is None and new[name]['unit'] == 'unreported'
    assert new['perturbation_difference']['value'] == 9
    assert new['W_mean_variance']['value'] == 1
    assert new['amount_comparability']['value'] is None
    assert new['reference_restoration_index']['value'] is None


@pytest.mark.parametrize('role', ['A_reference', 'A_restored'])
@pytest.mark.parametrize('case', ['zero', 'positive', 'raw_units', 'graph', 'digitization',
    'sd_zero', 'sem', 'confidence_interval', 'lower_only_interval', 'detection_limit', 'untyped_pm'])
def test_unreported_unit_cannot_conceal_an_actual_amount_or_numerical_uncertainty(role, case):
    data = missing_amount_data(); entry = data['measurements'][role]; images = None
    entry['measurement_id'] = role
    if case in ('zero', 'positive'):
        entry['value'] = 0 if case == 'zero' else 7
    elif case == 'raw_units':
        entry['raw_units'] = [{'unit_id': 'unit1', 'values': [1, 2]}]
    elif case == 'graph':
        body, selected = figure_fixture()
        selected['calibration']['unit'] = 'molecules_per_cell'
        entry['graph'] = {'source_ref': IMAGE, 'selection': selected}; images = {IMAGE: body}
    elif case == 'digitization':
        entry['digitization'] = {'lower': 0, 'upper': 1, 'kind': 'conditional_digitization_not_confidence_interval'}
    elif case in ('sd_zero', 'sem', 'untyped_pm'):
        entry['uncertainty'].update(kind='sd' if case == 'sd_zero' else case,
            value=0 if case == 'sd_zero' else .5)
    else:
        entry['uncertainty'].update(kind='detection_limit' if case == 'detection_limit' else 'confidence_interval',
            lower=1 if case != 'detection_limit' else None,
            upper=None if case == 'lower_only_interval' else 2,
            coverage=None if case == 'detection_limit' else .95)
    def forbidden(*a, **kw):
        raise AssertionError('unitless amount must be rejected before image decoding')
    with patch('gene_annotation_episode.literature_perturbation_summary.read_summary_figure', forbidden):
        with pytest.raises(ExperimentalContractError, match='observed_amount_unit_required'):
            extract(data, images)


@pytest.mark.parametrize('scale', ['endpoint', 'log10_endpoint', 'ln_endpoint', 'unknown'])
@pytest.mark.parametrize('kind', ['sd', 'sem'])
def test_transformed_or_unknown_spread_scale_does_not_hide_numeric_amount_statistic(scale, kind):
    data = missing_amount_data()
    data['measurements']['A_restored']['uncertainty'].update(kind=kind, value=.2, scale=scale)
    with pytest.raises(ExperimentalContractError, match='observed_amount_unit_required'):
        extract(data)


def test_dimensionless_count_coverage_and_nonnumerical_meanings_do_not_invent_physical_unit():
    data = missing_amount_data(); entry = data['measurements']['A_reference']
    entry['count'].update(n=3, unit_kind='other', independence='unknown')
    entry['uncertainty'].update(kind='confidence_interval', coverage=.95)
    out = calculate(data)['cells']
    assert out['A_reference_reported_count']['value'] == 3
    assert out['A_reference_reported_count']['unit'] == 'count'
    assert out['A_reference_summary_value']['value'] is None
    assert out['A_reference_summary_value']['unit'] == 'unreported'
    assert out['A_reference_mean_variance']['value'] is None


@pytest.mark.parametrize('unit', ['molecules_per_cell', 'normalized_signal', 'fraction', 'mg_per_mL'])
def test_existing_physical_amount_unit_paths_remain_usable(unit):
    data = source_data(); data['exposure_unit'] = unit
    for role, value in [('A_reference', 1), ('A_restored', .5)]:
        data['measurements'][role].update(value=value, measurement_id=role)
    extraction, _ = extract(data)
    extraction['amount_role'] = 'nuisance'
    out = populate_summary_restoration(extraction, origin='synthetic')['cells']
    assert out['amount_comparability']['value'] == .5
    assert out['A_reference_summary_value']['unit'] == unit


def test_v1_reader_contract_still_rejects_unreported_amount_unit():
    data = missing_amount_data()
    data = {k: data[k] for k in ('version', 'endpoint_unit', 'exposure_unit', 'origin', 'uncertainty_basis', 'measurements')}
    data.update(version='a106_source_measurements_v1', uncertainty_basis='unreported')
    data['measurements'] = {r: {k: e[k] for k in ('value', 'measurement_id')} for r, e in data['measurements'].items()}
    bodies = {SOURCE: TEXT, DATA: canonical(data).encode()}
    with pytest.raises(ExperimentalContractError, match='unsupported_exposure_unit'):
        read_perturbation_inputs(arguments(), read_source=lambda ref, rep: {'artifact_ref': 'artifact_' + ref.split('_')[1], 'content': bodies[ref]})


def test_selected_typed_unknown_unit_and_exact_saved_replay_without_sources(tmp_path):
    store, context, args = fixture(tmp_path)
    try:
        retained = source(store, canonical(missing_amount_data()), parents=[args['source_ref']])
        args['data_source_ref'] = retained['id']
        names = ['W_summary_value', 'W_mean_variance', 'perturbation_difference',
            'A_reference_summary_value', 'A_restored_summary_value', 'amount_comparability', 'reference_restoration_index']
        context = replace(context, assignment={**context.assignment,
            'source_refs': [*context.assignment['source_refs'], retained['id']],
            'requested_perturbation_summary_components': names},
            received_record_refs=(*context.received_record_refs, retained['id']))
        binding = binding_for(store, context)
        result = asyncio.run(binding.execute(context, 'literature.perturbation.populate', args, 'unit-selected'))
        assert result['status'] == 'completed', result.get('feedback')
        assert result['result']['exposure_unit'] == 'unreported'
        sheet = result['result']['sheet_ref']
        context = replace(context, received_record_refs=(*context.received_record_refs, *result['record_refs']))
        schema = obj({'measurements': perturbation_summary_cells_schema()})
        form = form_with_facts({}, schema, binding.facts(context, {'committed_record_refs': [sheet]}))
        binding.validate_report(context, form, schema)
        rows = form['measurements']
        assert all(row['exposure_unit'] == 'unreported' for row in rows)
        assert rows[0]['value'] == 12 and rows[1]['value'] == 1 and rows[2]['value'] == 9
        assert all(row['value'] is None for row in rows[3:])
        parent = replace(context, role='annotation', episode_id='unit-parent', assignment={}, path=(('annotation', 'root'),))
        binding.received_form_references(parent, form, schema, 'unit-receipt')
        projection = LiteraturePerturbationSummaryProjection(store, context.run_id)
        saved = store.get(sheet); allowed = {saved['artifact_ref'], saved['request_ref']}
        get = store.get_artifact
        def saved_only(ref):
            assert ref in allowed, 'replay must not reacquire source/recipe bytes'
            return get(ref)
        def forbidden(*a, **kw):
            raise AssertionError('no reader, calculator or mutation in saved replay')
        store.db.execute('pragma query_only=ON'); before = store.db.total_changes
        with patch.object(store, 'get_artifact', saved_only), patch.object(store, 'put', forbidden), \
            patch.object(store, 'artifact', forbidden), patch.object(store, 'transaction', forbidden), \
            patch('gene_annotation_episode.literature_perturbation_storage.read_perturbation_inputs', forbidden), \
            patch('gene_annotation_episode.literature_perturbation_storage.populate_source_summary_restoration', forbidden):
            assert projection.received_cells(parent) == rows
            assert projection.project_cells([sheet], permitted_record_refs=context.received_record_refs, components=names) == rows
            assert store.db.total_changes == before
    finally:
        store.close()
