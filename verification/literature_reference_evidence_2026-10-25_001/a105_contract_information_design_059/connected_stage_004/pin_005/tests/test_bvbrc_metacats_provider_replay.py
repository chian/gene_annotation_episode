"""Retained-native numerical replay and detached sheet/component validation."""
from copy import deepcopy
import json
import math
from pathlib import Path

import pytest

from test_bvbrc_metacats_provider import (
    CASES, OLD, retained_sheet, requests, simple_sheet, by_id, native_family_request, forbid_io,
)
from gene_annotation_episode import bvbrc_metacats_provider_contracts as c
from gene_annotation_episode.bvbrc_metacats_grader import calculate_metacats


@pytest.mark.parametrize('case', CASES)
def test_seven_retained_native_cases_keep_full_native_and_derived_values(case):
    sheet, parameters, receipt = retained_sheet(case)
    before = deepcopy(sheet)
    if case == 'official_na':
        parameters['requests'].append(native_family_request(sheet, eligibility=['native:GROUP:statistics']))
    result = calculate_metacats(sheet, parameters)
    category = sheet['analysis']['category_ids'][0]
    native = by_id(result, 'native:' + category + ':statistics')['value']
    old = json.loads((OLD / ('EXAMPLES_002' if case == 'twelve_groups' else 'EXAMPLES_001') / (case + '-answer.json')).read_text())
    assert native is not None
    for collection in ('omnibus', 'pairs'):
        assert len(native[collection]) == len(old['statistics'][collection])
        for actual, retained in zip(native[collection], old['statistics'][collection]):
            assert actual['column_0based'] == retained['column_0based']
            for field in ('epsilon', 'augmented_total', 'continuity_delta', 'chi_square', 'df', 'mathematical_p', 'log_p', 'native_zero_rule_p'):
                assert actual[field]['value'] == retained[field]['value']
    if case == 'official_na':
        exported = next(d['value'] for d in sheet['documents'] if d['kind'] == 'metacats_chisq')
        assert len(native['omnibus']) == 312 and len(exported['rows']) == 143
        assert by_id(result, 'native-observed-family')['value']['total_test_count'] == 312
        assert all(row['p_value']['value'] < .05 for row in exported['rows'])
    biological_reference = json.loads((OLD.parent / 'tool_graders_bvbrc_metacats_biological_2026-10-25/EXAMPLES_001' / (case + '-answer.json')).read_text())
    biological = by_id(result, 'biological:' + category + ':statistics')['value']
    for collection in ('omnibus', 'pairs'):
        assert len(biological[collection]) == len(biological_reference['statistics'][collection])
        for actual, retained in zip(biological[collection], biological_reference['statistics'][collection]):
            for field in ('epsilon', 'augmented_total', 'continuity_delta', 'chi_square', 'df', 'mathematical_p', 'log_p'):
                assert actual[field]['value'] == retained[field]['value']
    if case == 'metadata_only_first_group':
        biological = by_id(result, 'biological:' + category + ':counts')['value']
        assert biological['sites'][1]['observed_counts'] == [[6, 0, 0], [0, 6, 0]]
        assert [g['raw_group_value'] for g in biological['group_population']['groups']] == ['B', 'C', 'A']
        observations = [o for o in sheet['native_observations'] if o['field'] == 'metacats_symbol_count' and o['document_id'] in sheet['analysis']['chisq_table_ids']]
        assert [o['association_state'] for o in observations] == ['wrong_native_label', 'wrong_native_label']
    if case == 'twelve_groups':
        assert [r['r_group_token'] for r in sheet['native_group_columns']] == [f'{i:2d}' for i in range(1, 13)]
        pairs = [r for r in sheet['native_test_associations'] if r['test_kind'] == 'pairwise']
        assert any(r['state'] == 'resolved' for r in pairs)
    assert sheet == before


@pytest.mark.parametrize('case', ('aa_two_groups', 'aa_three_groups', 'native_pair_tail_underflow', 'all_missing'))
def test_saved_recalculation_needs_no_bytes_readers_or_native_execution(case, monkeypatch):
    sheet, parameters, _ = retained_sheet(case); answer = calculate_metacats(sheet, parameters)
    saved = json.dumps({'sheet': sheet, 'parameters': parameters, 'answer': answer}, allow_nan=False)
    restored = json.loads(saved)
    forbid_io(monkeypatch)
    def forbidden(*args, **kwargs):
        raise AssertionError('native parser called during saved replay')
    import gene_annotation_episode.bvbrc_metacats_formats as formats
    import gene_annotation_episode.bvbrc_metacats_input_formats as inputs
    for name in formats.__all__:
        monkeypatch.setattr(formats, name, forbidden)
    monkeypatch.setattr(inputs, 'parse_metacats_input_fasta', forbidden)
    assert calculate_metacats(restored['sheet'], restored['parameters']) == restored['answer']
    changed = deepcopy(restored['parameters'])
    for request in changed['requests']:
        if request['kind'] in c.STAT_KINDS:
            request['epsilon'] = .01
    new = calculate_metacats(restored['sheet'], changed)
    assert restored['sheet'] == sheet
    assert new['parameters'] != answer['parameters']
    for old, current in zip(answer['results'], new['results']):
        if old['kind'] in c.COUNT_KINDS | c.EFFECT_KINDS:
            assert old == current


