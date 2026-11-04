"""Check independent retained-native answers and saved-data recalculation."""
from copy import deepcopy
from decimal import Decimal, localcontext, Inexact, Rounded, ROUND_DOWN
import json
import socket
import subprocess

import pytest

from gene_annotation_episode.bvbrc_proteome_directional_sheet import build_directional_sheet
from gene_annotation_episode.bvbrc_proteome_directional_calculators import calculate_directional_components
from gene_annotation_episode.bvbrc_proteome_directional_numerical_contracts import (
    canonical_sheet_sha256, validate_directional_numerical, DirectionalNumericalContractError,
)
from test_bvbrc_proteome_directional import native, parse


PARAMETERS = {'version': 'bvbrc_proteome_directional_parameters_v1',
    'formula_version': 'displayed_blastp_correspondence_v1',
    'amino_acid_alphabet': 'standard20', 'ratio_decimal_places': 18, 'rounding': 'half_even'}


def calculate(key='2221', *, data=None, parameters=None):
    parsed = parse(native(key) if data is None else data)
    built = build_directional_sheet([parsed])
    assert built['state'] in {'available', 'partial'} and built['sheet'] is not None
    result = calculate_directional_components(built['sheet'], parameters=deepcopy(PARAMETERS if parameters is None else parameters))
    assert result['state'] in {'available', 'partial'} and result['components'] is not None
    return built['sheet'], result


@pytest.fixture(scope='module')
def native_results():
    return {key: calculate(key) for key in ('2011', '2202', '2221')}


def subject(result, q=1, s=0):
    return result['components']['reports'][0]['queries'][q]['subjects'][s]


def fraction(cell, numerator, denominator):
    assert cell['state'] == 'value' and cell['unit'] == 'fraction'
    assert cell['value']['numerator'] == numerator
    assert cell['value']['denominator'] == denominator


def test_all_native_memberships_and_complete_observations(native_results):
    for key, counts in {'2011': (1, 0, 0, 0), '2202': (2, 23, 23, 25), '2221': (3, 30, 3, 4)}.items():
        observed, result = native_results[key]
        report = result['components']['reports'][0]
        assert tuple(report['displayed_' + kind + '_count']['value']
            for kind in ('query', 'description', 'subject', 'hsp')) == counts
        assert observed['reader_results'] == [parse(native(key))]
        assert result['components']['sheet_sha256'] == canonical_sheet_sha256(observed)
        assert validate_directional_numerical('DirectionalComponentsResult', result, sheet=observed) == result


def test_disjoint_native_alignment_retains_ambiguous_pairs(native_results):
    _, result = native_results['2221']
    value = subject(result)
    for axis in ('query', 'subject'):
        for basis in ('reported_interval', 'trace_occupied', 'trace_paired'):
            union = value['coverage'][axis + '_' + basis + '_union']
            assert union['intervals'] == [[0, 414], [485, 600]]
            assert union['count']['value'] == 529
            fraction(union['coverage'], 529, 600)
    assert value['correspondence']['mapping_state'] == 'compatible_displayed_partial_map'
    fraction(value['compatible_unique_pair_symbol_identity'], 468, 529)
    fraction(value['compatible_unique_pair_resolved_identity'], 468, 468)
    fraction(value['compatible_unique_pair_resolved_fraction'], 468, 529)
    assert value['compatible_pair_counts']['unresolved_pairs']['value'] == 61
    assert value['compatible_pair_counts']['resolved_substituted_pairs']['value'] == 0
    assert value['nonoverlapping_hsp_reported_identity_count']['value'] == 468
    assert value['nonoverlapping_hsp_reported_alignment_columns']['value'] == 529
    fraction(value['nonoverlapping_hsp_reported_identity_over_columns'], 468, 529)
    hsp0, hsp1 = value['hsps']
    assert hsp0['trace_counts']['unresolved_symbol_pairs']['value'] == 61
    assert hsp0['trace_counts']['subject_gap_columns']['value'] == 0
    assert hsp0['reported']['reported_gap_fraction']['state'] == 'missing'
    assert hsp0['reported']['reported_paired_column_count']['state'] == 'missing'
    assert hsp0['native_scores']['expect']['value'] == '0.0'
    assert hsp0['native_scores']['expectation_display'] == 'printed_zero_precision_unknown'
    assert hsp1['native_scores']['expect']['value'] == '2e-66'
    fraction(subject(result, 0)['coverage']['query_trace_paired_union']['coverage'], 303, 472)
    fraction(subject(result, 2)['compatible_unique_pair_symbol_identity'], 458, 473)
    fraction(subject(result, 2)['compatible_unique_pair_resolved_identity'], 458, 458)


