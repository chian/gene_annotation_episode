"""Differential credit over candidate annotations (the owner's formula of 2026-11-20).

A measurement is one graded result: the test it belongs to (the same tool, settings and region of the target), the
candidate annotation its reference stands for, and its value on the subscoring sheet (0 to 1). Measurements are
given in the order they arrived. The tests are ordered by their first measurement.

- The score ``S_c`` of a candidate after a test is the mean of its values over the tests it has undergone so far;
  its value in one test is the mean of its measurements in that test (its replicates in that test).
- A candidate is a possibility only on positive evidence: it is admitted with its first value above zero and earns
  its score after the test that admitted it. A candidate that never scored above zero is not on the list and earns
  nothing.
- A test that two candidates both underwent after both were already on the list earns ``|d_A - d_B|`` for that
  pair, where ``d_c`` is the change of ``S_c`` over that test. The test that admits a candidate earns that
  candidate's entry score only: its rise from nothing is not counted a second time as a differential. A test only
  one of the two underwent earns nothing for the pair until the other undergoes it too.

``credit`` is the sum of the entry scores and of the differentials. Nothing here reads a record, a file or a model."""
import math
from itertools import combinations


def differential_credit(measurements):
    """The scores and the credit of ``measurements`` (``[{'test', 'candidate', 'value'}]`` in arrival order)."""
    tests, values = [], {}
    for row in measurements:
        if row['test'] not in tests:
            tests.append(row['test'])
        values.setdefault((row['test'], row['candidate']), []).append(row['value'])
    candidates = sorted({candidate for _, candidate in values})
    scores, changes, entries, admitted = dict.fromkeys(candidates, 0.0), {}, {}, {}
    undergone = {candidate: [] for candidate in candidates}
    for test in tests:
        for candidate in candidates:
            if (test, candidate) not in values:
                continue
            replicates = values[test, candidate]
            undergone[candidate].append(math.fsum(replicates) / len(replicates))
            score = math.fsum(undergone[candidate]) / len(undergone[candidate])
            changes[test, candidate] = score - scores[candidate]
            scores[candidate] = score
            if candidate not in entries and score > 0:
                entries[candidate], admitted[candidate] = score, tests.index(test)
    differentials = [{'test': test, 'pair': [first, second],
                      'value': abs(changes[test, first] - changes[test, second])}
                     for position, test in enumerate(tests) for first, second in combinations(sorted(entries), 2)
                     if (test, first) in changes and (test, second) in changes
                     and position > max(admitted[first], admitted[second])]
    return {'scores': {candidate: scores[candidate] for candidate in sorted(entries)}, 'entries': entries,
            'differentials': differentials,
            'credit': math.fsum(entries.values()) + math.fsum(row['value'] for row in differentials)}
