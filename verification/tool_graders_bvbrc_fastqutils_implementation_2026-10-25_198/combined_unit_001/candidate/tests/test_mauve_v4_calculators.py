"""Native numeric example and labelled synthetic correspondence/coverage cases."""
from copy import deepcopy
import builtins
import json
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode.mauve_v4_formats import parse_mauve_v4
from gene_annotation_episode.mauve_v4_calculators import calculate_mauve_v4_segments
from gene_annotation_episode.mauve_v4_calculation_contracts import (
    validate_mauve_v4_components, validate_mauve_v4_selection)
from gene_annotation_episode.bvbrc_genome_alignment_input_contracts import validate_genome_alignment_inputs
from test_mauve_v4_formats import OFFICIAL, parse, native
from test_bvbrc_genome_alignment_input_contracts import input_fixture


def member(index):
    return {'namespace': 'mauve_v4_member_0based', 'index': index}


def selection(document, *, denominator='none', pairs=True):
    return {'schema_version': 'mauve_v4_selection_v1', 'document_id': document['document_id'],
        'population_id': 'synthetic:selected-explicit-segments', 'members': [member(0), member(1)],
        'pairs': [{'member_a': member(0), 'member_b': member(1)}] if pairs else [],
        'segments': [{'interval_index': interval['interval_index'], 'segment_index': segment['segment_index'],
            'column_ranges_0based_half_open': [[0, (segment['native_width'] if segment['kind'] == 'gapped_rows' else segment['native_length'])['value']]]}
            for interval in document['intervals'] for segment in interval['segments']],
        'case_policy': 'uppercase', 'denominator': denominator,
        'population_scope': 'all_observed_document_segments', 'evidence': []}


def calculate(raw, *, denominator='none', inputs=None, pairs=True):
    document = parse(raw)['value']; sel = selection(document, denominator=denominator, pairs=pairs)
    return calculate_mauve_v4_segments(document, selection=sel, inputs=inputs)


def bound_inputs():
    inputs, raw = input_fixture()
    for i, row in enumerate(inputs['member_bindings']): row['member'] = member(i)
    inputs['original_task']['submitted_parameters']['recipe'] = 'mauveAligner'
    inputs['invocation'].update(requested_recipe='mauveAligner', effective_recipe='mauveAligner',
                               observed_argv=['mauveAligner', '/staged/f0', '/staged/f1'])
    return validate_genome_alignment_inputs(inputs)


def test_official_example_has_no_invented_anchor_identity_or_interanchor_columns():
    d = parse(OFFICIAL.read_bytes())['value']; sel = selection(d, denominator='native_declared_length')
    result = calculate_mauve_v4_segments(d, selection=sel, inputs=None)
    assert [(r['known_union_bases']['value'], r['denominator_bases']['value']) for r in result['coverage']] == [(690, 693), (2000, 2000)]
    assert result['coverage'][0]['complement_intervals'] == [[578, 581]]
    assert result['coverage'][0]['coverage_fraction']['value'] == 690 / 693
    for index in (0, 1, 3):
        assert result['pair_segments'][index]['state'] == 'missing_symbols'
        assert result['pair_segments'][index]['counts']['identity_fraction']['value'] is None
    pair = result['pair_segments'][2]
    assert pair['counts']['identical_canonical']['value'] == pair['counts']['comparable_canonical']['value'] == 4
    assert pair['counts']['a_only_gap']['value'] == 265
    assert [(m['selected_nongap_count']['value'], m['selected_gap_count']['value']) for m in result['member_segments'][4:6]] == [(4, 265), (269, 0)]


