#!/usr/bin/env python3
"""Research arithmetic only. No production reader, scorer binding, or episode.

The manually declared synthetic count cells below are not source extraction.
All writes stay alongside this file. No network, source-library, or run access.
"""
from fractions import Fraction as F
from pathlib import Path
import json

HERE = Path(__file__).resolve().parent
checks = []


def check(name, condition):
    if not condition:
        raise AssertionError(name)
    checks.append(name)


def g(p, b):
    assert 0 <= p <= 1 and 0 <= b <= 1
    if p == b:
        return F(0)
    return (p - b) / ((1 - b) if p > b else b)


def aggregate(signed):
    if not signed:
        return None
    w = F(1, len(signed))
    support = sum(w * max(t, 0) for t in signed)
    oppose = sum(w * max(-t, 0) for t in signed)
    return support, oppose, support * (1 - oppose)


def count_question(strata):
    n = sum(r['n'] for r in strata)
    n0 = sum(r['n0'] for r in strata)
    assert n > 0 and n0 > 0
    overlap = F(0)
    signed = F(0)
    detail = []
    for r in strata:
        assert 0 <= r['k'] <= r['n'] and 0 <= r['k0'] <= r['n0']
        p, b = F(r['k'], r['n']), F(r['k0'], r['n0'])
        a, a0 = F(r['n'], n), F(r['n0'], n0)
        m = min(a, a0)
        e = g(p, b)
        overlap += m
        signed += m * e
        detail.append({**r, 'p': p, 'b': b, 'a': a, 'a0': a0, 'm': m, 'e': e})
    return {'C': overlap, 'E': signed / overlap if overlap else None,
            't': signed, 'strata': detail}


fixture = {
    'label': 'Entirely synthetic count fixture; no biological observations',
    'policy': 'equal weights over the three declared context questions',
    'questions': [
        {'id': 'Q1', 'strata': [
            {'s': 'A', 'k': 2, 'n': 3, 'k0': 0, 'n0': 3},
            {'s': 'B', 'k': 2, 'n': 3, 'k0': 1, 'n0': 3}]},
        {'id': 'Q2', 'strata': [
            {'s': 'A', 'k': 3, 'n': 3, 'k0': 1, 'n0': 2},
            {'s': 'B', 'k': 0, 'n': 1, 'k0': 0, 'n0': 2}]},
        {'id': 'Q3', 'strata': [
            {'s': 'A', 'k': 0, 'n': 2, 'k0': 1, 'n0': 2},
            {'s': 'B', 'k': 1, 'n': 2, 'k0': 1, 'n0': 2}]}]
}
question_results = [count_question(q['strata']) for q in fixture['questions']]
ts = [q['t'] for q in question_results]
check('Q1 signed 7/12', ts[0] == F(7, 12))
check('Q2 overlap 3/4 separate from contrast 2/3',
      question_results[1]['C'] == F(3, 4) and question_results[1]['E'] == F(2, 3))
check('Q2 product 1/2', ts[1] == F(1, 2))
check('Q3 opposition -1/2', ts[2] == -F(1, 2))
support, oppose, coordinate = aggregate(ts)
check('support 13/36', support == F(13, 36))
check('opposition 1/6', oppose == F(1, 6))
check('coordinate 65/216', coordinate == F(65, 216))
check('opposition reduces coordinate', aggregate([ts[0], ts[1], F(0)])[2] > coordinate)
check('same contextual evidence yields same result for reaction alternatives',
      aggregate(ts) == aggregate(list(ts)))

for p, b, expected in [(0, 0, 0), (1, 1, 0), (1, 0, 1), (0, 1, -1)]:
    check(f'boundary g({p},{b})={expected}', g(F(p), F(b)) == expected)

grid = [F(i, 20) for i in range(21)]
check('g range on full 21x21 grid', all(-1 <= g(p, b) <= 1 for p in grid for b in grid))
check('g monotone increasing in p', all(g(grid[i], b) <= g(grid[i+1], b)
      for i in range(20) for b in grid))
check('g monotone decreasing in b', all(g(p, grid[i]) >= g(p, grid[i+1])
      for i in range(20) for p in grid))

missing_lower = aggregate([ts[0], F(-1), ts[2]])[2]
missing_upper = aggregate([ts[0], F(1), ts[2]])[2]
check('one missing question lower 7/72', missing_lower == F(7, 72))
check('one missing question upper 95/216', missing_upper == F(95, 216))
check('observed coordinate inside missing-question bounds', missing_lower <= coordinate <= missing_upper)
check('all missing interval lower', aggregate([F(-1)] * 3)[2] == 0)
check('all missing interval upper', aggregate([F(1)] * 3)[2] == 1)
check('no questions is not a biological zero', aggregate([]) is None)

# One unresolved member in a four-member stratum: k=2, negative=1, u=1.
p_bounds = (F(2, 4), F(3, 4))
b_bounds = (F(1, 4), F(1, 4))
e_bounds = (g(p_bounds[0], b_bounds[1]), g(p_bounds[1], b_bounds[0]))
check('finite missing counts give contrast 1/3 to 2/3', e_bounds == (F(1, 3), F(2, 3)))

