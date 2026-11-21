"""Differential credit over candidate annotations (the owner's formula of 2026-11-20).

"The graders should additively add to the subscoring sheets and then the subscoring sheets additively add to the score"
(the owner, 2026-11-21).

THE SCORING SHEET'S WEIGHTS (the owner, 2026-11-21: the scoring sheet weighs the subscoring sheets into the score with stated weights, so each
sheet's typical strong result counts comparably). ``SHEET_WEIGHT[family]`` multiplies every value of a test of that family (the part of the
test name before its first ``:``); a candidate's value in a test, its sheet value, its score, its entry and every differential are in these
weighted units. The weight of a family is ONE OVER ITS TYPICAL STRONG VALUE (``TYPICAL_STRONG_VALUE``), so the typical strong result of each
sheet is worth about 1; the derivation is beside the constants.

A measurement is one graded result: the test it belongs to (the same tool, settings and region of the target), the
candidate annotation its reference stands for, and its value on the subscoring sheet (0 to 1). Measurements are
given in the order they arrived. The tests are ordered by their first measurement.

- A candidate's value in one test is the mean of its measurements in that test (its replicates in that test), in
  [0, 1] (the alignment's value, a count of new conserved sites x a weight, is not capped at 1: see
  ``candidate_measurements``).
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
file or a model.

ONE CREDIT FOR ONE DATASET (the owner, 2026-11-21: "You only can earn one credit for one dataset - you can improve a clustering
to earn more, but you cannot replicate"). A measurement may name its ``dataset`` (a graded clustering names the graded search its
sequences are drawn from). Each test of a dataset is computed as a test at its own place in the order, its entries and
differentials exactly as above; its TEST CREDIT is the sum of the entries it admitted and of its differentials. All the tests of
one dataset together earn the MAXIMUM of their test credits: a later test of the dataset earns only the amount by which it beats
the best so far (an improvement), a replicate earns 0, and the credit never falls. A candidate's value on the sheet from one
dataset reads the same maximum: its largest value over the dataset's tests (not their sum), so a replicate adds nothing to a
score either. A test that names no dataset counts as before."""
import math
from itertools import combinations


# The typical strong value of each sheet's family: the value, in ONE test of that family, of the candidate that leads a stored real run
# (direct read, 2026-11-21, of the stored head records of runs a101_conserved_ws_C2, a101_diff_ws_H1 and a101_final_ws_cspa, all of E.
# coli CspA, 70 residues, one BV-BRC bacteria-archaea blastp search; the unweighted values; the other stored runs, a101_msa_ws_M1/M2 and
# a101_returns_ws_R1, hold the same search and scan and an older alignment sheet that the present reading does not take):
#   database_search  0.9592726552144761  the CspA product's mean hit value in the search (the same in all three runs; the other products
#                                        are 0.81 to 0.84)
#   profile_scan     0.8198338046876612  the cold-shock-domain family's value in the Pfam hmmscan (the same in all three runs)
#   msa              12 / 7              the CspA product's value in the first alignment (12 new matched distinguishing sites x W = 1/7;
#                                        later alignments of the same target add 0.0 to 0.29 because a site counts once)
#   cluster          1.0                 the CspA product's share of its sequences in the target's cluster in the committed clustering of
#                                        the C2 set (MCL, inflation 4.0, rescaled contrast: CspA 10/10, CspB/CspG/CspI 10/10, CspC 0/9)
#   pairwise         1.0                 no stored run holds a pairwise value: the weight is 1 until one does
# The data is one target: re-derive these as runs of other targets accumulate.
TYPICAL_STRONG_VALUE = {'database_search': 0.9592726552144761, 'profile_scan': 0.8198338046876612, 'msa': 12 / 7, 'cluster': 1.0,
                        'pairwise': 1.0}
SHEET_WEIGHT = {family: 1 / value for family, value in TYPICAL_STRONG_VALUE.items()}


def sheet_weight(test):
    """The weight of the family of ``test`` (the part of its name before the first ``:`` or ``@``)."""
    return SHEET_WEIGHT[test.split('@', 1)[0].split(':', 1)[0]]


def _kind(test):
    """The subscoring sheet of a test: its kind, the part of the name before ``@``."""
    return test.split('@', 1)[0]


def _datasets(measurements):
    """``{test: dataset}`` for the tests whose measurements name a dataset."""
    return {row['test']: row['dataset'] for row in measurements if row.get('dataset') is not None}


def _sheet_value(held):
    """A candidate's value on one sheet from its weighted test values ``[(dataset or None, value)]``: the sum of the values of
    tests of no dataset plus, per dataset, its largest value over that dataset's tests."""
    best = {}
    for dataset, value in held:
        if dataset is not None:
            best[dataset] = max(best.get(dataset, value), value)
    return math.fsum([value for dataset, value in held if dataset is None] + list(best.values()))