def test_reverse_coordinates_selected_columns_and_nongap_coverage():
    d = parse(native('GappedAlignment\n6 -5 9\nAC-Nt-\nATGNa-\n', lengths=(20, 20)))['value']
    sel = selection(d); sel['population_scope'] = 'selected_segments'; sel['segments'][0]['column_ranges_0based_half_open'] = [[1, 4]]
    r = calculate_mauve_v4_segments(d, selection=sel, inputs=None)
    assert r['member_segments'][0]['native_interval_0based_half_open'] == [4, 8]
    assert r['coverage'][0]['known_union_intervals'] == [[5, 7]]
    assert r['member_segments'][0]['selected_gap_count']['value'] == 1
    counts = r['pair_segments'][0]['counts']
    assert [counts[k]['value'] for k in ('identical_canonical', 'substitutions', 'a_only_gap', 'ambiguous_or_other')] == [0, 1, 1, 1]
    assert counts['identity_fraction']['value'] == 0.0


def test_case_policy_changes_only_declared_symbol_count_population():
    d = parse(native('GappedAlignment\n4 1 1\nAcNN\nAcNN\n'))['value']; sel = selection(d)
    upper = calculate_mauve_v4_segments(d, selection=sel, inputs=None)
    sel['case_policy'] = 'preserve'
    lower = calculate_mauve_v4_segments(d, selection=sel, inputs=None)
    assert upper['pair_segments'][0]['counts']['comparable_canonical']['value'] == 2
    assert lower['pair_segments'][0]['counts']['comparable_canonical']['value'] == 1
    assert lower['member_segments'][0]['selected_other_count']['value'] == 1


def test_source_symbols_and_exact_denominator_are_separate_from_native_declarations():
    inputs = bound_inputs(); d = parse(native('4 1 1\n', lengths=(100, 100)))['value']
    sel = selection(d, denominator='validated_staged_length')
    r = calculate_mauve_v4_segments(d, selection=sel, inputs=inputs)
    assert r['pair_segments'][0]['counts']['identity_fraction']['value'] == 3 / 4
    assert r['member_segments'][0]['symbols_origin'] == 'source_extracted'
    assert r['member_segments'][0]['aligned_sequence'] == 'ACGT'
    assert r['coverage'][0]['coverage_fraction']['value'] == 4 / 6
    assert r['coverage'][0]['denominator_bases']['origin'] == 'calculated'
    sel['denominator'] = 'native_declared_length'
    declared = calculate_mauve_v4_segments(d, selection=sel, inputs=inputs)
    assert declared['coverage'][0]['coverage_fraction']['value'] == 4 / 100
    assert declared['coverage'][0]['denominator_bases']['origin'] == 'native_observation'


def test_reverse_source_extraction_and_cross_record_concatenation():
    r = calculate(native('4 -2 1\n'), inputs=bound_inputs(), denominator='validated_staged_length')
    assert r['member_segments'][0]['aligned_sequence'] == 'TACG'
    assert r['coverage'][0]['known_union_intervals'] == [[1, 5]]


@pytest.mark.parametrize('source_mutation', ['path', 'row_mismatch', 'outside'])
def test_source_conflict_preserves_native_counts_but_invalidates_source_fraction(source_mutation):
    inputs = bound_inputs()
    raw = native('GappedAlignment\n4 1 1\nACGT\nAAGT\n')
    if source_mutation == 'path': inputs['files'][0]['native_path_token'] = '/another/f0'
    elif source_mutation == 'row_mismatch': raw = native('GappedAlignment\n4 1 1\nTCGT\nAAGT\n')
    else: raw = native('GappedAlignment\n4 5 1\nACGT\nAAGT\n')
    r = calculate(raw, inputs=inputs, denominator='validated_staged_length')
    assert r['member_segments'][0]['selected_nongap_count']['value'] == 4
    assert r['pair_segments'][0]['counts']['comparable_canonical']['value'] == 4
    assert r['coverage'][0]['coverage_fraction']['state'] == 'incompatible'
    assert r['coverage'][0]['complement_intervals'] is None


@pytest.mark.parametrize('corruption', ['source_length', 'content_hash', 'member_component'])
def test_non_null_inputs_use_public_c_validator(corruption):
    inputs = bound_inputs()
    if corruption == 'source_length': inputs['member_bindings'][0]['source_length'] += 1
    elif corruption == 'content_hash': inputs['files'][0]['content']['sha256'] = 'f' * 64
    else: inputs['member_bindings'][0]['components'][0]['record_id'] = 'not-a-record'
    with pytest.raises(ValueError, match='bvbrc_genome_alignment_'):
        calculate(native(), inputs=inputs)


