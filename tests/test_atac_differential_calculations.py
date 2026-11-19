"""Contract 005/006 checks; native oracles are retained, never reacquired.

The small file decoder below constructs the already-agreed numerical input
port for these calculator tests. It is not a production parser or a claim of
native-reader/episode-path integration.
"""
from copy import deepcopy
import hashlib
import json
import math
import os
from pathlib import Path
import socket
import struct
import subprocess

import pytest

from gene_annotation_episode.atac_differential_calculations import (
    iter_atac_track_segments, iter_atac_interval_components, iter_atac_differential_regions,
)


ROLES = ('signal1', 'background1', 'signal2', 'background2')
LIKELIHOODS = ('condition1_vs_background', 'condition2_vs_background', 'condition1_vs_condition2')
MAX_COORDINATE = 2**63 - 1


def row(start, end, value=1.0, *, ordinal=0, chromosome='chr1', lexeme=None):
    return (ordinal, ordinal + 1, ordinal * 20, (ordinal + 1) * 20,
            chromosome, start, end, value, str(value) if lexeme is None else lexeme)


def population(start=0, end=100, chromosome='chr1'):
    return {'chromosome': chromosome, 'start': start, 'end': end}


def tracks(rows=None, **overrides):
    source = [row(0, 100)] if rows is None else rows
    result = {role: {'rows': list(source), 'extent': 'complete',
                     'unlocated_invalid_row_count': 0} for role in ROLES}
    for role, supplied in overrides.items():
        result[role].update(supplied if isinstance(supplied, dict) else {'rows': supplied})
    return result


def native_rows(path):
    """Read every known-valid fixture row, retaining physical byte locations."""
    offset, result = 0, []
    for line_number, line in enumerate(path.read_bytes().splitlines(keepends=True), 1):
        chromosome, start, end, lexeme = line.decode('utf-8').rstrip('\r\n').split('\t')
        result.append((len(result), line_number, offset, offset + len(line), chromosome,
                       int(start), int(end), float(lexeme), lexeme))
        offset += len(line)
    return result


def native_tracks(directory, names):
    return {role: {'rows': native_rows(directory / name), 'extent': 'complete',
                   'unlocated_invalid_row_count': 0} for role, name in zip(ROLES, names)}


def segments(source, populations=None):
    return list(iter_atac_track_segments(source,
                intervals=[population()] if populations is None else populations))


def components(source, populations=None, *, depth1=1, depth2=2, depth_unit='million_tags', pseudocount=0.01):
    return list(iter_atac_interval_components(
        iter_atac_track_segments(source, intervals=[population()] if populations is None else populations),
        depth1=depth1, depth2=depth2, depth_unit=depth_unit, pseudocount=pseudocount))


def regions(records, *, cutoff=3, min_length_bp=1, max_gap_bp=0):
    return list(iter_atac_differential_regions(records, cutoff=cutoff,
                                              min_length_bp=min_length_bp, max_gap_bp=max_gap_bp))


def likelihood_component(start, end, first, second, between, *, ordinal=0,
                         population_ordinal=0, chromosome='chr1', partial_role=None):
    """Explicit synthetic likelihood cells isolate category/merge mathematics."""
    item = {
        'interval_ordinal': ordinal, 'population_ordinal': population_ordinal,
        'chromosome': chromosome, 'start': start, 'end': end,
        'values': {role: 1.0 for role in ROLES}, 'states': {role: 'observed' for role in ROLES},
        'source_rows': {role: [ordinal] for role in ROLES},
        'source_extents': {role: 'complete' for role in ROLES},
        'unlocated_invalid_rows': {role: 0 for role in ROLES},
        'scores': {'likelihoods': {
            name: {'native_float32': {'value': value, 'state': 'derived' if value is not None else 'missing',
                                      'reason': None if value is not None else 'operand_unavailable',
                                      'unit': 'signed_log10_likelihood_ratio'}}
            for name, value in zip(LIKELIHOODS, (first, second, between))}},
    }
    if partial_role is not None:
        item['values'][partial_role] = None
        item['states'][partial_role] = 'missing'
        item['source_rows'][partial_role] = []
    return item