def differential_credit(measurements):
    """The scores, the sheets and the credit of ``measurements`` (``[{'test', 'candidate', 'value'}]``, each optionally
    with its ``dataset``, in arrival order). Also ``test_credits`` (each test's entries plus differentials) and ``datasets``
    (per dataset: its ``best`` test credit so far, the ``best_test`` and the credit each of its tests ``earned``)."""
    tests, values = [], {}
    dataset_of = _datasets(measurements)
    for row in measurements:
        if row['test'] not in tests:
            tests.append(row['test'])
        values.setdefault((row['test'], row['candidate']), []).append(row['value'])
    candidates = sorted({candidate for _, candidate in values})
    sheets = {candidate: {} for candidate in candidates}
    changes, entries, admitted = {}, {}, {}

    def score(candidate):
        return math.fsum(_sheet_value(held) for held in sheets[candidate].values())
    for test in tests:
        for candidate in candidates:
            if (test, candidate) not in values:
                continue
            replicates = values[test, candidate]
            value = sheet_weight(test) * math.fsum(replicates) / len(replicates)
            sheets[candidate].setdefault(_kind(test), []).append((dataset_of.get(test), value))
            changes[test, candidate] = value
            if candidate not in entries and value > 0:
                entries[candidate], admitted[candidate] = score(candidate), tests.index(test)
    differentials = [{'test': test, 'pair': [first, second],
                      'value': abs(changes[test, first] - changes[test, second])}
                     for position, test in enumerate(tests) for first, second in combinations(sorted(entries), 2)
                     if (test, first) in changes and (test, second) in changes
                     and position > max(admitted[first], admitted[second])]
    test_credits = {test: math.fsum([entries[candidate] for candidate in entries if tests[admitted[candidate]] == test]
                                    + [row['value'] for row in differentials if row['test'] == test]) for test in tests}
    datasets = {}
    for test in tests:
        if test in dataset_of:
            held = datasets.setdefault(dataset_of[test], {'best': 0.0, 'best_test': None, 'earned': {}})
            held['earned'][test] = max(0.0, test_credits[test] - held['best'])
            if held['best_test'] is None or test_credits[test] > held['best']:
                held['best'], held['best_test'] = test_credits[test], test
    return {'scores': {candidate: score(candidate) for candidate in sorted(entries)},
            'sheets': {candidate: {kind: _sheet_value(held) for kind, held in sheets[candidate].items()}
                       for candidate in sorted(entries)},
            'entries': entries, 'differentials': differentials, 'test_credits': test_credits, 'datasets': datasets,
            'credit': math.fsum([credit for test, credit in test_credits.items() if test not in dataset_of]
                                + [held['best'] for held in datasets.values()])}


def standing(measurements):
    """Where each candidate stands before a further test: ``{candidate: {'sheets', 'score', 'listed'}}`` for every
    candidate measured so far (listed or not): its value on each sheet (the sum of its values in the tests of that kind),
    its score (the sum of its sheet values) and whether it is on the list (its score is above zero; values are never
    below zero). A sheet value from the tests of one dataset is the largest of them (``_sheet_value``)."""
    held, dataset_of = {}, _datasets(measurements)
    for row_test, row_candidate in dict.fromkeys((row['test'], row['candidate']) for row in measurements):
        replicates = [row['value'] for row in measurements
                      if row['test'] == row_test and row['candidate'] == row_candidate]
        held.setdefault(row_candidate, {}).setdefault(_kind(row_test), []).append(
            (dataset_of.get(row_test), sheet_weight(row_test) * math.fsum(replicates) / len(replicates)))
    sheets = {candidate: {kind: _sheet_value(values) for kind, values in kinds.items()}
              for candidate, kinds in held.items()}
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


def dataset_test_ceiling(bound, best):
    """The most one further test of a dataset can add to the credit, given ``bound``, the most that test's own credit (its
    entries plus its differentials) can be (``test_ceiling``), and ``best``, the largest test credit of the dataset's tests held
    so far (``differential_credit(...)['datasets'][dataset]['best']``, 0 with none): ``max(0, bound - best)``.

    Proof. The dataset contributes the largest test credit of its tests to the credit, and nothing else of the credit changes
    when a test is appended (earlier entries and differentials are fixed; the new test's entries and differentials are its own
    test credit). So the credit rises by ``max(0, T - best)`` where ``T`` is the new test's credit, and ``T <= bound``."""
    return max(0.0, bound - best)


