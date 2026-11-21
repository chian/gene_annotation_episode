"""Differential credit over candidate annotations: A102's own copy of the owner's formula of 2026-11-20 (A101 has its own,
``grading/sequence_homology_evidence/differential_credit.py``, which names A101's sheet families and stays untouched; the
repository keeps one such library per axis).

"The graders should additively add to the subscoring sheets and then the subscoring sheets additively add to the score"
(the owner, 2026-11-21).

THE SCORING SHEET'S WEIGHTS (the owner, 2026-11-21: the scoring sheet weighs the subscoring sheets into the score with stated
weights, so each sheet's typical strong result counts comparably). ``SHEET_WEIGHT[family]`` multiplies every value of a test of
that family (the part of the test name before its first ``:``); a candidate's value in a test, its sheet value, its score, its
entry and every differential are in these weighted units. The weight of a family is one over its typical strong value
(``TYPICAL_STRONG_VALUE``).

A measurement is one graded result: the test it belongs to, the candidate annotation its reference stands for, and its value on
the subscoring sheet. Measurements are given in the order they arrived. The tests are ordered by their first measurement.

- A candidate's value in one test is the mean of its measurements in that test (its replicates in that test: the hits of one
  structure search that share a product), times the weight of the test's family. Round 1 has one family, ``structure_search``,
  whose raw value (the index B of ``scoring.geometry``) lies in [0, 1]; the second family, ``site_correspondence``, has a raw
  value (the mean E = B F of the hits with sites) in [0, 1] as well.
- A subscoring sheet is a kind of test: the part of the test name before ``@``
  (``structure_search:foldseek:tmalign:<database>``). A candidate's value on a sheet is the SUM of its values in the tests of
  that kind.
- The score ``S_c`` of a candidate is the SUM of its sheet values, which is the sum of its values over all the tests it has
  undergone so far. A test therefore moves the score by exactly the candidate's value in it, never below zero.
- A candidate is a possibility only on positive evidence: it is admitted with its first value above zero and earns its score
  after the test that admitted it. A candidate that never scored above zero is not on the list and earns nothing.
- A test that two candidates both underwent after both were already on the list earns ``|d_A - d_B|`` for that pair, where
  ``d_c`` is the change of ``S_c`` over that test, that is, the candidate's value in that test. The test that admits a
  candidate earns that candidate's entry score only: its rise from nothing is not counted a second time as a differential. A
  test only one of the two underwent earns nothing for the pair until the other undergoes it too.

``credit`` is the sum of the entry scores and of the differentials: it never falls. Nothing here reads a record, a file or a
model. A102 has no dataset rule and no evidence weighting in round 1 (those are A101's, for its clustering test)."""
import math
from itertools import combinations


# The typical strong value of each sheet's family: the value, in ONE test of the family, of the candidate that leads stored real
# runs (the derivation is written here when there is one).
# no real run yet: 1 until real runs give the family's typical strong value (SOP Step 6)
TYPICAL_STRONG_VALUE = {'structure_search': 1.0,
                        # no real run yet: 1 until real runs give the family's typical strong value (SOP Step 6)
                        'site_correspondence': 1.0}
SHEET_WEIGHT = {family: 1 / value for family, value in TYPICAL_STRONG_VALUE.items()}


def sheet_weight(test):
    """The weight of the family of ``test`` (the part of its name before the first ``:`` or ``@``)."""
    return SHEET_WEIGHT[test.split('@', 1)[0].split(':', 1)[0]]


def _kind(test):
    """The subscoring sheet of a test: its kind, the part of the name before ``@``."""
    return test.split('@', 1)[0]