def _positions(conflicts, code, side):
    return {position for conflict in conflicts if conflict['code'] == code
        for start, end in conflict[side + '_intervals'] for position in range(start, end)}


@pytest.mark.parametrize('query,occupied,paired,alternative_count', [
    (0, (219, 144), (187, 140), 47), (1, (333, 225), (327, 223), 104),
])
def test_overlapping_native_hsps_keep_independent_unions_and_conflicts(native_results, query, occupied, paired, alternative_count):
    _, result = native_results['2202']
    value = subject(result, query)
    for index, axis in enumerate(('query', 'subject')):
        assert value['coverage'][axis + '_trace_occupied_union']['count']['value'] == occupied[index]
        assert value['coverage'][axis + '_trace_paired_union']['count']['value'] == paired[index]
    graph = value['correspondence']
    assert graph['mapping_state'] == 'observed_conflict'
    assert len(_positions(graph['conflicts'], 'alternative_subject_mapping', 'subject')) == alternative_count
    assert value['compatible_unique_pair_symbol_identity']['state'] == 'conflict'
    assert value['nonoverlapping_hsp_reported_identity_over_columns']['state'] == 'conflict'
    assert value['hsps'][1]['reported']['reported_gap_fraction']['state'] == 'missing'
    assert value['hsps'][1]['trace_counts']['query_gap_columns']['value'] == 0
    if query == 1:
        assert 126 in _positions(graph['conflicts'], 'subject_gap_versus_pair_conflict', 'subject')
    else:
        first = value['hsps'][0]
        assert first['trace_counts']['paired_columns']['value'] == 140
        assert first['trace_counts']['resolved_amino_acid_substituted_pairs']['value'] == 84
        assert first['trace_counts']['unresolved_symbol_pairs']['value'] == 3
        fraction(first['reported']['reported_identity_among_paired_fraction'], 53, 140)


def test_native_no_hit_zero_is_not_a_fabricated_pair_identity(native_results):
    _, result = native_results['2011']
    query = result['components']['reports'][0]['queries'][0]
    assert query['display_state'] == 'native_no_hit_claim'
    assert query['subjects'] == [] and query['displayed_hsp_count']['value'] == 0
    fraction(query['any_displayed_subject_query_paired_union']['coverage'], 0, 102)
    assert 'statistic_occurrences_disagree' not in {i['code'] for i in result['diagnostics']}