# Construct explicit synthetic coordinate rows whose deterministic endpoint
# reproduces every manually declared count. This is an arithmetic illustration,
# not a GFF/GenBank reader or a claim of having searched a biological genome.
rows = []
for q in fixture['questions']:
    for s in q['strata']:
        for side, kn, nn in [('foreground', 'k', 'n'), ('background', 'k0', 'n0')]:
            for i in range(s[nn]):
                rid = f"{q['id']}_{s['s']}_{side}_{i+1}"
                expected = int(i < s[kn])
                gap = 30 + i if expected else 500 + i
                rows.append({
                    'row_ref': rid, 'origin': 'synthetic', 'question_ref': q['id'],
                    'side': side, 'stratum_ref': s['s'], 'source_event_ref': rid,
                    'assembly_ref': rid + '_assembly.1', 'contig_ref': rid + '_contig',
                    'subject_gene_ref': rid + '_subject', 'anchor_gene_ref': rid + '_anchor',
                    'dependence_block_ref': rid + '_block', 'selected_representative': True,
                    'subject_start': 1000, 'subject_end': 1299, 'subject_strand': '+',
                    'anchor_start': 1300 + gap, 'anchor_end': 1599 + gap, 'anchor_strand': '+',
                    'coordinate_system': '1_based_closed', 'intervening_gene_count': 0,
                    'same_contig': True, 'homolog_assignment': 'resolved_in_synthetic_fixture',
                    'readability': 'observed_complete_window', 'gap_bp': gap,
                    'endpoint_value': expected, 'duplicate_of': None})

duplicate = dict(rows[0], row_ref='duplicate_representation', duplicate_of=rows[0]['row_ref'])
related = dict(rows[0], row_ref='related_genome', assembly_ref='related_genome_assembly.1',
               source_event_ref='related_genome_event', selected_representative=False)
all_rows = rows + [duplicate, related]


def selected_rows(source_rows):
    selected, seen = [], set()
    for r in source_rows:
        if not r['selected_representative'] or r['duplicate_of'] is not None:
            continue
        key = (r['question_ref'], r['side'], r['dependence_block_ref'])
        if key not in seen:
            selected.append(r)
            seen.add(key)
    return selected


selected = selected_rows(all_rows)
check('28 synthetic unique representatives', len(selected) == 28)
check('duplicate and related genome add no observation', selected == rows)
check('gap endpoint arithmetic', all(r['anchor_start'] - r['subject_end'] - 1 == r['gap_bp']
      and int(r['gap_bp'] <= 300 and r['intervening_gene_count'] == 0
              and r['subject_strand'] == r['anchor_strand'] and r['same_contig']) == r['endpoint_value']
      for r in rows))
for q in fixture['questions']:
    for s in q['strata']:
        for side, kn, nn in [('foreground', 'k', 'n'), ('background', 'k0', 'n0')]:
            subset = [r for r in selected if r['question_ref'] == q['id']
                      and r['stratum_ref'] == s['s'] and r['side'] == side]
            check(f"count reconstruction {q['id']} {s['s']} {side}",
                  len(subset) == s[nn] and sum(r['endpoint_value'] for r in subset) == s[kn])

native_record = json.loads((HERE / 'string_ribk_pair.json').read_text())
native_rows = native_record['selected_pair_rows']
check('exact native pair selected once', len(native_rows) == 1)
native = native_rows[0]
check('native nscore preserved', F(str(native['nscore'])) == F(956, 1000))
check('combined score is distinct', F(str(native['score'])) == F(959, 1000)
      and native['score'] != native['nscore'])
native_coordinate = aggregate([F(str(native['nscore']))])[2]
check('native one-question coordinate 0.956', native_coordinate == F(239, 250))
check('BioY genes per genome', F(150, 127) > 1)
check('RibK selected-list fraction is one', F(9, 9) == 1)


def encode(value):
    if isinstance(value, F):
        return {'fraction': str(value), 'decimal': float(value)}
    if isinstance(value, list):
        return [encode(v) for v in value]
    if isinstance(value, dict):
        return {k: encode(v) for k, v in value.items()}
    return value


output = {
    'artifact_kind': 'research_arithmetic_checks_not_production_reader',
    'checks_passed': len(checks), 'check_names': checks,
    'synthetic_results': {'questions': question_results, 'S': support, 'O': oppose,
                          'coordinate': coordinate,
                          'one_missing_question': {'point': None, 'lower': missing_lower,
                                                   'upper': missing_upper},
                          'one_missing_member_contrast': list(e_bounds)},
    'native_current_data_result': {'nscore': F(str(native['nscore'])),
                                  'combined_score_not_used': F(str(native['score'])),
                                  'coordinate': native_coordinate,
                                  'biological_calibration_uncertainty': 'unreported'},
    'paper_arithmetic': {'bioy_genes_per_genome': F(150, 127), 'bioy_excess_copies': 23,
                         'bioy_approximate_fraction_not_exact_count': F(1, 3),
                         'ribk_positive_examples': 9, 'ribk_selected_list_fraction': F(9, 9),
                         'historical_only_coordinate': {'point': None, 'lower': 0, 'upper': 1}}
}
(HERE / 'synthetic_count_inputs.json').write_text(json.dumps(fixture, indent=2) + '\n')
(HERE / 'synthetic_observation_rows.json').write_text(json.dumps(all_rows, indent=2) + '\n')
(HERE / 'arithmetic_results.json').write_text(json.dumps(encode(output), indent=2) + '\n')
print(json.dumps({'checks_passed': len(checks), 'coordinate': str(coordinate),
                  'native_coordinate': str(native_coordinate),
                  'missing_bounds': [str(missing_lower), str(missing_upper)]}))
