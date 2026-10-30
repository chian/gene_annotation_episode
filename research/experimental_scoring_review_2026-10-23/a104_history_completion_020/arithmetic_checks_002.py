"""Corrected arithmetic fixture for A104 proposal 002; not a reader/scorer.

Version 001 remains preserved. This checks conjunctive named-route compatibility
and explicit max over alternative physical routes, with unknown other routes.

All complete candidate inputs are synthetic. This invokes the retained pure
toy-tree checker only to verify shared geometry; no biological input is read,
no inference tool is run, and no existing record is modified. Output is JSON
to stdout only. Invoke from any directory with python3.
"""
from contextlib import redirect_stdout
from fractions import Fraction as Q
from io import StringIO
from itertools import product
from pathlib import Path
import json
import math
import runpy


base = Path(__file__).resolve().parent.parent
with redirect_stdout(StringIO()):
    legacy = runpy.run_path(str(base / 'a104_phylogeny_sheet_012' / 'arithmetic_checks_001.py'))
plus, minus = legacy['a'], legacy['b']
assert plus['P'] == 1 and minus['P'] == -1
assert plus['outlier_F']['factor'] == Q(3, 4)
assert minus['outlier_G']['factor'] == Q(1, 2)
assert plus['history_counts']['discordant'] == 6
assert minus['history_counts']['concordant'] == 6

# Synthetic environmental data, ordered marine / intestinal / coastal.
donor_counts = [80, 20, 0]
recipient_counts = [0, 75, 25]
donor = [Q(x, 100) for x in donor_counts]
recipient = [Q(x, 100) for x in recipient_counts]
route = [[Q(0), Q(60, 80), Q(10, 80)],
         [Q(0), Q(20, 20), Q(0)],
         [Q(0), Q(0), Q(0)]]
assert sum(donor) == sum(recipient) == 1
assert all(0 <= sum(row) <= 1 for row in route)
routed = [sum(donor[i] * route[i][j] for i in range(3)) for j in range(3)]
B = sum(min(d, r) for d, r in zip(routed, recipient))
assert routed == [0, Q(4, 5), Q(1, 10)]
assert sum(routed) == Q(9, 10) and B == Q(17, 20)

# Synthetic narrow membership judgment, not a paper-derived number.
cargo = [{'length_bp': 600, 'm': Q(1), 'status': 'synthetic_observed'},
         {'length_bp': 200, 'm': Q(1, 2), 'status': 'synthetic_explicit_judgment'},
         {'length_bp': 200, 'm': Q(0), 'status': 'synthetic_documented_exclusion'}]
L = sum(row['length_bp'] for row in cargo)
M = sum(row['length_bp'] * row['m'] for row in cargo) / L
T = Q(9, 10)
E = T * B * M
assert L == 1000 and M == Q(7, 10) and E == Q(1071, 2000)
# Splitting one interval does not manufacture additional coverage.
assert M == (300 + 300 + 200 * Q(1, 2) + 200 * Q(0)) / 1000


def fixture_region(plus_count, event_explanation):
    s = plus['outlier_F']['factor'] * event_explanation
    c = minus['outlier_G']['factor']
    positive = Q(plus_count, 10) * s
    opposing = Q(10 - plus_count, 10) * c
    scores = [-c] * (10 - plus_count) + [s] * plus_count
    scores.sort()
    return {'trees': 10, 'plus_count': plus_count, 'minus_count': 10 - plus_count,
            'E_plus': event_explanation, 'H_minus': Q(1),
            'plus_own_support': s, 'minus_own_opposition': c,
            'positive': positive, 'opposing': opposing, 'signed': positive - opposing,
            'empirical_025': scores[max(1, math.ceil(.025 * 10)) - 1],
            'empirical_975': scores[max(1, math.ceil(.975 * 10)) - 1]}


R1 = fixture_region(8, E)
R2 = fixture_region(9, Q(3, 5))
R3 = fixture_region(6, Q(1))
assert (R1['positive'], R1['opposing'], R1['signed']) == (Q(3213, 10000), Q(1, 10), Q(2213, 10000))
assert (R2['positive'], R2['opposing'], R2['signed']) == (Q(81, 200), Q(1, 20), Q(71, 200))
assert (R3['positive'], R3['opposing'], R3['signed']) == (Q(9, 20), Q(1, 5), Q(1, 4))