def test_saved_sheet_recalculation_uses_no_native_reader_network_or_process(native_results, monkeypatch):
    observed, original = deepcopy(native_results['2221'])
    saved = json.loads(json.dumps(observed))
    def forbidden(*args, **kwargs):
        raise AssertionError('Saved-sheet recalculation attempted scientific I/O')
    monkeypatch.setattr('gene_annotation_episode.bvbrc_proteome_directional.parse_genome_comparison_directional_report', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    monkeypatch.setattr(subprocess, 'run', forbidden)
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    assert calculate_directional_components(saved, parameters=deepcopy(PARAMETERS)) == original
    changed = calculate_directional_components(saved, parameters={**PARAMETERS, 'ratio_decimal_places': 3})
    changed_cell = subject(changed)['compatible_unique_pair_symbol_identity']
    fraction(changed_cell, 468, 529)
    assert changed_cell['value']['decimal'] == '0.885'
    assert saved == observed
    assert original['components']['parameters']['ratio_decimal_places'] == 18


def test_report_occurrences_and_dictionary_order_are_not_identity_keys(native_results):
    observed, _ = deepcopy(native_results['2221'])
    parsed = observed['reader_results'][0]
    twice = build_directional_sheet([parsed, deepcopy(parsed)])['sheet']
    result = calculate_directional_components(twice, parameters=PARAMETERS)
    assert len(result['components']['reports']) == 2
    for ordinal, report in enumerate(result['components']['reports']):
        assert report['report_ordinal'] == ordinal
        assert report['displayed_hsp_count']['value'] == 4
    def reverse_keys(value):
        if isinstance(value, dict):
            return {k: reverse_keys(v) for k, v in reversed(list(value.items()))}
        if isinstance(value, list):
            return [reverse_keys(v) for v in value]
        return value
    assert calculate_directional_components(reverse_keys(twice), parameters=PARAMETERS) == result


@pytest.mark.parametrize('bad', [True, -1, 31, None, '18'])
def test_invalid_explicit_precision_returns_typed_failure(native_results, bad):
    observed, _ = native_results['2011']
    result = calculate_directional_components(observed, parameters={**PARAMETERS, 'ratio_decimal_places': bad})
    assert result['state'] == 'failure' and result['components'] is None
    assert result['diagnostics'][0]['code'] == 'invalid_parameters'
    assert result['diagnostics'][0]['argument_pointer'].startswith('/parameters')


def test_corrupt_observed_population_is_not_silently_repaired(native_results):
    observed, _ = deepcopy(native_results['2221'])
    observed['reports'][0]['query_rows'][1]['subjects'][0]['hsps'].pop()
    result = calculate_directional_components(observed, parameters=PARAMETERS)
    assert result['state'] == 'failure' and result['components'] is None
    assert result['diagnostics'][0]['code'] == 'invalid_input_contract'


def test_tiny_positive_and_printed_zero_expectations_stay_distinct():
    raw = native('2221').replace(b'2e-66', b'e-900')
    observed, result = calculate(data=raw)
    value = subject(result)
    assert Decimal(value['hsps'][1]['native_scores']['expect']['value']) > 0
    assert value['hsps'][1]['native_scores']['expectation_display'] == 'positive_reported_decimal'
    assert value['hsps'][0]['native_scores']['expectation_display'] == 'printed_zero_precision_unknown'
    assert value['minimum_reported_hsp_expectation']['tied_hsps'] == [value['hsps'][0]['key']]


def test_saved_component_tampering_is_rejected(native_results):
    observed, result = deepcopy(native_results['2221'])
    subject(result)['compatible_unique_pair_symbol_identity']['value']['numerator'] += 1
    with pytest.raises(DirectionalNumericalContractError):
        validate_directional_numerical('DirectionalComponents', result['components'], sheet=observed)


def test_caller_decimal_settings_cannot_change_saved_sheet_calculation(native_results):
    observed, expected = native_results['2221']
    with localcontext() as context:
        context.prec = 2
        context.Emin, context.Emax = -9, 9
        context.rounding = ROUND_DOWN
        context.traps[Inexact] = context.traps[Rounded] = True
        assert calculate_directional_components(observed, parameters=PARAMETERS) == expected


@pytest.mark.parametrize('identity,symbols,rendered', [(1,'AKLMNPQR','0.12'),(3,'ACDKLMNP','0.38')])
def test_exact_half_even_rounding_retains_the_native_rational(identity, symbols, rendered):
    data = (f'BLASTP 2.2.2\nQuery= q\n (8 letters)\n> s\n Length = 8\n'
            f' Score = 20 bits (40), Expect = e-30\n'
            f' Identities = {identity}/8 (0%), Gaps = 0/8 (0%)\n'
            f'Query: 1 ACDEFGHI 8\nSbjct: 1 {symbols} 8\nS2: 40 (20 bits)\n').encode()
    _, result = calculate(data=data, parameters={**PARAMETERS,'ratio_decimal_places':2})
    cell = subject(result,0)['compatible_unique_pair_symbol_identity']
    fraction(cell,identity,8)
    assert cell['value']['decimal'] == rendered
