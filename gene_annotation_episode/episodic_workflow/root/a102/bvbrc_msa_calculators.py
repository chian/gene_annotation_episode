"""Pure BV-BRC MSA calculations on supplied, validated saved documents.

Literal entropy uses every eligible uppercased symbol and excludes only terminal
dashes. It is separate from the shared canonical-only conservation calculation.
Reference comparisons are per aligned column, not normalized variant alleles.
No parser, file, network, native program or model is invoked by either function.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
import math
from typing import Literal

from . import phylogeny_calculation_contracts as shared
from .bvbrc_alignment_values import diagnostic, numeric_cell, requirement
from .bvbrc_msa_calculation_contracts import (
    CATEGORIES, ENTROPY_METHOD, REFERENCE_METHOD, RESIDUAL_METHOD, ROUNDING,
    ROUNDING_METHOD, _validate_correspondence, _validate_reference,
    validate_msa_entropy_components, validate_msa_reference_components,
)
from .bvbrc_msa_format_contracts import PROTEIN_SYMBOLS, _require, _text, validate_msa_frequency_table
from .phylogeny_calculators import ungapped_coordinate_map
from .phylogeny_format_contracts import validate_alignment_document


def _scope(*tokens):
    return 'bvbrc_msa/' + '/'.join(token.replace('%', '%25').replace('/', '%2F') for token in tokens)


def _inputs(alignment, analysis_id, population, alphabet):
    alignment = validate_alignment_document(alignment)
    _text(analysis_id)
    shared.alignment_population(population, alignment)
    _require(alphabet in ('dna', 'protein'), 'alphabet_invalid')
    return alignment, deepcopy(population)


def _state(alignment, population):
    if alignment['completeness'] == population['completeness'] == 'complete':
        return 'available'
    return 'truncated' if 'truncated' in (alignment['completeness'], population['completeness']) else 'missing'


def _qualification(code, *, path='', refs=()):
    return diagnostic('bvbrc_msa_' + code, path=path, evidence_refs=refs)


def _need(analysis_id, population_id, reason, *, role, source_ref, row=None):
    tokens = (analysis_id, population_id) + (() if row is None else ('row', str(row)))
    return requirement(_scope(*tokens, reason), kind='output_bytes' if reason == 'incomplete_alignment'
        else 'scientific_metadata', role=role, source_refs=(source_ref,), reason_code='bvbrc_msa_' + reason)


def _cell(value, *, population, method, unit, state='available', denominator=None, requirements=(), evidence=None):
    return numeric_cell(value, state='available' if value is not None else state,
        unit=unit, origin='calculated', population_id=population['population_id'], method_id=method,
        denominator=denominator, evidence=population['evidence'] if evidence is None else evidence,
        requirement_ids=requirements)


def msa_native_entropy(alignment: dict, *, analysis_id: str, population: dict,
    alphabet: Literal['dna', 'protein'], case_policy: Literal['uppercase'], terminal_gap: Literal['-'],
    observed_table: dict | None,
    native_rounding: Literal['binary64_fixed_2_ties_to_even'] | None) -> dict:
    """Calculate literal H=-sum(p*log2(p)) over each eligible site population.

    Each full row's first/last non-dash precedes column selection. Internal '-'
    and ambiguous/stop symbols are literal states. Zero eligible symbols gives
    null entropy, not zero. Rounding, when selected, is the declared binary64
    float(format(H, '.2f'))*100 implementation, not a claim about deployed Perl.

    score_residual is observed Score minus this selected population's score.
    It does not establish equal native/calculated membership or a producer error.
    Changed native counts and subsets are qualified. Duplicate native positions
    keep all score identities and cannot supply a unique residual operand.
    """
    alignment, population = _inputs(alignment, analysis_id, population, alphabet)
    _require(case_policy == 'uppercase' and terminal_gap == '-', 'entropy_parameters_invalid')
    _require(native_rounding in (ROUNDING, None), 'native_rounding_invalid')
    if observed_table is not None:
        observed_table = validate_msa_frequency_table(observed_table)
        _require(observed_table['alphabet'] == alphabet, 'native_table_alphabet_conflict')
    status = _state(alignment, population)
    complete = status == 'available'
    requirements, diagnostics = [], []
    refs = (alignment['artifact']['raw_artifact_ref'],)
    if not complete:
        requirements.append(_need(analysis_id, population['population_id'], 'incomplete_alignment',
            role='final_alignment', source_ref=alignment['artifact']['source_ref']))
        diagnostics.append(_qualification('incomplete_alignment', refs=refs))
    req_ids = [row['requirement_id'] for row in requirements]
    rows = {row['row_index']: row['sequence'].upper() for row in alignment['rows']}
    _require(all(len(rows[row['row_index']]) == len(row['sequence']) for row in alignment['rows']),
             'case_policy_changes_coordinates')
    bounds = {index: (len(rows[index]) - len(rows[index].lstrip('-')), len(rows[index].rstrip('-')))
              for index in population['row_indices']}
    full_row_bounds_known = {index: alignment['completeness'] == 'complete' or (
        alignment['declared_column_count'] is not None and len(rows[index]) == alignment['declared_column_count'])
        for index in population['row_indices']}
    observed_by_column = defaultdict(list)
    if observed_table is not None:
        if set(population['row_indices']) != set(rows):
            diagnostics.append(_qualification('native_comparison_selected_row_subset', refs=refs))
        if observed_table['completeness'] != 'complete':
            diagnostics.append(_qualification('native_table_partial', refs=(observed_table['artifact']['raw_artifact_ref'],)))
        for row in observed_table['rows']:
            position = row['alignment_position']
            if position['state'] != 'available':
                diagnostics.append(_qualification('native_coordinate_unavailable',
                    path='/observed_table/rows/' + str(row['row_index']),
                    refs=(observed_table['artifact']['raw_artifact_ref'],)))
                continue
            column = position['value'] - 1
            observed_by_column[column].append(row)
            if alignment['observed_column_count'] is not None and column >= alignment['observed_column_count']:
                diagnostics.append(_qualification('native_coordinate_outside_alignment',
                    path='/observed_table/rows/' + str(row['row_index']),
                    refs=(observed_table['artifact']['raw_artifact_ref'],)))
    sites = []
    for column in population['columns_0based']:
        included, excluded = [], []
        for index in population['row_indices']:
            start, end = bounds[index]
            if column >= len(rows[index]):
                continue
            if start <= column < end:
                included.append(index)
            elif column < start or full_row_bounds_known[index]:
                # An incomplete row's trailing dashes might precede an unread
                # residue. Only its observed leading run is certainly terminal;
                # the retained alignment still contains unclassified cells.
                excluded.append(index)
        counts = Counter(rows[index][column] for index in included)
        n = len(included)
        entropy = -math.fsum((count / n) * math.log2(count / n) for count in counts.values()) if n and complete else None
        if entropy == 0:
            entropy = 0.0
        score = float(format(entropy, '.2f')) * 100 if entropy is not None and native_rounding is not None else None
        consensus = next((symbol for symbol, count in counts.items() if count > n / 2),
                         'N' if alphabet == 'dna' else 'X') if n and complete else None
        path = '/sites/' + str(len(sites))
        if n == 0 and complete:
            diagnostics.append(_qualification('empty_site_population', path=path, refs=refs))
        native_rows = observed_by_column.get(column, [])
        observation_ids = [observed_table['table_id'] + '/rows/' + str(row['row_index']) + '/score'
                           for row in native_rows]
        residual, residual_state = None, 'not_measured' if observed_table is None else 'missing'
        if len(native_rows) > 1:
            residual_state = 'incompatible'
            diagnostics.append(_qualification('duplicate_native_coordinate', path=path,
                refs=(observed_table['artifact']['raw_artifact_ref'],)))
        elif len(native_rows) == 1:
            native_row = native_rows[0]
            native_score = native_row['score']
            if score is not None and native_score['state'] == 'available':
                residual = native_score['value'] - score
                if residual != 0:
                    diagnostics.append(_qualification('native_vs_recalculated_conflict', path=path + '/score_residual',
                        refs=(observed_table['artifact']['raw_artifact_ref'],)))
            else:
                residual_state = native_score['state'] if native_score['state'] != 'available' else (
                    'not_measured' if native_rounding is None or n == 0 and complete else status)
            # Comparisons are descriptive, never a gate on independent entropy.
            conflicts = []
            if complete and native_row['n_sequences']['state'] == 'available' and native_row['n_sequences']['value'] != n:
                conflicts.append('n_sequences')
            if complete and alphabet == 'dna':
                for base, count in native_row['dna_counts'].items():
                    if count['state'] == 'available' and count['value'] != counts['-' if base == 'Deletion' else base]:
                        conflicts.append('dna_counts/' + base)
            elif complete:
                for entry in native_row['protein_detail']:
                    if entry['symbol'] is not None and entry['count']['state'] == 'available' and entry['count']['value'] != counts[entry['symbol']]:
                        conflicts.append('protein_detail')
            native_consensus = (native_row['consensus_token'] if alphabet == 'dna'
                                else PROTEIN_SYMBOLS.get(native_row['consensus_token']))
            if consensus is not None and native_consensus is not None and native_consensus != consensus:
                conflicts.append('consensus_token')
            for field in dict.fromkeys(conflicts):
                diagnostics.append(_qualification('native_vs_recalculated_conflict', path=path + '/' + field,
                    refs=(observed_table['artifact']['raw_artifact_ref'],)))
        elif observed_table is not None:
            diagnostics.append(_qualification('native_coordinate_unavailable', path=path,
                refs=(observed_table['artifact']['raw_artifact_ref'],)))
        site = {'column_0based': column, 'included_row_indices': included,
            'excluded_terminal_row_indices': excluded,
            'symbol_counts': [{'symbol': symbol, 'count': count} for symbol, count in sorted(counts.items())],
            'strict_majority_consensus': consensus, 'native_observation_ids': observation_ids}
        for field, count in (('eligible_count', n), ('internal_gap_count', counts['-']),
                              ('terminal_gap_excluded_count', len(excluded))):
            site[field] = _cell(count if complete else None, population=population, method='msa_' + field + '_v1',
                                unit='characters', state=status, requirements=() if complete else req_ids)
        site['literal_entropy_bits'] = _cell(entropy, population=population, method=ENTROPY_METHOD,
            unit='bits', state='not_measured' if complete else status,
            denominator=n if complete else None, requirements=() if complete else req_ids)
        site['native_score_recalculated'] = _cell(score, population=population, method=ROUNDING_METHOD,
            unit='hundredths_of_bit', state='not_measured' if native_rounding is None or complete else status,
            requirements=() if complete or native_rounding is None else req_ids)
        site['score_residual'] = _cell(residual, population=population, method=RESIDUAL_METHOD,
            unit='hundredths_of_bit', state=residual_state,
            requirements=req_ids if not complete and observed_table is not None else ())
        sites.append(site)
    return validate_msa_entropy_components({'status': 'partial' if diagnostics or requirements else 'ok',
        'analysis_id': analysis_id, 'population_id': population['population_id'], 'alignment_id': alignment['alignment_id'],
        'method_parameters': {'alphabet': alphabet, 'case_policy': case_policy, 'terminal_gap': terminal_gap,
                              'native_rounding': native_rounding},
        'sites': sites, 'requirements': requirements, 'diagnostics': diagnostics})


def msa_reference_differences(alignment: dict, *, analysis_id: str, population: dict,
    reference: dict, member_row_indices: tuple[int, ...], alphabet: Literal['dna', 'protein'],
    case_policy: Literal['preserve', 'uppercase'], original_correspondences: tuple[dict, ...]) -> dict:
    """Classify each requested member/reference column and retain coordinate maps.

    Staged offsets count all non-dash symbols from the full row, before selecting
    columns. Supplied original maps are validated independently. Missing original
    maps qualify the result without suppressing known staged differences/counts.
    The reference may be outside the selected member rows but must be an actual
    row of this alignment; no first-row or member-label identity is inferred.
    """
    alignment, population = _inputs(alignment, analysis_id, population, alphabet)
    _require(case_policy in ('preserve', 'uppercase'), 'case_policy_invalid')
    _validate_reference(reference)
    reference = deepcopy(reference)
    _require(reference['alignment_id'] == alignment['alignment_id']
             and reference['row_index'] < len(alignment['rows']), 'reference_row_conflict')
    shared.unique_indices(member_row_indices, stored=False)
    _require(set(member_row_indices) <= set(population['row_indices']), 'member_row_outside_population')
    shared.sequence(original_correspondences)
    maps = ungapped_coordinate_map(alignment, row_indices=tuple(range(len(alignment['rows']))))
    offsets = {(row['row_index'], row['column_0based']): row['ungapped_position_0based'] for row in maps}
    correspondences, identities = {}, {}
    for record in original_correspondences:
        _validate_correspondence(record)
        key = record['row_index'], record['column_0based']
        _require(record['alignment_id'] == alignment['alignment_id'] and key in offsets,
                 'correspondence_identity_conflict')
        _require(key not in correspondences, 'duplicate_correspondence')
        _require(record['staged_ungapped_position_0based'] in (None, offsets[key]), 'staged_coordinate_conflict')
        _require(offsets[key] is not None or record['original_interval_0based_half_open'] is None,
                 'gap_original_coordinate_conflict')
        identity = record['original_member']
        if identity is not None:
            _require(record['row_index'] not in identities or identities[record['row_index']] == identity,
                     'original_member_conflict')
            identities[record['row_index']] = identity
        if record['row_index'] == reference['row_index'] and reference['original_member'] is not None:
            _require(identity is None or identity == reference['original_member'], 'reference_original_member_conflict')
        correspondences[key] = deepcopy(record)
    sequences = {row['row_index']: row['sequence'].upper() if case_policy == 'uppercase' else row['sequence']
                 for row in alignment['rows']}
    _require(all(len(sequences[row['row_index']]) == len(row['sequence']) for row in alignment['rows']),
             'case_policy_changes_coordinates')
    status = _state(alignment, population)
    complete = status == 'available'
    requirements, diagnostics, differences, counts = [], [], [], []
    refs = (alignment['artifact']['raw_artifact_ref'],)
    if not complete:
        requirements.append(_need(analysis_id, population['population_id'], 'incomplete_alignment',
            role='final_alignment', source_ref=alignment['artifact']['source_ref']))
        diagnostics.append(_qualification('incomplete_alignment', refs=refs))
    if reference['identity_state'] != 'resolved':
        requirements.append(_need(analysis_id, population['population_id'], 'requested_reference_unresolved',
            role='reference_binding', source_ref=alignment['artifact']['source_ref']))
        diagnostics.append(_qualification('requested_reference_unresolved', path='/reference', refs=refs))
    incomplete_reqs = [row['requirement_id'] for row in requirements
                       if row['reason_code'] == 'bvbrc_msa_incomplete_alignment']
    reference_row = reference['row_index']
    canonical = set('ACGT' if alphabet == 'dna' else 'ACDEFGHIKLMNPQRSTVWY')
    missing_original_rows = set()
    for index in member_row_indices:
        tally = Counter()
        for column in population['columns_0based']:
            if column >= len(sequences[index]) or column >= len(sequences[reference_row]):
                continue
            a, b = sequences[index][column], sequences[reference_row][column]
            category = ('both_gap' if a == b == '-' else 'insertion_relative_to_reference' if b == '-'
                else 'deletion_relative_to_reference' if a == '-' else
                ('identical_canonical' if a == b else 'substitution') if a in canonical and b in canonical
                else 'ambiguous_or_other')
            tally[category] += 1
            row = {'row_index': index, 'column_0based': column, 'member_character': a,
                'reference_character': b, 'category': category,
                'member_ungapped_position_0based': offsets[index, column],
                'reference_ungapped_position_0based': offsets[reference_row, column],
                'member_original_correspondence': correspondences.get((index, column)),
                'reference_original_correspondence': correspondences.get((reference_row, column))}
            for operand_index, char in ((index, a), (reference_row, b)):
                mapping = correspondences.get((operand_index, column))
                if char != '-' and (mapping is None or mapping['original_member'] is None
                                     or mapping['original_interval_0based_half_open'] is None):
                    missing_original_rows.add(operand_index)
            differences.append(row)
        for category in CATEGORIES:
            counts.append({'row_index': index, 'category': category,
                'count': _cell(tally[category] if complete else None, population=population, method=REFERENCE_METHOD,
                              unit='columns', state=status, requirements=incomplete_reqs if not complete else ())})
    for index in sorted(missing_original_rows):
        requirements.append(_need(analysis_id, population['population_id'], 'original_residue_map_required',
            role='original_residue_map', source_ref=alignment['artifact']['source_ref'], row=index))
        diagnostics.append(_qualification('original_residue_map_required', path='/rows/' + str(index), refs=refs))
    return validate_msa_reference_components({'status': 'partial' if diagnostics or requirements else 'ok',
        'analysis_id': analysis_id, 'population_id': population['population_id'], 'alignment_id': alignment['alignment_id'],
        'reference': reference, 'method_parameters': {'alphabet': alphabet, 'case_policy': case_policy},
        'differences': differences, 'counts': counts, 'requirements': requirements, 'diagnostics': diagnostics})


__all__ = ['msa_native_entropy', 'msa_reference_differences']