I1_S = min(R1['positive'], R2['positive'])
I1_O = max(R1['opposing'], R2['opposing'])
I2_S, I2_O = R3['positive'], R3['opposing']
S_C = min(I1_S, I2_S)
O_C = max(I1_O, I2_O)
Z_C = S_C - O_C
C_C = max(Q(0), Z_C)
assert (S_C, O_C, Z_C, C_C) == (Q(3213, 10000), Q(1, 5), Q(1213, 10000), Q(1213, 10000))
# Duplication/aliases do not alter extrema. This is an arithmetic property,
# not a claim that a real source identity resolver is implemented here.
assert min(R1['positive'], R1['positive'], R2['positive'], R3['positive']) == S_C
assert max(R1['opposing'], R1['opposing'], R2['opposing'], R3['opposing']) == O_C
contradictory_S = min(S_C, Q(1, 5))
contradictory_O = max(O_C, Q(1, 4))
assert contradictory_S - contradictory_O == -Q(1, 20)
assert max(Q(0), contradictory_S - contradictory_O) == 0


def candidate_with_r1_support(s):
    return max(Q(0), min(s, R2['positive'], R3['positive']) - O_C)


membership_interval = []
for m in [Q(3, 10), Q(7, 10)]:
    mechanism = Q(3, 5) + Q(1, 5) * m
    explanation = T * B * mechanism
    support = Q(8, 10) * Q(3, 4) * explanation
    membership_interval.append({'m': m, 'M': mechanism, 'E': explanation,
                                'R1_positive': support, 'candidate': candidate_with_r1_support(support)})
assert [x['candidate'] for x in membership_interval] == [Q(5147, 50000), Q(6983, 50000)]
missing_membership = [candidate_with_r1_support(Q(8, 10) * Q(3, 4) * T * B * (Q(3, 5) + Q(1, 5) * m))
                      for m in [Q(0), Q(1)]]
assert missing_membership == [Q(377, 5000), Q(209, 1250)]
missing_environment_r1 = [Q(8, 10) * Q(3, 4) * T * b * M for b in [Q(0), Q(1)]]
assert missing_environment_r1 == [Q(0), Q(189, 500)]
missing_environment_candidate = [candidate_with_r1_support(x) for x in missing_environment_r1]
assert missing_environment_candidate == [Q(0), Q(89, 500)]
sparse_reference_r1 = [Q(0), Q(8, 10) * E]
assert sparse_reference_r1 == [Q(0), Q(1071, 2500)]
assert [candidate_with_r1_support(s) for s in sparse_reference_r1] == [Q(0), Q(41, 200)]

# Excluding one route does not exclude another or an unexamined route.
excluded_route = Q(0)
other_examined_route = Q(2, 5)
assert max(excluded_route, other_examined_route) == Q(2, 5)
assert max(excluded_route, excluded_route) == 0
assert [max(excluded_route, unknown) for unknown in [Q(0), Q(1)]] == [Q(0), Q(1)]
unknown_other_event = [E, Q(1)]
unknown_other_candidate = [candidate_with_r1_support(Q(8, 10) * Q(3, 4) * x) for x in unknown_other_event]
assert unknown_other_candidate == [Q(1213, 10000), Q(41, 200)]
# A known exclusion of this route's whole cargo or chronology cannot be rescued.
assert T * B * Q(0) == 0 and Q(0) * B * M == 0

# The retained asymmetry is not antisymmetry.
asym_positive = Q(1) * Q(3, 4) * Q(2, 5)
asym_reversed = -Q(1) * Q(3, 4)
assert (asym_positive, asym_reversed) == (Q(3, 10), -Q(3, 4))
assert asym_positive + asym_reversed == -Q(1) * Q(3, 4) * (1 - Q(2, 5))

