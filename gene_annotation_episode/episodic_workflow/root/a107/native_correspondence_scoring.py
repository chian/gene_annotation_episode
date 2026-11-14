"""Private A107 native residue-map readers and coefficients."""
from types import MappingProxyType

SCALES = MappingProxyType({'blast': 0.025, 'hmmer': 0.020})

class NativeCorrespondenceUnavailable(ValueError):
    def __init__(self, code, **detail):
        self.code, self.detail = code, detail
        super().__init__(code)


def _require(condition, code, **detail):
    if not condition:
        raise NativeCorrespondenceUnavailable(code, **detail)


def hmmer_comparisons(grading):
    """R3 native fields/maps, with phmmer's query-profile orientation intact."""
    sheet, scores = grading.get('sheet'), grading.get('scores')
    _require(isinstance(sheet, dict) and sheet.get('schema') == 'hmmer_search_sheet_v1'
        and isinstance(scores, dict) and scores.get('schema') == 'hmmer_search_scores_v1',
        'a107_correspondence_hmmer_grading_unavailable')
    program = sheet['operation']['program']
    _require(program in {'phmmer', 'hmmsearch', 'hmmscan'},
        'a107_correspondence_original_query_mapping_unavailable', program=program)
    result = []
    for row in sheet['domains']:
        matches = [d for d in scores['domains'] if d['record_key'] == row['record_key']]
        _require(len(matches) == 1, 'a107_correspondence_hmmer_domain_join_ambiguous')
        score = matches[0]
        alignment, bounds = row.get('alignment', {}), score.get('intervals', {})
        model, sequence = alignment.get('model'), alignment.get('aseq')
        _require(isinstance(model, str) and isinstance(sequence, str) and len(model) == len(sequence),
            'a107_correspondence_native_traceback_unavailable')
        _require(bounds.get('model') is not None and bounds.get('sequence') is not None,
            'a107_correspondence_native_coordinates_unavailable')
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
            and len(target) == score.get('paired_positions'), 'a107_correspondence_native_map_conflict')
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
    raise NativeCorrespondenceUnavailable('a107_correspondence_unsupported_score_profile', schema=schema)


def blast_comparisons(grading):
    """R2 cells from already calculated protein BLAST HSP components."""
    sheet = grading['sheet']
    normalized = sheet.get('input', sheet.get('normalized_result', {}))
    program = normalized.get('search', {}).get('program')
    _require(program == 'blastp', 'a107_correspondence_translated_or_nucleotide_map_not_bound', program=program)
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
        raise NativeCorrespondenceUnavailable('a107_correspondence_unsupported_score_profile', schema=sheet['schema'])
    for hit_index, hsps, reference_length in populations:
        for hsp in hsps:
            native, component = hsp['native'], hsp['components']
            q, r = native.get('qseq'), native.get('hseq', native.get('sseq'))
            _require(isinstance(q,str) and isinstance(r,str) and len(q) == len(r),
                'a107_correspondence_native_traceback_unavailable')
            qi, ri = native.get('query_from', native.get('qstart')), native.get('hit_from', native.get('sstart'))
            _require(type(qi) is int and type(ri) is int, 'a107_correspondence_native_coordinates_unavailable')
            qi -= 1
            ri -= 1
            positions, refs, symbols, reference_symbols = [], [], [], []
            for a,b in zip(q,r):
                if a != '-' and b != '-':
                    positions.append(qi); refs.append(ri); symbols.append(a.upper())
                    reference_symbols.append(b.upper())
                qi += a != '-'
                ri += b != '-'
            _require(len(positions) == component['counts']['paired_columns'], 'a107_correspondence_native_map_conflict')
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
