"""Closed selected fields, ordering, pages and wrong source joins."""
from copy import deepcopy

import pytest

from gene_annotation_episode.chromatin_interaction_calculations import calculate_chromatin_components
from gene_annotation_episode.chromatin_interaction_contracts import chromatin_record_digest
from gene_annotation_episode.chromatin_interaction_result_views import project_chromatin_result
from verification.tool_graders_chromatin_calculations_projection_2026-10-27_443.fixture_helpers import case, record


@pytest.mark.parametrize('name,selector_name', [('raw','raw'),('weighted','weighted'),('raw','raw_distances'),
    ('raw','raw_saved'),('insulation','insulation'),('insulation','domains'),('insulation','population'),('partial','partial')])
def test_every_worked_projection_has_exact_selected_fields_and_page(name, selector_name):
    sheet,tables,p = case(name)
    components = calculate_chromatin_components(sheet,tables=tables,parameters=p)
    selector = record(selector_name + '.selector')
    result = project_chromatin_result(sheet,components,selector=selector)
    expected = record(selector_name + '.projection')
    for field in ('kind','source_sheet_sha256','parameters','population_keys','requested_fields','page'):
        assert result[field] == expected[field]
    assert len(result['rows']) == len(expected['rows'])
    for row, oracle in zip(result['rows'],expected['rows']):
        assert list(row['fields']) == selector['projection']['fields']
        assert set(row) == set(oracle)
        for name in row.keys() - {'fields','qualifications'}:
            assert row[name] == oracle[name]
        for field,wanted in oracle['fields'].items():
            for part,value in wanted.items():
                if type(value) in (int,float):
                    assert row['fields'][field][part] == pytest.approx(value)
                else:
                    assert row['fields'][field][part] == value


def test_projection_page_cannot_change_distance_population_or_leak_other_fields():
    sheet,tables,p = case('raw')
    components = calculate_chromatin_components(sheet,tables=tables,parameters=p)
    before = chromatin_record_digest(components)
    selector = record('raw.selector')
    selector['projection']['fields'] = ['fold_enrichment']
    selector['projection']['selection']['page'] = {'offset':0,'limit':1}
    view = project_chromatin_result(sheet,components,selector=selector)
    assert view['rows'][0]['fields']['fold_enrichment']['value'] == 1.5
    assert list(view['rows'][0]['fields']) == ['fold_enrichment']
    assert view['page'] == {'offset':0,'returned_count':1,'total_row_count':2,'has_more':True}
    assert not view['failures']  # The unselected zero-denominator pair is private.
    assert chromatin_record_digest(components) == before
    selector['projection']['selection']['page']['offset'] = 1
    view = project_chromatin_result(sheet,components,selector=selector)
    assert view['rows'][0]['fields']['fold_enrichment']['reason'] == 'zero_denominator'
    assert any(f['field_path'] == '/rows/0/fields/fold_enrichment' for f in view['failures'])


@pytest.mark.parametrize('kind,key_field,key_values,row_field', [
    ('contact_pairs','pair_keys',['p0.E.Q','p0.E.P'],'pair_key'),
    ('distance_expectations','separations',[3,1],'separation_bins'),
    ('insulation_windows','boundary_bin_ids',[4,2],'boundary_bin_id'),
    ('domains','domain_keys',['p0.domain0'],'domain_key')])
def test_explicit_requested_key_order(kind,key_field,key_values,row_field):
    source = 'raw' if kind in ('contact_pairs','distance_expectations') else 'insulation'
    sheet,tables,p = case(source)
    components = calculate_chromatin_components(sheet,tables=tables,parameters=p)
    selector = record({'contact_pairs':'raw','distance_expectations':'raw_distances',
                       'insulation_windows':'insulation','domains':'domains'}[kind]+'.selector')
    selector['projection']['selection'] = {'by':'keys',key_field:key_values}
    view = project_chromatin_result(sheet,components,selector=selector)
    assert [r[row_field] for r in view['rows']] == key_values
    assert view['page'] is None


def test_unselected_mode_population_metrics_are_not_measured_not_zero():
    sheet,tables,p = case('insulation')
    components = calculate_chromatin_components(sheet,tables=tables,parameters=p)
    selector = record('population.selector')
    selector['projection']['fields'] = ['requested_pair_count','complete_window_count']
    view = project_chromatin_result(sheet,components,selector=selector)
    value = view['rows'][0]['fields']['requested_pair_count']
    assert value['value'] is None and value['state'] == 'not_measured'
    assert view['rows'][0]['fields']['complete_window_count']['value'] == 5


@pytest.mark.parametrize('mutation', ['sheet_digest','table_order','inner_parameters','selector_parameters',
                                     'pair_element','measure_population','population_order'])
def test_wrong_source_component_or_selector_join_rejects(mutation):
    sheet,tables,p = case('raw')
    c = calculate_chromatin_components(sheet,tables=tables,parameters=p)
    s = record('raw.selector')
    if mutation == 'sheet_digest':
        c['source_sheet_sha256'] = '0'*64
    elif mutation == 'table_order':
        c['table_identities'].reverse()
    elif mutation == 'inner_parameters':
        c['contact']['parameters']['fold_threshold'] = 10
    elif mutation == 'selector_parameters':
        s['parameters']['contact']['fold_threshold'] = 10
    elif mutation == 'pair_element':
        c['contact']['populations'][0]['pairs'][0]['enhancer_element_key'] = 'wrong'
    elif mutation == 'measure_population':
        c['contact']['populations'][0]['pairs'][0]['measurements']['raw_contact']['population_key'] = 'wrong'
    elif mutation == 'population_order':
        c['contact']['populations'] = []
    with pytest.raises(ValueError):
        project_chromatin_result(sheet,c,selector=s)


def test_saved_bundle_must_include_exact_table_order_and_sheet_identity():
    sheet,tables,p = case()
    c = calculate_chromatin_components(sheet,tables=tables,parameters=p)
    s = record('raw_saved.selector')
    s['saved_sheet_bundle']['tables'].reverse()
    with pytest.raises(ValueError,match='saved_table'):
        project_chromatin_result(sheet,c,selector=s)


def test_forged_domain_relationship_and_unknown_keys_reject():
    sheet,tables,p = case('insulation')
    c = calculate_chromatin_components(sheet,tables=tables,parameters=p)
    s = record('domains.selector')
    c['insulation']['populations'][0]['domains'][0]['right_boundary_bin_id'] = 5
    with pytest.raises(ValueError,match='domain_boundary'):
        project_chromatin_result(sheet,c,selector=s)
    sheet,tables,p = case()
    c = calculate_chromatin_components(sheet,tables=tables,parameters=p)
    s = record('raw.selector')
    s['projection']['selection'] = {'by':'keys','pair_keys':['p0.foreign']}
    with pytest.raises(ValueError,match='unknown_row'):
        project_chromatin_result(sheet,c,selector=s)