# True joint chronology/explanation dependence must be calculated before mean.
joint = [(Q(1, 2), Q(1), Q(1), Q(1)), (Q(1, 2), Q(0), Q(0), Q(0))]
joint_E = sum(w * t * b * m for w, t, b, m in joint)
product_of_means = sum(w * t for w, t, b, m in joint) * sum(w * b for w, t, b, m in joint) * sum(w * m for w, t, b, m in joint)
assert joint_E == Q(1, 2) and product_of_means == Q(1, 8)

checks = 0
grid = [Q(0), Q(1, 5), Q(1, 2), Q(1)]
for b, m, t, p, of, og in product(grid, grid, grid, [-1, Q(-1, 2), 0, Q(1, 2), 1], grid, grid):
    e = t * b * m
    s = max(Q(0), p) * of * e
    o = max(Q(0), -p) * og
    assert 0 <= e <= 1 and 0 <= s <= 1 and 0 <= o <= 1 and -1 <= s - o <= 1
    assert 0 <= max(Q(0), s - o) <= 1
    checks += 1


def export(x):
    if isinstance(x, Q):
        return {'exact': str(x), 'decimal': float(x)}
    if isinstance(x, dict):
        return {k: export(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [export(v) for v in x]
    return x


result = {
    'status': 'all assertions passed; research arithmetic only',
    'published_arithmetic_only': {
        'smillie_reported_enrichment': 25,
        'smillie_inverse_frequency_diagnostic_not_B': Q(1, 25),
        'hehemann_observed_Japanese_prevalence': Q(4, 13),
        'hehemann_observed_NorthAmerican_nondetection': Q(0, 18),
        'hehemann_observed_prevalence_difference_not_causal': Q(4, 13),
        'hehemann_descriptor_direct_overlap_not_historical_contact': Q(0),
        'hehemann_Bp1689_placement': Q(1), 'hehemann_Bp1670_placement': Q(-1)},
    'synthetic_R1_explanation': {'donor_counts': donor_counts, 'recipient_counts': recipient_counts,
                                'donor': donor, 'recipient': recipient, 'K': route,
                                'routed_donor': routed, 'B': B, 'cargo': cargo,
                                'cargo_length_bp': L, 'M': M, 'T': T, 'E': E},
    'synthetic_regions': {'R1': R1, 'R2': R2, 'R3': R3},
    'synthetic_candidate': {'requirements': {'I1': ['R1', 'R2'], 'I2': ['R3']},
                            'inference_I1': {'support': I1_S, 'opposition': I1_O},
                            'inference_I2': {'support': I2_S, 'opposition': I2_O},
                            'support': S_C, 'opposition': O_C, 'signed': Z_C, 'coordinate': C_C,
                            'duplicate_or_alias_coordinate': C_C,
                            'with_contradictory_R3_scenario': {'support': contradictory_S, 'opposition': contradictory_O,
                                                               'signed': contradictory_S - contradictory_O, 'coordinate': Q(0)}},
    'identification_bounds': {'membership_m_03_to_07': membership_interval,
                             'membership_unknown_candidate': missing_membership,
                             'environment_unknown_R1': missing_environment_r1,
                             'environment_unknown_candidate': missing_environment_candidate,
                             'one_positive_reference_R1_support': sparse_reference_r1,
                             'one_positive_reference_candidate': [Q(0), Q(41, 200)]},
    'alternative_routes': {'excluded_route': excluded_route, 'supported_second_route': other_examined_route,
                           'event_union': max(excluded_route, other_examined_route),
                           'excluded_only_with_unknown_others': [Q(0), Q(1)],
                           'R1_with_unknown_other_routes_event': unknown_other_event,
                           'R1_with_unknown_other_routes_candidate': unknown_other_candidate},
    'asymmetry': {'positive': asym_positive, 'reverse': asym_reversed},
    'joint_history_dependence': {'correct_within_sample_mean': joint_E, 'incorrect_product_of_means': product_of_means},
    'bounded_range_grid_checks': checks,
    'limitations': ['Synthetic complete example; no biological inference or reader implementation.',
                    'Published quantities manually extracted; arithmetic does not verify primary observations.',
                    'No adopted scoring policy, candidate calibration, W05 wiring, or axis completion.']}
print(json.dumps(export(result), indent=2))
