"""Deterministic A101 convention-015 native correspondence subscoring sheet.

This is the native channel of the sheet: it measures correspondence on supplied
material, independently of a functional hypothesis. Characterization and feature
grounding are separate inputs, never inferred from a hit's name or magnitude.
No model call, native execution, credit update or source read occurs here.
"""
from __future__ import annotations

import math
from copy import deepcopy
from types import MappingProxyType


VERSION = 'a101_native_correspondence_015_v1'
SCALES = MappingProxyType({'blast': 0.025, 'hmmer': 0.020})


class A101ScoringUnavailable(ValueError):
    def __init__(self, code, **detail):
        self.code, self.detail = code, detail
        super().__init__(code)


def _require(condition, code, **detail):
    if not condition:
        raise A101ScoringUnavailable(code, **detail)


def intervals(values, *, length, merge_adjacent=True):
    """Exact half-open union; adjacent display blocks are not requirements."""
    _require(type(length) is int and length > 0, 'a101_positive_length_required')
    _require(isinstance(values, (list,tuple)), 'a101_invalid_interval')
    for pair in values:
        _require(isinstance(pair, (list,tuple)) and len(pair)==2
            and all(type(x) is int for x in pair) and 0<=pair[0]<pair[1]<=length,
            'a101_invalid_interval')
    result = []
    for pair in sorted(values):
        _require(isinstance(pair, (list, tuple)) and len(pair) == 2
            and all(type(x) is int for x in pair) and 0 <= pair[0] < pair[1] <= length,
            'a101_invalid_interval')
        if result and (pair[0] <= result[-1][1] if merge_adjacent else pair[0] < result[-1][1]):
            result[-1][1] = max(result[-1][1], pair[1])
        else:
            result.append(list(pair))
    return result


def _count(values):
    return sum(end-start for start, end in values)


def _fraction(value, field):
    _require(type(value) in (int, float) and math.isfinite(value)
        and 0 <= value <= 1, 'a101_invalid_fraction', field=field)
    return value


def comparison_weight(row):
    family = row['algorithm']
    _require(family in SCALES, 'a101_unsupported_score_profile', profile=family)
    bits = row.get('bits')
    _require(type(bits) in (int, float) and math.isfinite(bits),
        'a101_native_bits_unavailable')
    paired, denominator = row.get('reference_paired_count'), row.get('reference_length')
    _require(type(denominator) is int and denominator > 0 and type(paired) is int
        and 0 <= paired <= denominator, 'a101_reference_denominator_unavailable')
    native = -math.expm1(-SCALES[family]*max(bits, 0))
    coverage = paired/denominator
    identity_factor = 1.0
    if family == 'blast':
        identity_factor = 0.5+0.5*_fraction(row.get('alignment_identity'), 'alignment_identity')
    return {'native_strength': native, 'reference_paired_fraction': coverage,
        'identity_factor': identity_factor, 'weight': native*coverage*identity_factor,
        'inverse_bit_scale': SCALES[family], 'unit': 'dimensionless_index'}