def test_single_file_members_use_actual_entry_axis_and_unknown_census_remains_unknown():
    inputs, _ = input_fixture(mode='single_file_entries')
    for i, row in enumerate(inputs['member_bindings']): row['member'] = member(i)
    r = calculate(native('2 1 1\n', paths=('/staged/f0', '/staged/f0')), inputs=inputs,
                  denominator='validated_staged_length')
    assert [c['denominator_bases']['value'] for c in r['coverage']] == [4, 2]
    assert r['pair_segments'][0]['counts']['identity_fraction']['value'] == 1
    assert inputs['genome_census_state'] == 'unknown'


def test_unverified_staged_binding_cannot_supply_symbols_or_denominator():
    inputs = bound_inputs()
    inputs['member_bindings'][0].update(state='unverified', source_length=None)
    inputs['files'][0]['same_run_state'] = 'unverified'
    r = calculate(native(), inputs=inputs, denominator='validated_staged_length')
    assert r['member_segments'][0]['symbols_origin'] == 'unavailable'
    assert r['coverage'][0]['denominator_bases']['state'] == 'missing'


@pytest.mark.parametrize('bad', [None, True, {}, [], float('nan')])
def test_malformed_saved_coverage_row_is_valueerror(bad):
    r = calculate(native())
    r['coverage'][0] = bad
    with pytest.raises(ValueError, match='mauve_v4_'): validate_mauve_v4_components(r)


def test_duplicate_overlapping_placements_use_unique_union_and_retain_multiplicity():
    r = calculate(native('4 1 1\n4 1 1\n4 3 3\n'), denominator='native_declared_length')
    cov = r['coverage'][0]
    assert [cov[k]['value'] for k in ('known_union_bases', 'placement_bases', 'multiply_represented_bases', 'excess_placement_bases')] == [6, 12, 4, 6]
    assert cov['coverage_fraction']['value'] == 6 / 12
    assert len(cov['placements']) == 3


@pytest.mark.parametrize('body', ['GappedAlignment\n4 1 1\nACGT\n', 'GappedAlignment\n4 1 1\nACGT\nACG\n', 'GappedAlignment\n4 1 1\nACGT\nACGT\nACGT\n'])
def test_incomplete_or_malformed_n_rows_never_certify_remaining_positional_membership(body):
    r = calculate(native(body), denominator='native_declared_length')
    assert all(x['state'] in ('missing', 'incompatible') for x in r['member_segments'])
    assert all(x['selected_nongap_count']['value'] is None for x in r['member_segments'])
    assert r['pair_segments'][0]['counts']['identity_fraction']['value'] is None
    assert r['coverage'][0]['population_state'] == 'partial_selected'
    assert r['coverage'][0]['coverage_fraction']['state'] == (
        'truncated' if r['member_segments'][0]['state'] == 'missing' else 'incompatible')


def test_unaffected_subset_survives_neighboring_partial_segment():
    d = parse(native('GappedAlignment\n4 1 1\nACGT\n4 8 8\n'))['value']; sel = selection(d, denominator='native_declared_length', pairs=False)
    sel['segments'] = sel['segments'][1:]; sel['population_scope'] = 'selected_segments'
    r = calculate_mauve_v4_segments(d, selection=sel, inputs=None)
    assert r['coverage'][0]['population_state'] == 'complete_selected'
    assert r['coverage'][0]['coverage_fraction']['value'] == 4 / 12


def test_conflicting_format_version_never_wins_even_for_explicit_subset():
    d = parse(native('GappedAlignment\n4 1 1\nACGT\nACGT\n').replace(
        'FormatVersion\t4', 'FormatVersion\t4\nFormatVersion\t5'))['value']
    sel = selection(d); sel['population_scope'] = 'selected_segments'
    r = calculate_mauve_v4_segments(d, selection=sel, inputs=None)
    assert all(row['state'] == 'incompatible' for row in r['member_segments'])
    assert r['pair_segments'][0]['state'] == 'incompatible'


