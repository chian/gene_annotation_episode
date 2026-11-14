"""Numerical correspondence sheets for supplied ``sequence_ops.align_pair`` results.

Reading a native result and calculating from its saved sheet are separate pure
operations. Neither operation imports Biopython, executes an alignment, chooses
a resource, assigns annotation credit, or estimates functional confidence.
"""
from __future__ import annotations
from copy import deepcopy
import json
import math
import re
from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.alignment_correspondence import BASE_COUNT_NAMES, count_literal_alignment_columns, populate_correspondence_sheet, calculate_correspondence_components
SHEET_SCHEMA = 'biopython_pairwise_sheet_v1'
_COUNT_FIELDS = ('alignment_columns', 'paired_positions', 'identical_positions', 'substituted_positions', 'query_gap_columns', 'reference_gap_columns', 'query_aligned_positions', 'reference_aligned_positions')
_REPORTED_FIELDS = ('paired_positions', 'identical_positions', 'identity_fraction', 'query_coverage', 'reference_coverage')

def _require_json(value, code):
    """Reject nonfinite/non-JSON inputs without dropping or rewriting native data."""

    def check(item):
        if type(item) is dict:
            if any((type(key) is not str for key in item)):
                raise TypeError
            for child in item.values():
                check(child)
        elif type(item) is list:
            for child in item:
                check(child)
        elif item is not None and type(item) not in (bool, int, float, str):
            raise TypeError
    try:
        check(value)
        json.dumps(value, allow_nan=False)
    except (TypeError, ValueError, RecursionError) as error:
        raise ValueError(code) from error

def _number(value, field, issues, *, integer=False, minimum=None, maximum=None, required=False):
    if value is None:
        if required:
            issues.append({'code': 'measurement_missing', 'field': field})
        return None
    if type(value) not in ((int,) if integer else (int, float)) or (minimum is not None and value < minimum) or (maximum is not None and value > maximum):
        issues.append({'code': 'measurement_invalid', 'field': field})
        return None
    return value

def _count_columns(query, reference):
    return count_literal_alignment_columns(query, reference)

def _traceback(native, issues):
    query, reference = (native.get('aligned_query'), native.get('aligned_reference'))
    if query is None and reference is None:
        issues.append({'code': 'traceback_missing'})
        return ({'status': 'unavailable', 'query': None, 'reference': None}, None)
    if type(query) is not str or type(reference) is not str or (not query) or (len(query) != len(reference)) or (re.fullmatch('[A-Za-z*\\-]+', query) is None) or (re.fullmatch('[A-Za-z*\\-]+', reference) is None):
        issues.append({'code': 'traceback_strings_invalid'})
        return ({'status': 'invalid', 'query': None, 'reference': None}, None)
    query, reference = (query.upper(), reference.upper())
    if any((a == b == '-' for a, b in zip(query, reference))):
        issues.append({'code': 'double_gap_alignment_column'})
        return ({'status': 'invalid', 'query': query, 'reference': reference}, None)
    return ({'status': 'valid', 'query': query, 'reference': reference}, _count_columns(query, reference))

def _empty_geometry():
    return {'available': False, 'coordinate_system': 'zero_based_half_open', 'coordinates': None, 'query_interval': None, 'reference_interval': None, 'operand_bounds_checked': {'query': False, 'reference': False}}

