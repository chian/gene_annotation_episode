"""Exact receiver projections retain units, native defects and typed missingness."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from gene_annotation_episode.atac_differential_result_contracts import atac_result_schema, validate_atac_result_record
from gene_annotation_episode.atac_differential_result_views import project_atac_result
from gene_annotation_episode.atac_differential_return_views import (
    atac_fact_sources, requested_atac_sources, select_atac_return_facts,
    PROJECTION_SOURCE, SAVED_SOURCE, FAILURE_SOURCE,
)
from gene_annotation_episode.atac_differential_execution_information import describe_atac_result, validate_atac_result_selector, atac_result_selector_schema
from gene_annotation_episode.atac_differential_result_worker import run_atac_result_worker
from test_atac_differential_result_worker import saved_plan, read_outputs, selector
from test_atac_differential_calculation_inputs import sheet, population


@pytest.fixture
def outputs(tmp_path):
    plan = saved_plan(tmp_path, sheet(native=True), intervals=population(end=12000))
    run_atac_result_worker(plan)
    return plan, read_outputs(plan)


@pytest.mark.parametrize('kind', ['summary', 'native_peak_rows', 'native_differential_rows', 'interval_components', 'derived_regions'])
def test_exact_requested_view_and_complete_total_after_explicit_window(outputs, kind):
    plan, output = outputs
    chosen = deepcopy(plan['selector'])
    view = chosen['projection']
    view.update(kind=kind, row_window=None if kind == 'summary' else dict(offset=1, limit=1),
        run_keys=['cp2', 'cp1'] if kind == 'native_peak_rows' else [],
        categories=['condition2', 'common', 'condition1'] if kind in ('native_differential_rows', 'derived_regions') else [])
    if kind == 'native_peak_rows':
        view['run_keys'] = [r['run_key'] for r in reversed(output['sheet']['callpeak_bindings'])]
    result = project_atac_result(output['sheet'], output['calculations'], selector=chosen,
        component_rows=iter(output['components']), region_rows=iter(output['regions']))
    assert result['row_extent'] == 'complete'
    assert result['summary'] is not None if kind == 'summary' else result['summary'] is None
    if kind == 'summary':
        assert result['rows'] == [] and result['total_rows'] == 0
    else:
        assert len(result['rows']) == min(1, max(0, result['total_rows'] - 1))
    if kind == 'native_peak_rows':
        assert result['total_rows'] == 6 and result['rows'][0]['row']['display_score'] == 1045
    if kind == 'native_differential_rows':
        assert result['total_rows'] == 2
        assert result['rows'][0]['coordinate_qualification'] == 'macs2_2_2_9_1_native_endpos_displacement_demonstrated'
        assert result['rows'][0]['row']['reported_start0'] == 907


def test_partial_component_total_is_unknown_and_prefix_retained(outputs):
    plan, output = outputs
    selected = deepcopy(plan['selector'])
    selected['projection'].update(kind='interval_components', row_window=dict(offset=0, limit=2))
    for table in output['calculations']['tables']:
        table['extent'] = 'partial'
    result = project_atac_result(output['sheet'], output['calculations'], selector=selected, component_rows=iter(output['components'][:3]))
    assert len(result['rows']) == 2 and result['total_rows'] is None and result['row_extent'] == 'partial'


def test_requested_fact_schema_cannot_be_weakened_or_add_prose(outputs):
    _, output = outputs
    registered = atac_fact_sources()
    schema = dict(type='object', properties={'answer': registered[PROJECTION_SOURCE]['report_schema']}, required=['answer'], additionalProperties=False)
    assert requested_atac_sources(schema) == (PROJECTION_SOURCE,)
    groups = {PROJECTION_SOURCE: [output['projection']], SAVED_SOURCE: [], FAILURE_SOURCE: []}
    assert select_atac_return_facts(groups, schema=schema) == {PROJECTION_SOURCE: [output['projection']]}
    bad = deepcopy(schema)
    bad['properties']['answer']['items'] = {'type': 'object'}
    with pytest.raises(ValueError, match='unregistered'):
        requested_atac_sources(bad)
    wrapped = deepcopy(schema)
    wrapped['properties']['answer'] = {'anyOf': [wrapped['properties']['answer'], {'type': 'object'}]}
    with pytest.raises(ValueError, match='unregistered'):
        requested_atac_sources(wrapped)
    bad = deepcopy(output['projection'])
    bad['findings'] = 'unrestricted prose'
    with pytest.raises(ValueError):
        validate_atac_result_record('RequestedProjection', bad)


@pytest.mark.parametrize('mutation', [
    lambda s: s['parameters'].update(pseudocount=True),
    lambda s: s['parameters'].update(cutoff_log10_lr=float('nan')),
    lambda s: s['parameters'].update(maximum_gap_bp=50),
    lambda s: s['projection'].update(run_keys=['arbitrary']),
    lambda s: s['projection'].update(row_window=dict(offset=0, limit=1)),
    lambda s: s['intervals'].append(dict(chromosome='chrToy', start=1, end=10)),
])
def test_selector_rejects_invalid_numeric_or_projection_meanings(outputs, mutation):
    plan, _ = outputs
    chosen = deepcopy(plan['selector'])
    mutation(chosen)
    with pytest.raises(ValueError):
        validate_atac_result_record('ResultSelector', chosen)


def test_bound_failure_schema_is_the_same_native_failure_declaration():
    from gene_annotation_episode.native_atac_differential_contracts import atac_execution_schema
    assert atac_result_schema('Failure') == atac_execution_schema('Failure')


def test_selector_schema_keeps_local_references_when_embedded_in_assignment_conditionals():
    from jsonschema import Draft202012Validator
    selected = selector(sheet())
    embedded = dict(type='object', properties={'operation': {'const': 'atac'}, 'selector': atac_result_selector_schema()},
        required=['operation', 'selector'], additionalProperties=False)
    outer = {
        'type': 'object', 'properties': {'assignment': embedded},
        'required': ['assignment'], 'additionalProperties': False,
        '$defs': {'ResultSelector': {'type': 'null'}},
        'allOf': [{
            'if': {'properties': {'assignment': {'properties': {'operation': {'const': 'atac'}}}}},
            'then': {'properties': {'assignment': {'properties': {'selector': atac_result_selector_schema()}}}},
        }],
    }
    value = dict(assignment=dict(operation='atac', selector=selected))
    validator = Draft202012Validator(outer)
    validator.validate(value)
    selected['parameters']['pseudocount'] = True
    assert not validator.is_valid(value)


def test_summary_keeps_real_zero_and_unknown_tail_as_separate_quantities(outputs):
    _, output = outputs
    summary = output['projection']['summary']
    assert summary['native_region_counts'][2]['count'] == 0
    assert summary['partition_coverage']['all_four_observed_bp'] == 8060
    assert summary['partition_coverage']['unavailable_or_invalid_bp'] == 3940
    assert summary['selected_population_bp'] == 12000
    assert summary['uncertainty'] == dict(kind='not_estimated', value=None)


def test_complete_row_projection_requires_its_whole_population_count(outputs):
    plan, output = outputs
    chosen = deepcopy(plan['selector'])
    chosen['projection'].update(kind='interval_components', row_window=dict(offset=0, limit=1))
    result = project_atac_result(output['sheet'], output['calculations'], selector=chosen, component_rows=iter(output['components']))
    result['total_rows'] = None
    with pytest.raises(ValueError, match='complete_population'):
        validate_atac_result_record('RequestedProjection', result)
