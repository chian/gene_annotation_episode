"""Differential credit over candidate annotations (the owner's formula of 2026-11-20).

"The graders should additively add to the subscoring sheets and then the subscoring sheets additively add to the score"
(the owner, 2026-11-21).

A measurement is one graded result: the test it belongs to (the same tool, settings and region of the target), the
candidate annotation its reference stands for, and its value on the subscoring sheet (0 to 1). Measurements are
given in the order they arrived. The tests are ordered by their first measurement.

- A candidate's value in one test is the mean of its measurements in that test (its replicates in that test), in
  [0, 1].
- A subscoring sheet is a kind of test: the part of the test name before ``@`` (for example ``database_search:...``,
  ``profile_scan:...``, ``msa:...``). A candidate's value on a sheet is the SUM of its values in the tests of that
  kind.
- The score ``S_c`` of a candidate is the SUM of its sheet values, which is the sum of its values over all the tests it
  has undergone so far. A test therefore moves the score by exactly the candidate's value in it, never below zero.
- A candidate is a possibility only on positive evidence: it is admitted with its first value above zero and earns
  its score after the test that admitted it (that value, since nothing was added before). A candidate that never
  scored above zero is not on the list and earns nothing.
- A test that two candidates both underwent after both were already on the list earns ``|d_A - d_B|`` for that
  pair, where ``d_c`` is the change of ``S_c`` over that test, that is, the candidate's value in that test. The test
  that admits a candidate earns that candidate's entry score only: its rise from nothing is not counted a second time
  as a differential. A test only one of the two underwent earns nothing for the pair until the other undergoes it
  too.

``credit`` is the sum of the entry scores and of the differentials: it never falls. Nothing here reads a record, a
file or a model."""
import math
from itertools import combinations


def _kind(test):
    """The subscoring sheet of a test: its kind, the part of the name before ``@``."""
    return test.split('@', 1)[0]


def differential_credit(measurements):
    """The scores, the sheets and the credit of ``measurements`` (``[{'test', 'candidate', 'value'}]`` in arrival
    order)."""
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
            value = math.fsum(replicates) / len(replicates)
            sheets[candidate].setdefault(_kind(test), []).append(value)
            changes[test, candidate] = value
            if candidate not in entries and value > 0:
                entries[candidate], admitted[candidate] = score(candidate), tests.index(test)
    differentials = [{'test': test, 'pair': [first, second],
                      'value': abs(changes[test, first] - changes[test, second])}
                     for position, test in enumerate(tests) for first, second in combinations(sorted(entries), 2)
                     if (test, first) in changes and (test, second) in changes
                     and position > max(admitted[first], admitted[second])]
    return {'scores': {candidate: score(candidate) for candidate in sorted(entries)},
            'sheets': {candidate: {kind: math.fsum(held) for kind, held in sheets[candidate].items()}
                       for candidate in sorted(entries)},
            'entries': entries, 'differentials': differentials,
            'credit': math.fsum(entries.values()) + math.fsum(row['value'] for row in differentials)}


def standing(measurements):
    """Where each candidate stands before a further test: ``{candidate: {'sheets', 'score', 'listed'}}`` for every
    candidate measured so far (listed or not): its value on each sheet (the sum of its values in the tests of that kind),
    its score (the sum of its sheet values) and whether it is on the list (its score is above zero; values are never
    below zero)."""
    held = {}
    for row_test, row_candidate in dict.fromkeys((row['test'], row['candidate']) for row in measurements):
        replicates = [row['value'] for row in measurements
                      if row['test'] == row_test and row['candidate'] == row_candidate]
        held.setdefault(row_candidate, {}).setdefault(_kind(row_test), []).append(math.fsum(replicates) / len(replicates))
    sheets = {candidate: {kind: math.fsum(values) for kind, values in kinds.items()}
              for candidate, kinds in held.items()}
    return {candidate: {'sheets': kinds, 'score': math.fsum(kinds.values()), 'listed': math.fsum(kinds.values()) > 0}
            for candidate, kinds in sheets.items()}


def test_ceiling(held, measurable, unseen=0, limit=None):
    """The most one further test can add to the credit of one target, from where the list stands.

    ``held`` is ``standing`` of the target. The test measures candidates of ``measurable`` (identifiers, each possibly
    not yet held) and up to ``unseen`` others never met, at most ``limit`` candidates in all when ``limit`` is given.
    Scores are additive and a candidate's value in a test is in [0, 1], so the test moves a score by its value, between
    0 and 1. The test is the last one, so it earns:

    * for two candidates on the list that it measures, the size of the difference of their moves: at most 1 for each pair;
    * for a candidate not on the list that it admits, the entry score (its first score): at most 1 each (the test that
      admits a candidate earns that candidate's entry only, so a pair with it earns nothing in this test);
    * nothing else: a test that measures one candidate on the list and admits none earns 0.

    With ``m`` listed candidates measured and the others new, the bound is ``m(m-1)/2`` pairs plus one for each new one;
    with a ``limit`` of ``k`` it is the largest of that over the ``m`` that leave ``k - m`` places for the new ones. It is
    a bound, not a forecast."""
    listed = {candidate for candidate, state in held.items() if state['listed']}
    count = len({candidate for candidate in measurable if candidate in listed})
    new = len({candidate for candidate in measurable if candidate not in listed}) + unseen
    if limit is None:
        return float(count * (count - 1) // 2 + new)
    return float(max(m * (m - 1) // 2 + min(limit - m, new) for m in range(min(limit, count) + 1)))