def _geometry(native, traceback, counts, lengths, mode, issues):
    """Check the entire path, including placement of gaps, before mapping positions."""
    empty = _empty_geometry()
    coordinates = native.get('coordinates')
    if coordinates is None:
        issues.append({'code': 'coordinate_path_missing'})
        return (empty, [])
    if type(coordinates) is not list or len(coordinates) != 2 or any((type(axis) is not list for axis in coordinates)) or (len(coordinates[0]) < 2) or (len(coordinates[0]) != len(coordinates[1])) or any((type(p) is not int or p < 0 for axis in coordinates for p in axis)):
        issues.append({'code': 'coordinate_path_invalid'})
        return (empty, [])
    deltas = [(coordinates[0][i + 1] - coordinates[0][i], coordinates[1][i + 1] - coordinates[1][i]) for i in range(len(coordinates[0]) - 1)]
    if any((dq < 0 or dr < 0 or dq == dr == 0 or (dq and dr and (dq != dr)) for dq, dr in deltas)):
        issues.append({'code': 'coordinate_step_invalid'})
        return (empty, [])
    if sum((max(dq, dr) for dq, dr in deltas)) != counts['alignment_columns']:
        issues.append({'code': 'coordinate_traceback_length_conflict'})
        return (empty, [])
    invalid = False
    intervals = {}
    for index, axis in enumerate(('query', 'reference')):
        start, end = (coordinates[index][0], coordinates[index][-1])
        interval = native.get(axis + '_interval')
        consumed = counts[axis + '_aligned_positions']
        if consumed == 0 and interval is None:
            intervals[axis] = None
        elif type(interval) is not list or len(interval) != 2 or any((type(p) is not int or p < 0 for p in interval)) or (interval[0] >= interval[1]):
            issues.append({'code': 'alignment_interval_invalid', 'operand': axis})
            invalid = True
        elif interval != [start, end]:
            issues.append({'code': 'coordinate_interval_conflict', 'operand': axis})
            invalid = True
        else:
            intervals[axis] = interval
        if end - start != consumed:
            issues.append({'code': 'coordinate_traceback_span_conflict', 'operand': axis})
            invalid = True
        if lengths[axis] is not None and end > lengths[axis]:
            issues.append({'code': 'coordinates_outside_operand', 'operand': axis})
            invalid = True
        if mode == 'global' and (start != 0 or (lengths[axis] is not None and end != lengths[axis])):
            issues.append({'code': 'global_alignment_operand_span_conflict', 'operand': axis})
            invalid = True
    if invalid:
        return (empty, [])
    rows, column = ([], 0)
    for segment, (dq, dr) in enumerate(deltas):
        for offset in range(max(dq, dr)):
            a, b = (traceback['query'][column], traceback['reference'][column])
            if (a != '-') != bool(dq) or (b != '-') != bool(dr):
                issues.append({'code': 'coordinate_traceback_gap_conflict', 'column': column})
                return (empty, [])
            rows.append({'column': column, 'query_position': coordinates[0][segment] + offset if dq else None, 'reference_position': coordinates[1][segment] + offset if dr else None, 'query_symbol': a if dq else None, 'reference_symbol': b if dr else None, 'relationship': 'query_gap' if not dq else 'reference_gap' if not dr else 'identical' if a == b else 'substituted'})
            column += 1
    return ({'available': True, 'coordinate_system': 'zero_based_half_open', 'coordinates': deepcopy(coordinates), 'query_interval': deepcopy(intervals['query']), 'reference_interval': deepcopy(intervals['reference']), 'operand_bounds_checked': {axis: lengths[axis] is not None for axis in lengths}}, rows)

def _no_alignment_conflict(native):
    detail_fields = ('aligned_query', 'aligned_reference', 'coordinates', 'query_interval', 'reference_interval')
    return any((native.get(field) not in (None, '', []) for field in detail_fields)) or any((native.get(field) not in (None, 0) for field in _REPORTED_FIELDS))

def _common_sheet(*, counts, lengths, geometry, correspondence, alignment_state, molecule):
    """Adapt measured cells; never manufacture another producer's traceback."""
    if alignment_state == 'no_alignment':
        measurement = {'kind': 'explicit_no_alignment'}
    elif counts is None or all((value is None for value in counts.values())):
        measurement = {'kind': 'unavailable'}
    else:
        measurement = {'kind': 'validated_saved_counts', 'basis': 'traceback', 'counts': {name: counts[name] for name in BASE_COUNT_NAMES}}
    available = geometry['available']
    pairs = [{'query_start': row['query_position'], 'query_end': row['query_position'] + 1, 'reference_start': row['reference_position'], 'reference_end': row['reference_position'] + 1, 'identical': row['relationship'] == 'identical'} for row in correspondence if row['query_position'] is not None and row['reference_position'] is not None]
    unit = 'aa' if molecule == 'protein' else 'nt'
    return populate_correspondence_sheet(operands={'query': {'length': lengths['query'], 'unit': unit}, 'reference': {'length': lengths['reference'], 'unit': unit}, 'alignment_unit': unit}, rows=[{'source_key': '', 'measurement_input': measurement, 'paired_lengths': dict(lengths), 'span_inputs': {axis: {'interval': deepcopy(geometry[axis + '_interval']) if available else None, 'length': lengths[axis]} for axis in ('query', 'reference')}, 'geometry_available': available, 'pairs': pairs, 'symbol_widths': {'query': 1, 'reference': 1}, 'reported_alignment_identity_fallback': None}], population={'original_rows_complete': True, 'execution_state': 'unknown', 'producer_state': 'unknown', 'explicit_zero_result': alignment_state == 'no_alignment'}, selected_intervals={'query': None, 'reference': None})