def test_detached_validators_with_all_calculators_disabled(monkeypatch):
    sheet, parameters, _ = retained_sheet('aa_two_groups')
    parameters['requests'].append(native_family_request(sheet, kind='pairwise', eligibility=['native:comparison:statistics']))
    components = calculate_metacats(sheet, parameters)
    saved = json.loads(json.dumps({'sheet': sheet, 'components': components}))
    forbid_io(monkeypatch)
    def forbidden(*args, **kwargs):
        raise AssertionError('calculation or parsing during saved validation')
    import gene_annotation_episode.bvbrc_metacats_calculators as native
    import gene_annotation_episode.bvbrc_metacats_biological_calculators as biological
    import gene_annotation_episode.bvbrc_metacats_adequacy as adequacy
    import gene_annotation_episode.phylogeny_calculators as shared
    import gene_annotation_episode.bvbrc_metacats_grader as grader
    import gene_annotation_episode.bvbrc_metacats_formats as formats
    for module, names in ((native, ('metacats_group_counts', 'metacats_statistics', 'metacats_effects', 'adjust_p_values', 'chi_square_tail')),
                          (biological, biological.__all__), (shared, shared.__all__), (formats, formats.__all__),
                          (adequacy, ('expected_count_adequacy',)), (grader, ('calculate_metacats',))):
        for name in names:
            monkeypatch.setattr(module, name, forbidden)
    assert c.validate_metacats_sheet(saved['sheet']) == sheet
    assert c.validate_metacats_components(saved['components'], sheet=saved['sheet']) == components
    detached = c.validate_metacats_components(saved['components'], sheet=saved['sheet'])
    detached['results'].clear()
    assert saved['components']['results']


@pytest.mark.parametrize('mutation', ['source_number', 'native_id', 'native_group', 'native_population', 'missing_observation', 'extra_sheet_field'])
def test_saved_sheet_native_source_relationship_forgeries_rejected(mutation):
    sheet, _, _ = retained_sheet('aa_two_groups'); bad = deepcopy(sheet)
    if mutation == 'source_number': bad['native_observations'][0]['number']['value'] += 1
    if mutation == 'native_id': bad['native_observations'][0]['observation_id'] = 'fake'
    if mutation == 'native_group': bad['native_observations'][0]['group_ids'].reverse()
    if mutation == 'native_population': bad['native_observations'][0]['population_id'] = 'calculated-test'
    if mutation == 'missing_observation': bad['native_observations'].pop()
    if mutation == 'extra_sheet_field': bad['invented'] = True
    with pytest.raises(ValueError, match='bvbrc_metacats_provider_'):
        c.validate_metacats_sheet(bad)


@pytest.mark.parametrize('mutation', ['request_kind', 'population', 'raw_identity', 'test_identity', 'parameters', 'subset', 'family_basis', 'p_value', 'dependency'])
def test_saved_component_request_population_and_identity_forgeries_rejected(mutation):
    sheet = simple_sheet(); parameters = requests(sheet, native=False); components = calculate_metacats(sheet, parameters)
    bad = deepcopy(components)
    if mutation == 'request_kind': bad['results'][0]['kind'] = 'native_group_counts'
    if mutation == 'population': bad['results'][0]['value']['population_id'] = 'foreign'
    if mutation == 'raw_identity': bad['results'][0]['value']['sites'][1]['table_id'] = 'biological_group_counts:fake'
    if mutation == 'test_identity': bad['results'][1]['value']['omnibus'][0]['test_id'] = 'biological_group_test:fake'
    if mutation == 'parameters': bad['parameters']['requests'][1]['epsilon'] = .1
    if mutation == 'subset': bad['results'][1]['value']['omnibus'] = []
    if mutation == 'family_basis': bad['results'][-1]['value']['family']['p_value_basis'] = 'native_unadjusted'
    if mutation == 'p_value': bad['results'][-1]['value']['results'][0]['input_p']['value'] = .123
    if mutation == 'dependency': bad['parameters']['requests'][1]['counts_request_id'] = bad['parameters']['requests'][2]['request_id']
    with pytest.raises(ValueError, match='bvbrc_metacats_provider_'):
        c.validate_metacats_components(bad, sheet=sheet)


def test_native_underflow_one_remains_an_observation_not_mathematical_p():
    sheet, parameters, _ = retained_sheet('native_pair_tail_underflow')
    family_request = native_family_request(sheet, kind='pairwise', eligibility=['native:comparison:statistics'])
    parameters['requests'].append(family_request)
    result = calculate_metacats(sheet, parameters)
    statistical = by_id(result, 'native:comparison:statistics')['value']['pairs'][0]
    biological = by_id(result, 'biological:comparison:statistics')['value']['pairs'][0]
    observed = by_id(result, 'native-observed-family')['value']['results'][0]
    assert statistical['mathematical_p']['value'] is None and statistical['native_zero_rule_p']['value'] == 1
    assert biological['mathematical_p']['value'] is None and biological['log_p']['value'] == -2004.3710655188884
    assert observed['input_p']['value'] == 1 and observed['input_p']['origin'] == 'native_observation'
    assert observed['test_id'] != statistical['test_id']
