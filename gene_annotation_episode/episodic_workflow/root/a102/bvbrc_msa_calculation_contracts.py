"""Detached MSA calculation-record and supplied-coordinate validators.

The values are ordinary closed records. Validation never authenticates source
custody, reads files, reparses native documents or selects execution work.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import math
import re

from . import phylogeny_calculation_contracts as shared
from .bvbrc_alignment_values import diagnostic, requirement, validate_numeric_cell
from .bvbrc_msa_format_contracts import _index, _require, _shape, _text


ENTROPY_METHOD = 'msa_literal_entropy_v1'
ROUNDING_METHOD = 'msa_literal_entropy_binary64_fixed2_v1'
RESIDUAL_METHOD = 'msa_observed_minus_selected_population_score_v1'
REFERENCE_METHOD = 'msa_reference_category_count_v1'
ROUNDING = 'binary64_fixed_2_ties_to_even'
CATEGORIES = ('identical_canonical', 'substitution', 'insertion_relative_to_reference',
              'deletion_relative_to_reference', 'both_gap', 'ambiguous_or_other')


def _indices(value):
    _require(type(value) is list, 'indices_invalid')
    for index in value:
        _index(index)
    _require(len(set(value)) == len(value), 'duplicate_index')


def _strings(value):
    _require(type(value) is list, 'strings_invalid')
    for item in value:
        _text(item)
    _require(len(set(value)) == len(value), 'duplicate_identifier')


def _metadata(value):
    _require(value['status'] in ('ok', 'partial', 'invalid'), 'status_invalid')
    for field in ('analysis_id', 'population_id', 'alignment_id'):
        _text(value[field])
    _require(type(value['requirements']) is list and type(value['diagnostics']) is list,
             'result_metadata_invalid')
    ids = []
    for row in value['requirements']:
        _shape(row, {'requirement_id', 'kind', 'role', 'source_refs', 'reason_code'},
               'requirement_shape_invalid')
        _require(type(row['source_refs']) is list, 'requirement_sources_invalid')
        _require(requirement(**row) == row, 'requirement_invalid')
        ids.append(row['requirement_id'])
    _require(len(set(ids)) == len(ids), 'duplicate_requirement')
    for row in value['diagnostics']:
        _shape(row, {'code', 'phase', 'path', 'severity', 'evidence_refs'}, 'diagnostic_shape_invalid')
        _require(type(row['evidence_refs']) is list, 'diagnostic_sources_invalid')
        _require(diagnostic(**row) == row, 'diagnostic_invalid')
    _require(value['status'] != 'ok' or not value['requirements'] and not value['diagnostics'],
             'status_qualification_conflict')
    return set(ids)


def _cell(value, *, population_id, method_id, unit, requirements, count=False):
    validate_numeric_cell(value)
    _require(value['population_id'] == population_id and value['method_id'] == method_id
             and value['unit'] == unit and value['origin'] == 'calculated', 'cell_meaning_conflict')
    _require(value['uncertainty'] is None, 'uncertainty_unmeasured')
    _require(type(value['requirement_ids']) is list and set(value['requirement_ids']) <= requirements,
             'cell_requirement_unresolved')
    if count and value['value'] is not None:
        _index(value['value'])
    _require(value['numerator'] is None, 'cell_numerator_invalid')
    if count:
        _require(value['denominator'] is None, 'count_denominator_invalid')


def _close(actual, expected):
    return math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12)


def _validate_reference(value):
    _shape(value, {'alignment_id', 'row_index', 'original_member', 'native_ref_type',
                   'native_ref_string', 'identity_state', 'evidence'}, 'reference_shape_invalid')
    _text(value['alignment_id'])
    _index(value['row_index'])
    _text(value['native_ref_type'])
    _require(value['native_ref_string'] is None or type(value['native_ref_string']) is str,
             'reference_string_invalid')
    _require(value['identity_state'] in ('resolved', 'unresolved'), 'reference_state_invalid')
    if value['original_member'] is not None:
        shared.member(value['original_member'])
    shared.evidence(value['evidence'])


def _validate_correspondence(value):
    _shape(value, {'alignment_id', 'row_index', 'column_0based', 'staged_ungapped_position_0based',
                  'original_member', 'original_interval_0based_half_open', 'strand',
                  'translation_table', 'transformation_id', 'evidence'}, 'correspondence_shape_invalid')
    _text(value['alignment_id'])
    _index(value['row_index'])
    _index(value['column_0based'])
    shared.integer(value['staged_ungapped_position_0based'], nullable=True)
    if value['original_member'] is not None:
        shared.member(value['original_member'])
    _require(value['strand'] in ('+', '-', 'unknown'), 'strand_invalid')
    shared.integer(value['translation_table'], nullable=True, minimum=1)
    shared.text(value['transformation_id'], nullable=True)
    shared.evidence(value['evidence'])
    interval = value['original_interval_0based_half_open']
    if interval is not None:
        _require(type(interval) is list and len(interval) == 2 and value['original_member'] is not None,
                 'original_interval_invalid')
        for index in interval:
            _index(index)
        _require(interval[0] < interval[1], 'original_interval_invalid')


def validate_msa_entropy_components(value: dict) -> dict:
    """Validate saved literal populations, numerical meanings and source IDs."""
    _shape(value, {'status', 'analysis_id', 'population_id', 'alignment_id', 'method_parameters',
                  'sites', 'requirements', 'diagnostics'}, 'entropy_components_shape_invalid')
    requirements = _metadata(value)
    params = value['method_parameters']
    _shape(params, {'alphabet', 'case_policy', 'terminal_gap', 'native_rounding'}, 'entropy_parameters_invalid')
    _require(params['alphabet'] in ('dna', 'protein') and params['case_policy'] == 'uppercase'
             and params['terminal_gap'] == '-' and params['native_rounding'] in (ROUNDING, None),
             'entropy_parameters_invalid')
    _require(type(value['sites']) is list, 'sites_invalid')
    columns = []
    for site in value['sites']:
        _shape(site, {'column_0based', 'included_row_indices', 'excluded_terminal_row_indices',
            'symbol_counts', 'eligible_count', 'internal_gap_count', 'terminal_gap_excluded_count',
            'literal_entropy_bits', 'native_score_recalculated', 'score_residual',
            'strict_majority_consensus', 'native_observation_ids'}, 'entropy_site_shape_invalid')
        _index(site['column_0based'])
        columns.append(site['column_0based'])
        for field in ('included_row_indices', 'excluded_terminal_row_indices'):
            _indices(site[field])
        _require(not set(site['included_row_indices']) & set(site['excluded_terminal_row_indices']),
                 'terminal_inclusion_conflict')
        _require(type(site['symbol_counts']) is list, 'symbol_counts_invalid')
        counts = {}
        for row in site['symbol_counts']:
            _shape(row, {'symbol', 'count'}, 'symbol_count_shape_invalid')
            _require(type(row['symbol']) is str and len(row['symbol']) == 1
                     and row['symbol'] == row['symbol'].upper(), 'literal_symbol_invalid')
            _require(type(row['count']) is int and row['count'] > 0, 'symbol_count_invalid')
            _require(row['symbol'] not in counts, 'duplicate_symbol')
            counts[row['symbol']] = row['count']
        n = sum(counts.values())
        _require(n == len(site['included_row_indices']), 'eligible_count_conflict')
        expected_counts = {'eligible_count': n, 'internal_gap_count': counts.get('-', 0),
                           'terminal_gap_excluded_count': len(site['excluded_terminal_row_indices'])}
        for field, expected in expected_counts.items():
            _cell(site[field], population_id=value['population_id'], method_id='msa_' + field + '_v1',
                  unit='characters', requirements=requirements, count=True)
            _require(site[field]['value'] is None or site[field]['value'] == expected, 'count_conflict')
        count_states = {site[field]['state'] for field in expected_counts}
        _require(len(count_states) == 1, 'site_count_states_conflict')
        entropy = site['literal_entropy_bits']
        _cell(entropy, population_id=value['population_id'], method_id=ENTROPY_METHOD,
              unit='bits', requirements=requirements)
        if entropy['value'] is not None:
            expected = -math.fsum((count / n) * math.log2(count / n) for count in counts.values()) if n else None
            _require(expected is not None and entropy['denominator'] == n
                     and _close(entropy['value'], expected), 'entropy_value_conflict')
        if site['eligible_count']['state'] == 'available':
            _require((entropy['value'] is not None) == (n > 0), 'entropy_availability_conflict')
            _require(entropy['denominator'] == n, 'entropy_denominator_conflict')
        score = site['native_score_recalculated']
        _cell(score, population_id=value['population_id'], method_id=ROUNDING_METHOD,
              unit='hundredths_of_bit', requirements=requirements)
        _require(score['denominator'] is None, 'score_denominator_invalid')
        if params['native_rounding'] is None:
            _require(score['value'] is None and score['state'] == 'not_measured', 'rounding_not_requested_conflict')
        if score['value'] is not None:
            _require(entropy['value'] is not None and params['native_rounding'] == ROUNDING
                     and score['value'] == float(format(entropy['value'], '.2f')) * 100,
                     'rounded_score_conflict')
        residual = site['score_residual']
        _cell(residual, population_id=value['population_id'], method_id=RESIDUAL_METHOD,
              unit='hundredths_of_bit', requirements=requirements)
        _require(residual['denominator'] is None, 'residual_denominator_invalid')
        _strings(site['native_observation_ids'])
        _require(all(re.fullmatch(r'msa_frequency_table:[0-9a-f]{64}/rows/(?:0|[1-9][0-9]*)/score', token)
                     for token in site['native_observation_ids']), 'native_observation_identity_invalid')
        _require(residual['value'] is None or score['value'] is not None
                 and len(site['native_observation_ids']) == 1, 'residual_operands_missing')
        consensus = site['strict_majority_consensus']
        _require((consensus is not None) == (n > 0 and site['eligible_count']['state'] == 'available'),
                 'consensus_availability_conflict')
        if consensus is not None:
            fallback = 'N' if params['alphabet'] == 'dna' else 'X'
            expected = next((symbol for symbol, count in counts.items() if count > n / 2), fallback)
            _require(n > 0 and consensus == expected, 'consensus_conflict')
    _require(len(columns) == len(set(columns)), 'duplicate_column')
    return deepcopy(value)


def validate_msa_reference_components(value: dict) -> dict:
    """Validate saved per-column categories and staged/original coordinate joins."""
    _shape(value, {'status', 'analysis_id', 'population_id', 'alignment_id', 'reference',
                  'method_parameters', 'differences', 'counts', 'requirements', 'diagnostics'},
           'reference_components_shape_invalid')
    requirements = _metadata(value)
    _validate_reference(value['reference'])
    _require(value['reference']['alignment_id'] == value['alignment_id'], 'reference_alignment_conflict')
    params = value['method_parameters']
    _shape(params, {'alphabet', 'case_policy'}, 'reference_parameters_invalid')
    _require(params['alphabet'] in ('dna', 'protein') and params['case_policy'] in ('preserve', 'uppercase'),
             'reference_parameters_invalid')
    _require(type(value['differences']) is list and type(value['counts']) is list, 'reference_rows_invalid')
    seen, tally, repeated_positions = set(), Counter(), {}
    canonical = set('ACGT' if params['alphabet'] == 'dna' else 'ACDEFGHIKLMNPQRSTVWY')
    for row in value['differences']:
        _shape(row, {'row_index', 'column_0based', 'member_character', 'reference_character', 'category',
            'member_ungapped_position_0based', 'reference_ungapped_position_0based',
            'member_original_correspondence', 'reference_original_correspondence'}, 'difference_shape_invalid')
        _index(row['row_index'])
        _index(row['column_0based'])
        key = row['row_index'], row['column_0based']
        _require(key not in seen, 'duplicate_difference')
        seen.add(key)
        a, b = row['member_character'], row['reference_character']
        _require(type(a) is str and len(a) == 1 and type(b) is str and len(b) == 1,
                 'difference_character_invalid')
        if params['case_policy'] == 'uppercase':
            _require(a == a.upper() and b == b.upper(), 'difference_case_conflict')
        expected_category = ('both_gap' if a == b == '-' else 'insertion_relative_to_reference' if b == '-'
            else 'deletion_relative_to_reference' if a == '-' else
            ('identical_canonical' if a == b else 'substitution') if a in canonical and b in canonical
            else 'ambiguous_or_other')
        _require(row['category'] == expected_category, 'difference_category_conflict')
        tally[row['row_index'], row['category']] += 1
        for operand, char, index in (('member', a, row['row_index']),
                                      ('reference', b, value['reference']['row_index'])):
            position = row[operand + '_ungapped_position_0based']
            shared.integer(position, nullable=True)
            _require((position is None) == (char == '-'), 'gap_staged_coordinate_conflict')
            mapping = row[operand + '_original_correspondence']
            position_key = index, row['column_0based']
            repeated_value = char, position, mapping
            _require(position_key not in repeated_positions or repeated_positions[position_key] == repeated_value,
                     'repeated_coordinate_conflict')
            repeated_positions[position_key] = repeated_value
            if mapping is not None:
                _validate_correspondence(mapping)
                _require(mapping['alignment_id'] == value['alignment_id'] and mapping['row_index'] == index
                         and mapping['column_0based'] == row['column_0based'], 'correspondence_identity_conflict')
                _require(mapping['staged_ungapped_position_0based'] in (None, position), 'staged_coordinate_conflict')
                _require(char != '-' or mapping['original_interval_0based_half_open'] is None,
                         'gap_original_coordinate_conflict')
                if operand == 'reference' and value['reference']['original_member'] is not None:
                    _require(mapping['original_member'] in (None, value['reference']['original_member']),
                             'reference_original_member_conflict')
    counts_seen = set()
    for row in value['counts']:
        _shape(row, {'row_index', 'category', 'count'}, 'reference_count_shape_invalid')
        _index(row['row_index'])
        _require(row['category'] in CATEGORIES, 'category_invalid')
        key = row['row_index'], row['category']
        _require(key not in counts_seen, 'duplicate_reference_count')
        counts_seen.add(key)
        _cell(row['count'], population_id=value['population_id'], method_id=REFERENCE_METHOD,
              unit='columns', requirements=requirements, count=True)
        _require(row['count']['value'] is None or row['count']['value'] == tally[key], 'reference_count_conflict')
    rows = {key[0] for key in counts_seen} | {key[0] for key in seen}
    _require(counts_seen == {(index, category) for index in rows for category in CATEGORIES},
             'reference_category_population_incomplete')
    return deepcopy(value)


__all__ = ['validate_msa_entropy_components', 'validate_msa_reference_components']