def differential_credit(measurements):
    """The scores, the sheets and the credit of ``measurements`` (``[{'test', 'candidate', 'value'}]``, in arrival order).
    Also ``entries`` (each admitted candidate's entry score), ``differentials`` (each: the ``test``, the ``pair`` and the
    ``value`` it earned, equal to the ``difference`` of the two moves) and ``test_credits`` (each test's entries plus its
    differentials)."""
    tests, values = [], {}
    for row in measurements:
        if row['test'] not in tests:
            tests.append(row['test'])
        values.setdefault((row['test'], row['candidate']), []).append(row['value'])
    candidates = sorted({candidate for _, candidate in values})
    sheets = {candidate: {} for candidate in candidates}
    changes, entries, admitted = {}, {}, {}

    def score(candidate):
        return math.fsum(math.fsum(held) for held in sheets[candidate].values())
    for test in tests:
        for candidate in candidates:
            if (test, candidate) not in values:
                continue
            replicates = values[test, candidate]
            value = sheet_weight(test) * math.fsum(replicates) / len(replicates)
            sheets[candidate].setdefault(_kind(test), []).append(value)
            changes[test, candidate] = value
            if candidate not in entries and value > 0:
                entries[candidate], admitted[candidate] = score(candidate), tests.index(test)
    differentials = [{'test': test, 'pair': [first, second],
                      'value': abs(changes[test, first] - changes[test, second]),
                      'difference': abs(changes[test, first] - changes[test, second])}
                     for position, test in enumerate(tests) for first, second in combinations(sorted(entries), 2)
                     if (test, first) in changes and (test, second) in changes
                     and position > max(admitted[first], admitted[second])]
    test_credits = {test: math.fsum([entries[candidate] for candidate in entries if tests[admitted[candidate]] == test]
                                    + [row['value'] for row in differentials if row['test'] == test]) for test in tests}
    return {'scores': {candidate: score(candidate) for candidate in sorted(entries)},
            'sheets': {candidate: {kind: math.fsum(held) for kind, held in sheets[candidate].items()}
                       for candidate in sorted(entries)},
            'entries': entries, 'differentials': differentials, 'test_credits': test_credits,
            'credit': math.fsum(test_credits.values())}


def standing(measurements):
    """Where each candidate stands before a further test: ``{candidate: {'sheets', 'score', 'listed'}}`` for every
    candidate measured so far (listed or not): its value on each sheet (the sum of its values in the tests of that kind),
    its score (the sum of its sheet values) and whether it is on the list (its score is above zero; values are never
    below zero)."""
    held = {}
    for row_test, row_candidate in dict.fromkeys((row['test'], row['candidate']) for row in measurements):
        replicates = [row['value'] for row in measurements
                      if row['test'] == row_test and row['candidate'] == row_candidate]
        held.setdefault(row_candidate, {}).setdefault(_kind(row_test), []).append(
            sheet_weight(row_test) * math.fsum(replicates) / len(replicates))
    sheets = {candidate: {kind: math.fsum(values) for kind, values in kinds.items()} for candidate, kinds in held.items()}
    return {candidate: {'sheets': kinds, 'score': math.fsum(kinds.values()), 'listed': math.fsum(kinds.values()) > 0}
            for candidate, kinds in sheets.items()}