def series(specs, **kwargs):
    position, result = 0, []
    for ordinal, (length, first, second, between) in enumerate(specs):
        result.append(likelihood_component(position, position + length, first, second, between,
                                           ordinal=ordinal, **kwargs))
        position += length
    return result


def for_category(result, category='condition1'):
    return [region for region in result if region['category'] == category]


def forbid_acquisition(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('saved-data calculation attempted native execution or network acquisition')
    for name in ('Popen', 'run', 'call', 'check_call', 'check_output'):
        monkeypatch.setattr(subprocess, name, forbidden)
    monkeypatch.setattr(os, 'system', forbidden)
    monkeypatch.setattr(socket, 'socket', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)


def test_actual_boundary_union_clips_but_keeps_original_source_ordinals():
    source = tracks([row(0, 100)], signal1=[row(0, 40, 2, ordinal=8), row(40, 100, 3, ordinal=2)],
                    signal2=[row(0, 30, 4, ordinal=7), row(30, 100, 5, ordinal=1)])
    result = segments(source, [population(15, 65)])
    assert [(item['start'], item['end']) for item in result] == [(15, 30), (30, 40), (40, 65)]
    assert [item['source_rows']['signal1'] for item in result] == [[8], [8], [2]]
    assert [item['source_rows']['signal2'] for item in result] == [[7], [1], [1]]
    assert [item['values']['signal1'] for item in result] == [2, 2, 3]


def test_equal_value_adjacent_source_rows_still_split_the_partition():
    source = tracks([row(0, 50, 1, ordinal=4), row(50, 100, 1, ordinal=9)])
    assert [(item['start'], item['end']) for item in segments(source)] == [(0, 50), (50, 100)]


def test_population_and_exact_chromosome_separation_without_alias_guessing():
    source = tracks([row(0, 100, 4, chromosome='1'), row(0, 50, 2, ordinal=1, chromosome='chr1')])
    populations = [population(0, 25, 'chr1'), population(25, 75, 'chr1'), population(0, 30, 'chr2')]
    result = segments(source, populations)
    assert [(item['population_ordinal'], item['start'], item['end']) for item in result] == [
        (0, 0, 25), (1, 25, 50), (1, 50, 75), (2, 0, 30)]
    assert result[0]['values']['signal1'] == 2
    assert result[-1]['states'] == {role: 'missing' for role in ROLES}


def test_zero_gaps_tails_missing_and_empty_complete_sources_remain_distinct():
    source = tracks([], signal1=[row(10, 20, 0), row(30, 40, 2, ordinal=1)],
                    background2={'rows': [], 'extent': 'missing'})
    result = segments(source, [population(0, 50)])
    assert [(item['start'], item['end']) for item in result] == [(0, 10), (10, 20), (20, 30), (30, 40), (40, 50)]
    assert [item['states']['signal1'] for item in result] == ['missing', 'observed', 'missing', 'observed', 'missing']
    assert result[1]['values']['signal1'] == 0
    assert result[1]['source_extents']['signal2'] == 'complete'
    assert result[1]['source_extents']['background2'] == 'missing'


def test_duplicate_overlapping_rows_are_ambiguous_and_independent_spans_survive():
    source = tracks(signal1=[row(0, 50, 2, ordinal=4), row(0, 50, 2, ordinal=9), row(30, 80, 3, ordinal=2)])
    result = segments(source)
    assert [(item['start'], item['end']) for item in result] == [(0, 30), (30, 50), (50, 80), (80, 100)]
    assert [item['source_rows']['signal1'] for item in result] == [[4, 9], [2, 4, 9], [2], []]
    assert [item['states']['signal1'] for item in result] == ['ambiguous', 'ambiguous', 'observed', 'missing']
    assert [item['values']['signal1'] for item in result] == [None, None, 3, None]


def test_invalid_negative_cells_and_unlocated_corruption_preserve_raw_values_and_ambiguity():
    source = tracks(signal1=[row(0, 25, -2), row(25, 50, None, ordinal=1), row(50, 100, 0, ordinal=2)],
                    signal2={'rows': [row(0, 75, 7), row(50, 100, 8, ordinal=1)], 'unlocated_invalid_row_count': 1})
    result = segments(source)
    assert [item['values']['signal1'] for item in result] == [-2, None, 0, 0]
    assert [item['states']['signal1'] for item in result] == ['invalid', 'invalid', 'observed', 'observed']
    assert [item['states']['signal2'] for item in result] == ['invalid', 'invalid', 'ambiguous', 'invalid']
    assert [item['values']['signal2'] for item in result] == [7, 7, None, 8]
    assert all(item['unlocated_invalid_rows']['signal2'] == 1 for item in result)


def test_components_preserve_raw_segment_and_independent_valid_likelihoods():
    source = tracks(signal1=[row(0, 100, 20)], signal2=[row(0, 100, 2)], background2=[])
    part = segments(source)[0]
    original = deepcopy(part)
    result = next(iter_atac_interval_components([part], depth1=1, depth2=2,
                                              depth_unit='million_tags', pseudocount=0.01))
    assert {name: result[name] for name in part} == part == original
    assert result['scores']['likelihoods']['condition1_vs_background']['native_float32']['value'] == 17.699888229370117
    assert result['scores']['likelihoods']['condition1_vs_condition2']['native_float32']['value'] == 17.7408447265625
    assert result['scores']['likelihoods']['condition2_vs_background']['native_float32']['value'] is None
    result['source_rows']['signal1'].append(999)
    assert part == original


def test_unusable_raw_values_are_not_passed_as_measured_operands():
    source = tracks(signal1=[row(0, 100, -7)], background1={'unlocated_invalid_row_count': 1})
    result = components(source)[0]
    assert result['values']['signal1'] == -7 and result['values']['background1'] == 1
    assert result['scores']['inputs']['signal1'] is None
    assert result['scores']['inputs']['background1'] is None
    assert result['scores']['likelihoods']['condition2_vs_background']['native_float32']['value'] == 0


@pytest.mark.parametrize('extent', ['partial', 'failed'])
def test_source_extent_does_not_erase_readable_scientific_components(extent):
    source = tracks([row(0, 100, 20)], background1=[row(0, 100, 1)],
                    signal2=[row(0, 100, 2)], background2={'extent': extent})
    result = components(source)
    assert result[0]['states']['background2'] == 'observed'
    assert result[0]['source_extents']['background2'] == extent
    assert result[0]['scores']['likelihoods']['condition1_vs_background']['native_float32']['value'] is not None
    assert for_category(regions(result))[0]['source_extent'] == 'partial'


@pytest.mark.parametrize('depth1,depth2', [(None, 2), (0, 2), (1, None), (1, -2)])
def test_missing_or_invalid_depth_does_not_invent_equal_factors(depth1, depth2):
    result = components(tracks(), depth1=depth1, depth2=depth2)[0]
    assert all(item['value'] is None for item in result['scores']['depth_factors'].values())
    assert regions([result]) == []


def test_region_weighted_mean_excludes_an_observed_bridged_gap():
    records = series([(10, 9, 0, 4), (3, 0, 0, 0), (20, 9, 0, 10)])
    result = for_category(regions(records, min_length_bp=25, max_gap_bp=3))
    assert len(result) == 1
    item = result[0]
    assert (item['start'], item['end'], item['span_bp'], item['qualifying_bp'], item['bridged_gap_bp']) == (0, 33, 33, 30, 3)
    assert item['qualifying_interval_ordinals'] == [0, 2]
    assert item['score_numerator'] == 240
    assert item['score_denominator_bp'] == 30
    assert item['mean_score'] == item['native_float32_mean_score'] == 8
    assert item['left_boundary'] == item['right_boundary'] == 'population_boundary'


def test_minimum_length_uses_observed_region_span_including_the_bridged_gap():
    records = series([(2, 9, 0, 4), (3, 0, 0, 0), (5, 9, 0, 10)])
    item = for_category(regions(records, min_length_bp=10, max_gap_bp=3))[0]
    assert item['span_bp'] == 10 and item['qualifying_bp'] == 7
    assert item['score_numerator'] == 58
    assert item['mean_score'] == 58 / 7
    assert for_category(regions(records, min_length_bp=11, max_gap_bp=3)) == []


def test_exact_maximum_gap_is_bridged_but_one_more_base_separates_regions():
    joined = series([(10, 9, 0, 4), (3, 0, 0, 0), (10, 9, 0, 8)])
    split = series([(10, 9, 0, 4), (4, 0, 0, 0), (10, 9, 0, 8)])
    assert len(for_category(regions(joined, min_length_bp=10, max_gap_bp=3))) == 1
    result = for_category(regions(split, min_length_bp=10, max_gap_bp=3))
    assert [(item['start'], item['end']) for item in result] == [(0, 10), (14, 24)]
    assert result[0]['right_boundary'] == result[1]['left_boundary'] == 'observed_gap'


def test_unknown_membership_breaks_regions_even_within_permitted_gap():
    records = series([(10, 9, 0, 4), (1, 9, 0, None), (10, 9, 0, 8)])
    result = for_category(regions(records, min_length_bp=10, max_gap_bp=3))
    assert [(item['start'], item['end']) for item in result] == [(0, 10), (11, 21)]
    assert result[0]['right_boundary'] == result[1]['left_boundary'] == 'unknown_gap'
    assert all(item['source_extent'] == 'partial' for item in result)
    assert all(item['bridged_gap_bp'] == 0 for item in result)


@pytest.mark.parametrize('gap,expected', [(2, 'unknown_gap'), (3, 'unknown_gap'), (4, 'observed_gap')])
def test_unknown_boundary_remains_relevant_until_known_false_gap_exceeds_maximum(gap, expected):
    records = series([(10, 9, 0, 4), (gap, 0, 0, 0), (1, 9, 0, None),
                      (gap, 0, 0, 0), (10, 9, 0, 8)])
    result = for_category(regions(records, min_length_bp=10, max_gap_bp=3))
    assert result[0]['right_boundary'] == result[1]['left_boundary'] == expected
    assert all(item['source_extent'] == ('partial' if expected == 'unknown_gap' else 'complete') for item in result)


@pytest.mark.parametrize('gap,expected', [(2, 'population_boundary'), (3, 'population_boundary'), (4, 'observed_gap')])
def test_population_boundary_remains_relevant_across_short_false_prefix_and_suffix(gap, expected):
    records = series([(gap, 0, 0, 0), (10, 9, 0, 4), (gap, 0, 0, 0)])
    item = for_category(regions(records, min_length_bp=10, max_gap_bp=3))[0]
    assert item['left_boundary'] == item['right_boundary'] == expected
    assert (item['start'], item['end']) == (gap, gap + 10)
    assert item['qualifying_bp'] == 10 and item['bridged_gap_bp'] == 0


def test_known_false_predicate_with_unknown_operand_can_bridge_but_marks_partial_input():
    records = series([(10, 9, 0, 4), (2, 0, None, None), (10, 9, 0, 8)])
    records[1]['values']['signal2'] = None
    records[1]['states']['signal2'] = 'missing'
    records[1]['source_rows']['signal2'] = []
    item = for_category(regions(records, min_length_bp=10, max_gap_bp=2))[0]
    assert item['span_bp'] == 22 and item['score_denominator_bp'] == 20
    assert item['mean_score'] == 6 and item['source_extent'] == 'partial'


def test_unused_unavailable_background_does_not_erase_known_directional_membership():
    records = [likelihood_component(0, 10, 8, None, 4, partial_role='background2')]
    item = for_category(regions(records))[0]
    assert item['mean_score'] == 4 and item['source_extent'] == 'partial'
    assert for_category(regions(records), 'common') == []


def test_unbridged_incomplete_false_suffix_does_not_enter_region_score_or_source_extent():
    records = series([(10, 9, 0, 4), (2, 0, None, None)])
    records[1]['source_extents']['signal2'] = 'partial'
    item = for_category(regions(records, min_length_bp=10, max_gap_bp=2))[0]
    assert item['source_extent'] == 'complete'
    assert item['score_denominator_bp'] == 10 and item['score_numerator'] == 40


@pytest.mark.parametrize('between,directional', [(3, 'condition1'), (-3, 'condition2')])
def test_inclusive_native_threshold_tie_preserves_overlapping_categories(between, directional):
    result = regions([likelihood_component(0, 10, 3, 3, between)])
    assert [item['category'] for item in result] == [directional, 'common']
    assert all(item['mean_score'] == 3 for item in result)
    assert all(item['qualifying_interval_ordinals'] == [0] for item in result)


def test_zero_cutoff_can_assign_all_three_categories_without_exclusivity():
    result = regions([likelihood_component(0, 10, 0, 0, 0)], cutoff=0)
    assert [item['category'] for item in result] == ['condition1', 'condition2', 'common']
    assert all(item['mean_score'] == 0 for item in result)


def test_negative_between_condition_score_is_negated_for_condition_two():
    item = for_category(regions(series([(10, 0, 10, -4), (20, 0, 10, -7)])), 'condition2')[0]
    assert item['score_numerator'] == 180 and item['mean_score'] == 6


def test_population_intervals_and_chromosomes_never_merge_even_when_touching():
    records = [likelihood_component(0, 10, 9, 0, 4),
               likelihood_component(10, 20, 9, 0, 8, ordinal=1, population_ordinal=1),
               likelihood_component(0, 10, 9, 0, 10, ordinal=2, population_ordinal=2, chromosome='chr2')]
    result = for_category(regions(records, min_length_bp=10, max_gap_bp=9))
    assert [item['population_ordinal'] for item in result] == [0, 1, 2]
    assert [item['mean_score'] for item in result] == [4, 8, 10]
    assert all(item['left_boundary'] == item['right_boundary'] == 'population_boundary' for item in result)


def test_region_binary64_mean_and_separate_binary32_rounding_are_preserved():
    item = for_category(regions(series([(1, 9, 0, 4), (2, 9, 0, 5)])))[0]
    assert item['mean_score'] == 14 / 3
    assert item['native_float32_mean_score'] == struct.unpack('<f', struct.pack('<f', 14 / 3))[0]
    assert item['mean_score'] != item['native_float32_mean_score']
    assert item['numerical_reason'] is None


def test_defensive_float32_mean_overflow_keeps_finite_binary64_result():
    # Synthetic supplied cells deliberately exceed binary32. Ordinary leaf
    # outputs cannot have this magnitude; this exercises the output safeguard.
    item = for_category(regions([likelihood_component(0, 2, 1e39, 0, 1e39)]))[0]
    assert item['score_numerator'] == 2e39 and item['mean_score'] == 1e39
    assert item['native_float32_mean_score'] is None
    assert item['numerical_reason'] == 'float32_overflow'
    json.dumps(item, allow_nan=False)


@pytest.mark.parametrize('cutoff,min_length,max_gap', [
    (-1, 1, 0), (math.nan, 1, 0), (math.inf, 1, 0), (True, 1, 0), ('3', 1, 0),
    (3, 0, 0), (3, 1.0, 0), (3, True, 0), (3, 1, -1), (3, 1, False), (3, 1, 1), (3, 2, 3),
])
def test_invalid_region_parameters_raise_on_empty_input(cutoff, min_length, max_gap):
    with pytest.raises(ValueError):
        regions([], cutoff=cutoff, min_length_bp=min_length, max_gap_bp=max_gap)


@pytest.mark.parametrize('populations', [
    [population(0, 0)], [population(-1, 10)], [population(0, MAX_COORDINATE + 1)],
    [population(0.0, 10)], [population(False, 10)], [population(0, 10, '')],
    [population(0, 20), population(10, 30)],
    [population(0, 10, 'chr2'), population(0, 10, 'chr1')],
])
def test_invalid_or_unsorted_population_geometry_is_rejected(populations):
    with pytest.raises(ValueError):
        segments(tracks(), populations)


@pytest.mark.parametrize('replacement', [
    None, (0,), row(0, 0), row(-1, 10), row(0, MAX_COORDINATE + 1), row(False, 10),
    row(0, 10, math.nan), row(0, 10, math.inf), row(0, 10, True), row(0, 10, '1'),
])
def test_invalid_track_port_rows_do_not_become_zero_or_silent_end(replacement):
    with pytest.raises(ValueError):
        segments(tracks(signal1=[replacement]))


@pytest.mark.parametrize('mutation', ['missing_role', 'extra_role', 'bad_extent', 'negative_count', 'bool_count', 'not_iterable'])
def test_invalid_track_port_declarations_raise(mutation):
    source = tracks()
    if mutation == 'missing_role':
        del source['signal1']
    elif mutation == 'extra_role':
        source['signal3'] = source['signal1']
    elif mutation == 'bad_extent':
        source['signal1']['extent'] = 'unknown'
    elif mutation == 'negative_count':
        source['signal1']['unlocated_invalid_row_count'] = -1
    elif mutation == 'bool_count':
        source['signal1']['unlocated_invalid_row_count'] = True
    else:
        source['signal1']['rows'] = None
    with pytest.raises(ValueError):
        segments(source)


def test_out_of_order_track_failure_preserves_previously_emitted_segments():
    source = tracks(signal1=[row(0, 10), row(10, 20, ordinal=1), row(20, 30, ordinal=2), row(5, 6, ordinal=3)])
    stream = iter_atac_track_segments(source, intervals=[population()])
    observed = [next(stream), next(stream)]
    assert [(item['start'], item['end']) for item in observed] == [(0, 10), (10, 20)]
    with pytest.raises(ValueError, match='atac_track_rows_out_of_order'):
        next(stream)
    assert observed[1]['source_rows']['signal1'] == [1]


def test_all_supplied_streams_are_drained_without_creating_extra_population_rows():
    reads = {role: 0 for role in ROLES}
    def supplied(role):
        for ordinal in range(100):
            reads[role] += 1
            yield row(ordinal * 10, ordinal * 10 + 10, ordinal=ordinal)
    source = {role: {'rows': supplied(role), 'extent': 'complete', 'unlocated_invalid_row_count': 0} for role in ROLES}
    result = segments(source, [population(0, 5)])
    assert len(result) == 1 and reads == {role: 100 for role in ROLES}


def test_streaming_partition_reads_only_active_rows_and_one_lookahead():
    reads = {role: 0 for role in ROLES}
    def supplied(role):
        for ordinal in range(10000):
            reads[role] += 1
            yield row(ordinal * 10, ordinal * 10 + 10, ordinal=ordinal)
    source = {role: {'rows': supplied(role), 'extent': 'complete', 'unlocated_invalid_row_count': 0} for role in ROLES}
    stream = iter_atac_track_segments(source, intervals=[population(0, 100000)])
    assert reads == {role: 0 for role in ROLES}
    assert next(stream)['end'] == 10
    assert reads == {role: 2 for role in ROLES}
    for ordinal in range(1, 10):
        assert next(stream)['interval_ordinal'] == ordinal
    assert reads == {role: 11 for role in ROLES}
    count = 10
    for item in stream:
        count += 1
    assert count == 10000 and reads == {role: 10000 for role in ROLES}


def test_huge_coordinate_span_uses_boundaries_not_per_base_expansion():
    source = tracks([row(0, MAX_COORDINATE, 0)])
    result = segments(source, [population(1, MAX_COORDINATE)])
    assert len(result) == 1
    assert result[0]['start'] == 1 and result[0]['end'] == MAX_COORDINATE


def test_population_iterator_is_not_materialized_before_first_output():
    def supplied():
        yield population(0, 10)
        raise RuntimeError('later_population_failure')
    stream = iter_atac_track_segments(tracks(), intervals=supplied())
    assert next(stream)['end'] == 10
    with pytest.raises(RuntimeError, match='later_population_failure'):
        next(stream)


def test_component_iterator_is_lazy_and_preserves_partial_failure():
    def supplied():
        yield segments(tracks())[0]
        raise RuntimeError('later_segment_failure')
    stream = iter_atac_interval_components(supplied(), depth1=1, depth2=2, depth_unit='million_tags', pseudocount=0.01)
    first = next(stream)
    with pytest.raises(RuntimeError, match='later_segment_failure'):
        next(stream)
    assert first['scores']['inputs']['signal1'] == 1


def test_region_iterator_emits_closed_regions_before_a_later_failure():
    def supplied():
        yield likelihood_component(0, 10, 9, 0, 4)
        yield likelihood_component(10, 11, 0, 0, 0, ordinal=1)
        raise RuntimeError('later_component_failure')
    stream = iter_atac_differential_regions(supplied(), cutoff=3, min_length_bp=10, max_gap_bp=0)
    first = next(stream)
    assert first['start'] == 0 and first['end'] == 10 and first['mean_score'] == 4
    with pytest.raises(RuntimeError, match='later_component_failure'):
        next(stream)


@pytest.mark.parametrize('second', [
    likelihood_component(9, 20, 9, 0, 4, ordinal=1),
    likelihood_component(11, 20, 9, 0, 4, ordinal=1),
    likelihood_component(10, 20, 9, 0, 4, ordinal=0),
    likelihood_component(10, 20, 9, 0, 4, ordinal=1, chromosome='chr2'),
    likelihood_component(0, 10, 9, 0, 4, ordinal=1, population_ordinal=1, chromosome='chr0'),
])
def test_region_order_validation_does_not_bridge_omitted_or_overlapping_intervals(second):
    with pytest.raises(ValueError, match='atac_components_out_of_partition_order'):
        regions([likelihood_component(0, 10, 9, 0, 4), second])


def test_empty_populations_components_and_region_streams_have_no_fabricated_results():
    assert segments(tracks([]), []) == []
    assert list(iter_atac_interval_components([], depth1=None, depth2=None, depth_unit='tags', pseudocount=0.01)) == []
    assert regions([]) == []


@pytest.mark.parametrize('depth_unit,pseudocount,error', [
    ('unknown', 0.01, 'atac_depth_unit_required'),
    (None, 0.01, 'atac_depth_unit_required'),
    ('tags', 0, 'atac_positive_finite_pseudocount_required'),
    ('tags', -1, 'atac_positive_finite_pseudocount_required'),
    ('tags', math.nan, 'atac_positive_finite_pseudocount_required'),
    ('tags', math.inf, 'atac_positive_finite_pseudocount_required'),
    ('tags', True, 'atac_positive_finite_pseudocount_required'),
    ('tags', '0.01', 'atac_positive_finite_pseudocount_required'),
])
def test_empty_component_population_does_not_validate_invalid_parameters(depth_unit, pseudocount, error):
    with pytest.raises(ValueError, match=error):
        list(iter_atac_interval_components([], depth1=None, depth2=None,
                                          depth_unit=depth_unit, pseudocount=pseudocount))


def test_component_parameters_are_validated_before_consuming_supplied_segments():
    def not_read():
        raise AssertionError('invalid declaration must not consume source data')
        yield
    with pytest.raises(ValueError, match='atac_positive_finite_pseudocount_required'):
        next(iter_atac_interval_components(not_read(), depth1=1, depth2=2,
                                           depth_unit='tags', pseudocount=0))