def compile_native_sheet(rows, *, supplied_length, regions=None, profile=None):
    """Max over overlapping comparisons, mean over tools, geometric regions.

    The population is all supplied, validated native comparisons. This subscore
    does not assign their references to a biological function. A repeated result
    or another reference on the same residues cannot add an independent vote.
    Included algorithms are selected from producer identities, never by score.
    """
    scope = intervals(regions if regions is not None else [[0, supplied_length]],
                      length=supplied_length, merge_adjacent=False)
    _require(bool(scope), 'a101_required_scope_empty')
    families = sorted(set(profile) if profile is not None else {r['algorithm'] for r in rows})
    _require(set(families) <= set(SCALES), 'a101_unsupported_score_profile')
    calculated = []
    for source in rows:
        row = deepcopy(source)
        _require(row['algorithm'] in families, 'a101_algorithm_outside_profile')
        row['target_intervals'] = intervals(row['target_intervals'], length=supplied_length)
        _require(bool(row['target_intervals']), 'a101_paired_target_positions_unavailable')
        row.update(comparison_weight(row))
        calculated.append(row)
    region_results = []
    for start, end in scope:
        channels = {}
        for family in families:
            candidates = [r for r in calculated if r['algorithm'] == family]
            boundaries = sorted({start, end, *(max(start, min(end, x))
                for row in candidates for pair in row['target_intervals'] for x in pair)})
            mass = 0.0
            for left, right in zip(boundaries, boundaries[1:]):
                weight = max((row['weight'] for row in candidates
                    if any(a <= left and right <= b for a,b in row['target_intervals'])), default=0.0)
                mass += (right-left)*weight
            channels[family] = mass/(end-start)
        value = math.fsum(channels.values())/len(families) if families else 0.0
        region_results.append({'start': start, 'end': end, 'length': end-start,
            'algorithm_components': channels, 'value': value})
    components = [r['value'] for r in region_results]
    value = math.exp(math.fsum(math.log(x) for x in components)/len(components)) if all(components) else 0.0
    return {'version': VERSION, 'axis': 'A101', 'component': 'native_sequence_correspondence',
        'value': value, 'status': 'derived', 'unit': 'dimensionless_index',
        'supplied_length': supplied_length, 'scope': scope, 'profile': families,
        'comparisons': calculated, 'regions': region_results,
        'function_specific_index': {'value': None, 'status': 'not_assessed',
            'reason': 'reference_function_and_feature_grounding_are_separate_inputs'},
        'full_target_index': {'value': None, 'status': 'not_assessed',
            'reason': 'supplied_scope_does_not_establish_biological_completeness'},
        'interpretation': 'native_correspondence_index_not_function_probability',
        'aggregation': 'max_at_each_target_position_mean_of_included_algorithms_geometric_required_regions',
        'coefficients': dict(SCALES)}


def hmmer_comparisons(grading):
    """R3 native fields/maps, with phmmer's query-profile orientation intact."""
    sheet, scores = grading.get('sheet'), grading.get('scores')
    _require(isinstance(sheet, dict) and sheet.get('schema') == 'hmmer_search_sheet_v1'
        and isinstance(scores, dict) and scores.get('schema') == 'hmmer_search_scores_v1',
        'a101_hmmer_grading_unavailable')
    program = sheet['operation']['program']
    _require(program in {'phmmer', 'hmmsearch', 'hmmscan'},
        'a101_original_query_mapping_unavailable', program=program)
    result = []
    for row in sheet['domains']:
        matches = [d for d in scores['domains'] if d['record_key'] == row['record_key']]
        _require(len(matches) == 1, 'a101_hmmer_domain_join_ambiguous')
        score = matches[0]
        alignment, bounds = row.get('alignment', {}), score.get('intervals', {})
        model, sequence = alignment.get('model'), alignment.get('aseq')
        _require(isinstance(model, str) and isinstance(sequence, str) and len(model) == len(sequence),
            'a101_native_traceback_unavailable')
        _require(bounds.get('model') is not None and bounds.get('sequence') is not None,
            'a101_native_coordinates_unavailable')
        m, s = bounds['model'][0], bounds['sequence'][0]
        target, reference, symbols, reference_symbols = [], [], [], []
        for a,b in zip(model, sequence):
            ma, sa = a not in '.-~', b not in '.-~'
            if ma and sa:
                target.append(m if program == 'phmmer' else s)
                reference.append(s if program == 'phmmer' else m)
                symbols.append(a.upper() if program == 'phmmer' else b.upper())
                reference_symbols.append(b.upper() if program == 'phmmer' else a.upper())
            m += ma
            s += sa
        _require(m == bounds['model'][1] and s == bounds['sequence'][1]
            and len(target) == score.get('paired_positions'), 'a101_native_map_conflict')
        denominator = score.get('sequence_length' if program == 'phmmer' else 'model_length')
        result.append({'algorithm': 'hmmer', 'program': program,
            'native_record_key': row['record_key'], 'target_name': row.get('target_name'),
            'bits': score.get('native_domain_score_bits'),
            'native_evalue': score.get('native_independent_evalue'),
            'native_identity': score.get('sequence_identity_fraction'),
            'reference_paired_count': len(set(reference)), 'reference_length': denominator,
            'target_intervals': [[p,p+1] for p in target],
            'target_symbols': list(zip(target, symbols)),
            'residue_pairs': [[i,j,a,b] for i,j,a,b in zip(target,reference,symbols,reference_symbols,strict=True)],
            'native_scope': 'hmmer_domain_envelope',
            'orientation': 'query_profile_representing_supplied_sequence' if program == 'phmmer' else 'native_sequence'})
    return result