def test_ceiling(held, measurable, family, unseen=0, limit=None):
    """The most one further test can add to the credit of one target, from where the list stands.

    ``held`` is ``standing`` of the target. The test measures candidates of ``measurable`` (identifiers, each possibly
    not yet held) and up to ``unseen`` others never met, at most ``limit`` candidates in all when ``limit`` is given.
    Scores are additive and a candidate's value in a test of ``family`` is in [0, w], ``w`` = ``SHEET_WEIGHT[family]`` (the raw
    value is in [0, 1]), so the test moves a score by its value, between 0 and ``w``. The test is the last one, so it earns:

    * for two candidates on the list that it measures, the size of the difference of their moves: at most ``w`` for each pair;
    * for a candidate not on the list that it admits, the entry score (its first score): at most ``w`` each (the test that
      admits a candidate earns that candidate's entry only, so a pair with it earns nothing in this test);
    * nothing else: a test that measures one candidate on the list and admits none earns 0.

    With ``m`` listed candidates measured and the others new, the bound is ``m(m-1)/2`` pairs plus one for each new one, times
    ``w``; with a ``limit`` of ``k`` it is the largest of that over the ``m`` that leave ``k - m`` places for the new ones. It
    is a bound, not a forecast."""
    weight = SHEET_WEIGHT[family]
    listed = {candidate for candidate, state in held.items() if state['listed']}
    count = len({candidate for candidate in measurable if candidate in listed})
    new = len({candidate for candidate in measurable if candidate not in listed}) + unseen
    if limit is None:
        return weight * float(count * (count - 1) // 2 + new)
    return weight * float(max(m * (m - 1) // 2 + min(limit - m, new) for m in range(min(limit, count) + 1)))


def vertex_maximum(held, maxima, measurable):
    """The largest rise of the credit over values ``0 <= v_c <= maxima[c]`` of the ``measurable`` candidates in one test appended
    last: the entries of the candidates not listed (each at its maximum) plus, over the sets ``S`` of listed candidates at their
    maximum (the others at 0), ``sum_{a<b in S} |m_a - m_b| + sum_{a in S, b not in S} m_a``; above 16 listed candidates the
    looser ``sum over pairs of max(m_a, m_b)``. The rise is the sum of ``v_c`` over the unlisted candidates plus ``|v_a - v_b|``
    over the listed pairs, a convex function of ``v`` on the box, so it is largest at a vertex (``v_c`` equal to 0 or ``m_c``)."""
    measured = [candidate for candidate in dict.fromkeys(measurable) if maxima[candidate] > 0]
    listed = [candidate for candidate in measured if held.get(candidate, {}).get('listed')]
    new = math.fsum(maxima[candidate] for candidate in measured if candidate not in listed)
    if len(listed) > 16:
        return new + math.fsum(max(maxima[first], maxima[second]) for first, second in combinations(listed, 2))
    best = 0.0
    for mask in range(1 << len(listed)):
        inside = [maxima[listed[i]] for i in range(len(listed)) if mask >> i & 1]
        outside = len(listed) - len(inside)
        best = max(best, math.fsum(abs(a - b) for a, b in combinations(inside, 2)) + outside * math.fsum(inside))
    return new + best


def site_test_ceiling(held, candidates):
    """The most one ``site_correspondence`` test can add to the credit of one target, from where the list stands (``held`` is
    ``standing`` of the target; ``candidates``: the identifiers of the candidates of the graded search it grades, all of which
    are already listed in the search's own test).

    PROOF. A candidate's value in the test is its mean E over its hits with sites, ``E = B F``; ``B`` is in [0, 1]
    (``B = [2 n / (L_target + L_reference)] / [1 + (RMSD / 2 A)^2]`` with ``n`` at most the shorter length, so the first factor
    is at most 1) and ``F`` is a mean of residue scores, each a class match 0 or 1 times a kernel in (0, 1]. So the raw value is
    in [0, 1] and, times the family weight ``w``, the candidate's move ``v_c`` is in [0, w]. A candidate with no hit with sites
    is not measured (a candidate not measured earns nothing), so each candidate's move is anywhere in [0, w], at most, whatever
    the sites turn out to be. The test is appended last. By the credit rule it earns the entry score of each candidate it admits
    (a candidate not yet on the list whose ``v_c`` is above 0: its score becomes ``v_c``) plus ``|v_a - v_b|`` for each pair of
    candidates both already on the list that it measures. The rise is therefore
    ``sum_{c not listed} v_c + sum_{a < b listed} |v_a - v_b|``, a convex function of ``v`` (sums of linear terms and absolute
    values of linear terms) on the box ``0 <= v_c <= w``, so it is largest at a vertex of the box: every ``v_c`` equal to 0 or
    ``w``. ``vertex_maximum`` takes the maximum over those vertices (exact up to 16 listed candidates, a looser bound above). Here
    every maximum is the same ``w``, so the maximum has a closed form that is exact for any number of candidates: with ``k``
    candidates listed and ``u`` not listed, a vertex puts ``s`` listed candidates at ``w`` and the rest at 0; the pairs earn ``w``
    for each of the ``s (k - s)`` pairs with one candidate in each group and 0 inside a group, so the rise is
    ``w (u + s (k - s))``, largest at ``s = k // 2``: ``w (u + k^2 // 4)``. That is what is returned (equal to
    ``vertex_maximum`` whenever that is exact; its looser bound above 16 listed candidates would overstate it twofold).
    It is a bound, not a forecast."""
    weight = SHEET_WEIGHT['site_correspondence']
    candidates = list(dict.fromkeys(candidates))
    listed = sum(1 for candidate in candidates if held.get(candidate, {}).get('listed'))
    return weight * float(len(candidates) - listed + listed * listed // 4)