def test_missing_source_denominator_and_no_requested_denominator_remain_distinct():
    missing = calculate(native('GappedAlignment\n4 1 1\nACGT\nACGT\n'), denominator='validated_staged_length')
    not_requested = calculate(native('GappedAlignment\n4 1 1\nACGT\nACGT\n'))
    assert missing['pair_segments'][0]['counts']['identity_fraction']['value'] == 1
    assert missing['coverage'][0]['coverage_fraction']['state'] == 'missing'
    assert not_requested['coverage'][0]['coverage_fraction']['state'] == 'not_measured'
    assert missing['requirements'] and not not_requested['requirements']


def test_conflicting_native_denominator_is_incompatible_and_requires_primary_output():
    raw = native('GappedAlignment\n4 1 1\nACGT\nACGT\n').replace(
        'Sequence0Length\t12', 'Sequence0Length\t12\nSequence0Length\t13')
    r = calculate(raw, denominator='native_declared_length')
    assert r['coverage'][0]['denominator_bases']['state'] == 'incompatible'
    assert r['coverage'][0]['coverage_fraction']['state'] == 'incompatible'
    reqs = [q for q in r['requirements'] if q['reason_code'] == 'mauve_v4_source_denominator_missing']
    assert reqs[0]['kind'] == 'output_bytes' and reqs[0]['role'] == 'genome_alignment_primary'


def test_malformed_native_width_has_unavailable_counts_without_losing_other_segment():
    d = parse(native('NaN 1 1\n4 8 8\n'))['value']; sel = selection(d, pairs=False)
    sel['segments'][0]['column_ranges_0based_half_open'] = []
    r = calculate_mauve_v4_segments(d, selection=sel, inputs=None)
    assert r['member_segments'][0]['alignment_columns']['state'] == 'incompatible'
    assert r['member_segments'][2]['selected_nongap_count']['value'] == 4
    assert r['coverage'][0]['known_union_bases']['value'] == 4
    assert r['coverage'][0]['population_state'] == 'partial_selected'


def test_coordinate_only_large_span_calculates_without_expanding_per_base():
    r = calculate(native('1000000000000 1 1\n', lengths=(1000000000000, 1000000000000)), denominator='native_declared_length')
    assert r['coverage'][0]['known_union_bases']['value'] == 1000000000000
    assert r['coverage'][0]['coverage_fraction']['value'] == 1


def test_measured_zero_identity_missing_symbols_and_not_measured_absence_are_distinct():
    mismatch = calculate(native('GappedAlignment\n4 1 1\nAAAA\nCCCC\n'))
    missing = calculate(native())
    absent = calculate(native('GappedAlignment\n4 0 1\n----\nCCCC\n'))
    assert mismatch['pair_segments'][0]['counts']['identity_fraction']['value'] == 0
    assert missing['pair_segments'][0]['counts']['identity_fraction']['state'] == 'missing'
    assert absent['pair_segments'][0]['state'] == 'not_coobserved'
    assert absent['pair_segments'][0]['counts']['identity_fraction']['state'] == 'not_measured'
    assert absent['member_segments'][0]['selected_gap_count']['value'] == 4
    assert absent['coverage'][0]['known_union_bases']['value'] == 0


def test_zero_canonical_denominator_and_zero_native_length_are_not_zero_fractions():
    r = calculate(native('GappedAlignment\n4 1 1\nNNNN\nNNNN\n'))
    f = r['pair_segments'][0]['counts']['identity_fraction']
    assert (f['state'], f['value'], f['numerator'], f['denominator']) == ('not_measured', None, 0, 0)
    d = parse(native('', lengths=(0, 0)).replace('IntervalCount\t1\nInterval 0\n', 'IntervalCount\t0\n'))['value']
    z = calculate_mauve_v4_segments(d, selection=selection(d, denominator='native_declared_length'), inputs=None)
    assert z['coverage'][0]['coverage_fraction']['state'] == 'not_measured'
    assert z['coverage'][0]['complement_bases']['value'] == 0