def build_biopython_pairwise_sheet(native: dict, *, molecule: str) -> dict:
    """Extract finite native facts and validated correspondence without scoring.

    Strings supply column counts even if coordinates are invalid. Positional
    coverage requires the full path to agree with strings, intervals, available
    operand lengths, and local/global mode. The supplied result does not contain
    original unaligned sequence symbols, so those cannot be reconstructed.

    Nonfinite/non-JSON inputs fail at the boundary. Finite malformed individual
    measurements are retained verbatim in ``native_result`` and have issues and
    null validated components. ``aligned=False`` is an explicit zero result;
    missing traceback for ``aligned=True`` supplies no zero measurements.

    ``biopython_pairwise_native_v2`` deliberately omits derived convenience
    measurements. Markerless legacy results retain their original required
    reported-field checks; any supplied reported values still retain conflicts.
    Both formats populate this same sheet and use the same calculator.
    """
    if type(native) is not dict:
        raise ValueError('biopython_pairwise_native_object_required')
    _require_json(native, 'finite_json_biopython_pairwise_native_required')
    if type(molecule) is not str or molecule not in {'protein', 'dna', 'rna'}:
        raise ValueError('biopython_pairwise_molecule_required')
    if type(native.get('aligned')) is not bool:
        raise ValueError('biopython_pairwise_aligned_boolean_required')
    if type(native.get('mode')) is not str or native['mode'] not in {'local', 'global'}:
        raise ValueError('biopython_pairwise_mode_required')
    native_format = native.get('native_format')
    if native_format is not None and native_format != 'biopython_pairwise_native_v2':
        raise ValueError('biopython_pairwise_native_format_unknown')
    issues = []
    aligned = native['aligned']
    lengths = {axis: _number(native.get(axis + '_length'), axis + '_length', issues, integer=True, minimum=0, required=True) for axis in ('query', 'reference')}
    matrix = native.get('matrix')
    if type(matrix) is not str or not matrix:
        issues.append({'code': 'native_matrix_missing_or_invalid'})
        matrix = None
    parameters = {'matrix': matrix, **{field: _number(native.get(field), field, issues, required=aligned) for field in ('gap_open', 'gap_extend')}}
    score = _number(native.get('native_score'), 'native_score', issues, required=aligned)
    reported = {field: _number(native.get(field), field, issues, integer=field.endswith('positions'), minimum=0, maximum=None if field.endswith('positions') else 1, required=aligned and native_format is None) for field in _REPORTED_FIELDS}
    counts = None
    geometry, correspondence = (_empty_geometry(), [])
    if aligned:
        traceback, counts = _traceback(native, issues)
        if counts is not None:
            geometry, correspondence = _geometry(native, traceback, counts, lengths, native['mode'], issues)
        alignment_state = 'alignment'
    elif _no_alignment_conflict(native):
        issues.append({'code': 'no_alignment_has_alignment_data'})
        traceback = {'status': 'conflicting', 'query': None, 'reference': None}
        alignment_state = 'conflicting'
    else:
        traceback = {'status': 'no_alignment', 'query': None, 'reference': None}
        counts = dict.fromkeys(_COUNT_FIELDS, 0)
        alignment_state = 'no_alignment'
    if counts is not None:
        for field in ('paired_positions', 'identical_positions'):
            if reported[field] is not None and reported[field] != counts[field]:
                issues.append({'code': 'reported_count_traceback_conflict', 'field': field, 'reported': reported[field], 'measured': counts[field]})
        common = calculate_correspondence_components(_common_sheet(counts=counts, lengths=lengths, geometry=geometry, correspondence=correspondence, alignment_state=alignment_state, molecule=molecule))['rows'][0]
        fractions = {'identity_fraction': common['fractions']['paired_identity']}
        if geometry['available'] or alignment_state == 'no_alignment':
            fractions.update({axis + '_coverage': common['fractions'][axis + '_aligned_coverage'] for axis in ('query', 'reference')})
        for field, measured in fractions.items():
            if reported[field] is not None and measured is not None and (not math.isclose(reported[field], measured, rel_tol=1e-12, abs_tol=1e-15)):
                issues.append({'code': 'reported_fraction_traceback_conflict', 'field': field, 'reported': reported[field], 'measured': measured})
    if reported['identical_positions'] is not None and reported['paired_positions'] is not None:
        if reported['identical_positions'] > reported['paired_positions']:
            issues.append({'code': 'reported_identity_exceeds_paired_positions'})
    status = 'partial' if issues else 'no_alignment' if alignment_state == 'no_alignment' else 'complete'
    if aligned and counts is None:
        status = 'alignment_data_unavailable'
    return {'schema': SHEET_SCHEMA, 'status': status, 'native_result': deepcopy(native), 'molecule': molecule, 'mode': native['mode'], 'aligned': aligned, 'alignment_state': alignment_state, 'native_parameters': parameters, 'native_score': score, 'lengths': lengths, 'reported_measurements': reported, 'traceback': traceback, 'measured_column_counts': counts if counts is not None else dict.fromkeys(_COUNT_FIELDS), 'geometry': geometry, 'residue_correspondence': correspondence, 'issues': issues, 'symbol_interpretation': {'reader_normalization': 'uppercase_of_native_traceback_symbols', 'native_nucleotide_normalization': 'U_to_T_before_alignment' if molecule != 'protein' else None, 'identity': 'literal_normalized_symbol_equality_without_ambiguity_resolution'}, 'limitations': ['only_the_supplied_native_alignment_is_available_not_all_optimal_alternatives', 'original_unaligned_sequence_symbols_are_not_present_in_this_native_result', 'native_score_is_not_database_significance_or_function_confidence']}