def route_native_grading(grading):
    """Hard-coded schema dispatch. Neither callers nor models name a route."""
    schema = (grading.get('sheet') or {}).get('schema')
    if schema == 'hmmer_search_sheet_v1':
        return hmmer_comparisons(grading)
    if schema and schema.startswith('blast_'):
        return blast_comparisons(grading)
    raise A101ScoringUnavailable('a101_unsupported_score_profile', schema=schema)


def blast_comparisons(grading):
    """R2 cells from already calculated protein BLAST HSP components."""
    sheet = grading['sheet']
    normalized = sheet.get('input', sheet.get('normalized_result', {}))
    program = normalized.get('search', {}).get('program')
    _require(program == 'blastp', 'a101_translated_or_nucleotide_map_not_bound', program=program)
    result = []
    if sheet['schema'] == 'blast_pairwise_sheet_v1':
        populations = [(0, sheet['hsps'], sheet['reference']['length'])]
    elif sheet['schema'] in {'blast_database_sheet_v1', 'blast_database_sheet_v2', 'blast_database_sheet_v3'}:
        populations = [(hit['hit_index'], [
            {'native': normalized['hits'][hit['hit_index']]['hsps'][address['hsp_index']],
             'components': component, 'hsp_index': address['hsp_index']}
            for address,component in zip(hit['hsp_source_map'], hit['hsp_components'], strict=True)],
            normalized['hits'][hit['hit_index']]['length']) for hit in sheet['hits']]
    else:
        raise A101ScoringUnavailable('a101_unsupported_score_profile', schema=sheet['schema'])
    for hit_index, hsps, reference_length in populations:
        for hsp in hsps:
            native, component = hsp['native'], hsp['components']
            q, r = native.get('qseq'), native.get('hseq', native.get('sseq'))
            _require(isinstance(q,str) and isinstance(r,str) and len(q) == len(r),
                'a101_native_traceback_unavailable')
            qi, ri = native.get('query_from', native.get('qstart')), native.get('hit_from', native.get('sstart'))
            _require(type(qi) is int and type(ri) is int, 'a101_native_coordinates_unavailable')
            qi -= 1
            ri -= 1
            positions, refs, symbols, reference_symbols = [], [], [], []
            for a,b in zip(q,r):
                if a != '-' and b != '-':
                    positions.append(qi); refs.append(ri); symbols.append(a.upper())
                    reference_symbols.append(b.upper())
                qi += a != '-'
                ri += b != '-'
            _require(len(positions) == component['counts']['paired_columns'], 'a101_native_map_conflict')
            result.append({'algorithm': 'blast', 'program': program,
                'hit_index': hit_index, 'hsp_index': hsp['hsp_index'],
                'native_record_key': f'{hit_index}:{hsp["hsp_index"]}',
                'bits': component['native_scores'].get('bit_score'),
                'native_evalue': component['native_scores'].get('evalue'),
                'alignment_identity': component['counts']['identical_pairs']/len(q),
                'reference_paired_count': len(set(refs)), 'reference_length': reference_length,
                'target_intervals': [[p,p+1] for p in positions],
                'target_symbols': list(zip(positions,symbols)),
                'residue_pairs': [[i,j,a,b] for i,j,a,b in zip(positions,refs,symbols,reference_symbols,strict=True)],
                'native_scope': 'blast_hsp'})
    return result