@pytest.mark.parametrize('mutation', ['document', 'member', 'record', 'column', 'all_scope', 'pair_order', 'duplicate_pair', 'overlapping_ranges', 'bool_index'])
def test_invalid_caller_selection_raises(mutation):
    d = parse(native())['value']; s = selection(d)
    if mutation == 'document': s['document_id'] = 'foreign'
    elif mutation == 'member': s['members'].append(member(7))
    elif mutation == 'record': s['segments'][0]['segment_index'] = 5
    elif mutation == 'column': s['segments'][0]['column_ranges_0based_half_open'] = [[0, 5]]
    elif mutation == 'all_scope': s['segments'] = []
    elif mutation == 'pair_order': s['pairs'][0] = {'member_a': member(1), 'member_b': member(0)}
    elif mutation == 'duplicate_pair': s['pairs'] *= 2
    elif mutation == 'overlapping_ranges': s['segments'][0]['column_ranges_0based_half_open'] = [[0, 3], [2, 4]]
    else: s['members'][0]['index'] = True
    with pytest.raises(ValueError, match='mauve_v4_'): calculate_mauve_v4_segments(d, selection=s, inputs=None)


@pytest.mark.parametrize('mutation', ['count', 'fraction', 'unit', 'method', 'requirement', 'placement', 'population', 'native_interval'])
def test_saved_components_reject_altered_numeric_relationships(mutation):
    r = calculate(native('GappedAlignment\n4 1 1\nACGT\nACGT\n'), denominator='native_declared_length')
    if mutation == 'count': r['pair_segments'][0]['counts']['comparable_canonical']['value'] = 3
    elif mutation == 'fraction': r['coverage'][0]['coverage_fraction']['value'] = 0.9
    elif mutation == 'unit': r['member_segments'][0]['selected_gap_count']['unit'] = 'confidence'
    elif mutation == 'method': r['coverage'][0]['denominator_bases']['method_id'] = 'invented'
    elif mutation == 'requirement': r['member_segments'][0]['requirement_ids'] = ['invented']
    elif mutation == 'placement': r['coverage'][0]['placements'][0]['interval_0based_half_open'] = [0, 5]
    elif mutation == 'population': r['coverage'][0]['population_state'] = 'partial_selected'
    else: r['member_segments'][0]['native_interval_0based_half_open'] = [2, 6]
    with pytest.raises(ValueError): validate_mauve_v4_components(r)


def test_recalculation_and_saved_validation_without_io_parsers_or_native_execution(monkeypatch):
    import gene_annotation_episode.mauve_v4_formats as formats
    import gene_annotation_episode.mauve_v4_calculators as calculators
    d = json.loads(json.dumps(parse(native('4 1 1\n'))['value'])); inputs = json.loads(json.dumps(bound_inputs()))
    s = selection(d, denominator='validated_staged_length')
    first = calculate_mauve_v4_segments(d, selection=s, inputs=inputs); saved = deepcopy(first)
    def forbidden(*args, **kwargs): raise AssertionError('unexpected I/O or scientific rerun')
    for name in ('open',): monkeypatch.setattr(builtins, name, forbidden)
    for name in ('read_bytes', 'read_text', 'write_bytes', 'write_text'): monkeypatch.setattr(Path, name, forbidden)
    monkeypatch.setattr(socket, 'socket', forbidden); monkeypatch.setattr(subprocess, 'Popen', forbidden)
    monkeypatch.setattr(formats, 'parse_mauve_v4', forbidden)
    s['population_scope'] = 'selected_segments'; s['segments'][0]['column_ranges_0based_half_open'] = [[0, 2]]
    second = calculate_mauve_v4_segments(d, selection=s, inputs=inputs)
    assert first == saved and first['coverage'][0]['known_union_bases']['value'] == 4
    assert second['coverage'][0]['known_union_bases']['value'] == 2
    monkeypatch.setattr(calculators, 'calculate_mauve_v4_segments', forbidden)
    assert validate_mauve_v4_components(saved) == saved
    assert validate_mauve_v4_selection(s) == s