def msa_test_ceiling(held, maxima, measurable):
    """The most one further alignment can add to the credit of one target, from where the list and the identified sites
    stand: a PROVED maximum, not a forecast.

    ``held`` is ``standing`` of the target; ``measurable`` lists the candidates (identifiers) the alignment can measure,
    each with at least ``MINIMUM_GROUP_SIZE`` sequences in it; ``maxima`` maps each of them to ``m_c``, the most its value
    can be in this alignment (``SITE_WEIGHT`` x ``room_c``, where ``room_c`` is the number of target positions whose
    matched site of ``c`` no held alignment identified: ``candidate_measurements.matched_positions_taken``).

    Proof sketch.

    1. An alignment's value for candidate ``c`` is ``W`` x (its NEW matched distinguishing sites). A matched site of
       ``c`` at target position ``p`` is a column where ``c``'s group conserves the TARGET's own residue ``t_p`` there, so
       its identity is (``p``, ``t_p``, ``c``) (``new_site_values``); it is new only if that identity is unseen, and every
       column the target occupies is exactly one position. So the count is at most ``room_c`` = ``L`` minus the positions
       whose (``p``, ``t_p``, ``c``) is seen, whatever the alignment's columns, groups or sequences are. (A position seen
       earlier with ANOTHER conserved residue stays open: a different group context can move the columns, so the old rule
       "every position identified at all is closed" was not a proved bound.) Hence ``0 <= v_c <= m_c = W room_c``.
    2. The credit adds, for this last test, the entries of the candidates it admits (not yet listed: ``v_c``, at most
       ``m_c``; a pair with an admitted candidate earns nothing in the test that admits it) and, for each pair of listed
       candidates both measured, ``|v_a - v_b|`` (``differential_credit``). A candidate with no new site is not measured
       (it earns nothing and makes no pair), which only lowers the sum, so ``v_c = 0`` is allowed.
    3. The rise ``R(v)`` is the sum of ``v_c`` over the unlisted candidates plus ``|v_a - v_b|`` over the listed pairs: a
       convex function of ``v`` (sum of norms and linear terms) on the box ``0 <= v_c <= m_c``, so it is largest at a vertex,
       ``v_c`` equal to 0 or to ``m_c``. For a set ``S`` of listed candidates at ``m`` and the other listed at 0 it is
       ``sum_{a<b in S} |m_a - m_b| + sum_{a in S, b not in S} m_a`` (plus the ``m_c`` of the unlisted candidates, always
       at ``m_c``). The bound is the largest over the sets ``S`` (all of them when 16 or fewer listed candidates are
       measured, else the looser ``sum over pairs of max(m_a, m_b)``, which is never below it).
    4. A candidate with fewer than ``MINIMUM_GROUP_SIZE`` sequences has no conserved site and is no partner, and a site
       needs two groups, so fewer than two eligible candidates, or an alignment that repeats a held one exactly (the same
       sequences in the same order: the same input, nothing new), earns 0. The caller passes only eligible candidates and
       decides the repeat (``credit.ceiling``).

    Not bounded further, and why: which columns the aligner gives a group depends on every other group in the alignment
    (removing or adding a group can move columns), so the positions of one group in a new alignment context are
    not fixed by its sequences; a count of residues or a share argument over the sequences would need the columns
    fixed. Those parts keep the open bound (every position not seen as a matched site of the candidate)."""
    return vertex_maximum(held, maxima, measurable)


def metacats_test_ceiling(held, maxima, measurable):
    """The most one further MetaCATS report of a named alignment can add to the credit of one target: a PROVED maximum.

    ``held`` is ``standing`` of the target; ``measurable`` lists the candidates (identifiers) of the alignment's groups;
    ``maxima`` maps each to ``m_c`` = (its matched conserved sites in that alignment, with a target position, that no held
    MetaCATS report confirmed: ``candidate_measurements.unconfirmed_matched_sites``) x ``SITE_WEIGHT`` x ``SHEET_WEIGHT['msa']``.

    Proof. The report's value for ``c`` is ``W`` x (its matched sites of that alignment whose column is significant and that no
    earlier report confirmed) (``confirmed_site_values``); a confirmed site is one of the alignment's matched sites of ``c``
    (fixed by the held alignment's sheet, whatever columns the service finds significant), and a site already confirmed is not
    counted, so the count is between 0 and the number of matched sites not yet confirmed; weighted by the msa sheet's weight,
    ``0 <= v_c <= m_c``. A candidate with ``m_c`` = 0 gets no measurement (it earns nothing and makes no pair). The report is
    one test appended last, so the credit rises by the entries of the candidates it admits (each ``v_c``) plus ``|v_a - v_b|``
    for each pair of listed candidates it measures (``differential_credit``; it is no dataset test, so nothing else changes).
    That rise is convex in ``v`` on the box ``0 <= v_c <= m_c``, so its maximum is at a vertex, the bound ``vertex_maximum``
    computes (the same as for an alignment: ``msa_test_ceiling`` step 3). A report of an alignment already analysed by a held
    report is refused by the request check (the reuse key), so its ceiling is 0; the caller decides that."""
    return vertex_maximum(held, maxima, measurable)


def vertex_maximum(held, maxima, measurable):
    """The largest rise of the credit over values ``0 <= v_c <= maxima[c]`` of the ``measurable`` candidates in one test appended
    last: the entries of the candidates not listed (each at its maximum) plus, over the sets ``S`` of listed candidates at their
    maximum (the others at 0), ``sum_{a<b in S} |m_a - m_b| + sum_{a in S, b not in S} m_a``; above 16 listed candidates the
    looser ``sum over pairs of max(m_a, m_b)``. The vertex argument is ``msa_test_ceiling``'s step 3."""
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
