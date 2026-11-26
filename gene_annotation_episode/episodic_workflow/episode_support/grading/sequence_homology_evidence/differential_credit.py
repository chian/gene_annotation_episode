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

- A candidate's value in one test is the largest of its measurements in that test (its replicates in that test: for a database search its top hit), in
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
- THE DIFFERENTIAL OF A TEST IS ONE PAIR'S (the owner, 2026-11-20: "(1) adding new possible annotations gets you a score (2)
  differentiating those scores (i.e., abs[S_A(t=i+1) - S_A(t=i)] vs abs[S_B(t=i+1) - S_B(t=1)] vs .... for all possibilities";
  "I mean that if S_A moves +0.5 and S_B only moves +0.1, then you have differentiated the lead candidates by 0.4"; 2026-11-21: "Do
  you not remember that you only do the differential between the top two candidates?"). Among the candidates already on the list
  BEFORE a test (admitted by an earlier test) that the test measures, take the TWO with the highest scores before the test (a tie is
  broken by the order of the candidate key); the test earns ``|d_A - d_B|`` for that pair, ``d_c`` being the change of ``S_c`` over
  the test (the candidate's weighted value in it), and NOTHING for any other pair. With fewer than two such candidates the test
  earns no differential. The test that admits a candidate earns that candidate's entry score only: its rise from nothing is not
  counted a second time as a differential.

``credit`` is the sum of the entry scores and of the differentials: it never falls. Nothing here reads a record, a
file or a model.

ONE CREDIT FOR ONE DATASET (the owner, 2026-11-21: "You only can earn one credit for one dataset - you can improve a clustering
to earn more, but you cannot replicate"). A measurement may name its ``dataset`` (a graded clustering names the graded search its
sequences are drawn from). Each test of a dataset is computed as a test at its own place in the order, its entries and
differentials exactly as above; its TEST CREDIT is the sum of the entries it admitted and of its differentials. All the tests of
one dataset together earn the MAXIMUM of their test credits: a later test of the dataset earns only the amount by which it beats
the best so far (an improvement), a replicate earns 0, and the credit never falls. A candidate's value on the sheet from one
dataset reads the same maximum: its largest value over the dataset's tests (not their sum), so a replicate adds nothing to a
score either. A test that names no dataset counts as before.

THE CLUSTER TEST WEIGHS ITS CREDIT BY THE EVIDENCE (the owner, 2026-11-21, on a second clustering that earned 0.90 almost entirely
by adding "hypothetical protein", one sequence, 0/1 in the target's cluster: "you need a better cluster metric the weights overall
evidence not just goodness of clusters ... more data is better and clusters with little data earn less"; approved rule "pair x
weaker side"). In a test of the ``cluster`` family a candidate's value stays its plain share of sequences in the target's cluster
(its sheet value and its score are unchanged), but the credit the test earns is weighed by how many sequences each candidate
has in the set: with ``n`` its sequences, its evidence is ``r(n) = n / (n + CLUSTER_PSEUDO_COUNT)`` (``cluster_evidence``). A
differential of two candidates is ``min(r_a, r_b) x |d_a - d_b|``: a pair is only as good as its weaker side. A candidate the
test admits (an entry) earns ``r(n) x`` its entry score: a candidate entering on thin data enters with less. Every other family
(search, scan, alignment, MetaCATS, pairwise) has evidence 1, so its rule is unchanged."""
import math

from gene_annotation_episode.episodic_workflow.episode_support.grading.similarity_search.hit_list_claim import (
    claim_value, taxa_share)


# The typical strong value of each sheet's family: the value, in ONE test of that family, of the candidate that leads a stored real run
# (direct read, 2026-11-21, of the stored head records of runs a101_conserved_ws_C2, a101_diff_ws_H1 and a101_final_ws_cspa, all of E.
# coli CspA, 70 residues, one BV-BRC bacteria-archaea blastp search; the unweighted values; the other stored runs, a101_msa_ws_M1/M2 and
# a101_returns_ws_R1, hold the same search and scan and an older alignment sheet that the present reading does not take):
#   database_search  0.9592726552144761  the CspA product's mean hit value in the search (the same in all three runs; the other products
#                                        are 0.81 to 0.84)
#   profile_scan     0.8198338046876612  the cold-shock-domain family's value in the Pfam hmmscan (the same in all three runs)
#   msa              12 / 7              the CspA product's value in the first alignment (12 new matched distinguishing sites x W = 1/7;
#                                        later alignments of the same target add 0.0 to 0.29 because a site counts once)
#   cluster          1.0                 the leading candidate's (the CspA product's) share of its sequences in the target's cluster,
#                                        the median over the 21 committed clusterings of the stored real runs (direct read, 2026-11-21,
#                                        of the all_vs_all sources of runs a101_goal3_ws_cspa to a101_goal10_ws_cspa; the RecA runs hold
#                                        none): 1.0 in 15 (18/18 in 12, 10/10 in 2, 17/17 in 1), 15/18 = 0.8333 in 6 (goal5 once,
#                                        goal9 three times, goal10 twice). The value stays the plain share under the evidence weighting
#                                        of the cluster credit (below), so the typical strong value is unchanged: 1.0
#   pairwise         1.0                 no stored run holds a pairwise value: the weight is 1 until one does
# The data is one target: re-derive these as runs of other targets accumulate.
TYPICAL_STRONG_VALUE = {'database_search': 0.9592726552144761, 'profile_scan': 0.8198338046876612, 'msa': 12 / 7, 'cluster': 1.0,
                        'pairwise': 1.0}
SHEET_WEIGHT = {family: 1 / value for family, value in TYPICAL_STRONG_VALUE.items()}
# The pseudo-count of the cluster test's evidence ``r(n) = n / (n + c)`` (``cluster_evidence``), c = 4: a candidate with one
# sequence in the set weighs 0.2, one with 4 weighs 0.5, one with 18 (a strong candidate at 20 sequences per candidate: the CspA
# product of the stored runs) weighs 0.82. A candidate with few sequences can therefore earn little whatever its share, and one with
# many can earn nearly its whole share: "more data is better and clusters with little data earn less" (the owner).
CLUSTER_PSEUDO_COUNT = 4


def cluster_evidence(size):
    """The evidence ``r(n) = n / (n + CLUSTER_PSEUDO_COUNT)`` of a candidate with ``size`` = n sequences in a clustered set."""
    return size / (size + CLUSTER_PSEUDO_COUNT)


def _evidence(row):
    """The evidence a measurement carries: ``cluster_evidence`` of its ``size`` for a test of the ``cluster`` family, else 1."""
    if row['test'].split('@', 1)[0].split(':', 1)[0] == 'cluster':
        return cluster_evidence(row['size'])
    return 1.0


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


def lead_pair(scores):
    """The top two of ``scores`` (``{candidate: score}``): the two with the highest scores, a tie broken by the order of the candidate
    key; ``None`` with fewer than two."""
    if len(scores) < 2:
        return None
    first, second = sorted(scores, key=lambda candidate: (-scores[candidate], candidate))[:2]
    return first, second


def test_value(rows, candidate):
    """The candidate's value in one test, from the test's measurements ``rows``. A ranked hit list (measurements with a
    ``rank``: a database search) gives the value of the claim the list makes for the candidate
    (``hit_list_claim.claim_value``): its top hit's value, the run of its hits before the first later hit of another
    candidate, and the taxa of that run. Any other test gives the largest of the candidate's measurements."""
    own = sorted((row for row in rows if row['candidate'] == candidate), key=lambda row: row.get('rank', 0))
    if 'rank' not in own[0]:
        return max(row['value'] for row in own)
    other = [row['rank'] for row in rows if row['candidate'] != candidate and row['rank'] > own[0]['rank']]
    block = [row for row in own if not other or row['rank'] < min(other)]
    return claim_value(own[0]['value'], len({row['rank'] for row in block}), taxa_share([row['taxon_id'] for row in block]))


def differential_credit(measurements):
    """The scores, the sheets and the credit of ``measurements`` (``[{'test', 'candidate', 'value'}]``, each optionally
    with its ``dataset``, in arrival order; a measurement of a ``cluster`` test also has its ``size``). Also ``test_credits``
    (each test's entries, each times the evidence of the admitting measurement, plus its differential, times the weaker
    evidence of its pair: ``_evidence``) and ``datasets`` (per dataset: its ``best`` test credit so far, the ``best_test`` and the
    credit each of its tests ``earned``). A test has at most one differential row: its ``pair`` (the top two of the candidates
    listed before it that it measured, the higher score first), the credit it earned (``value``), the ``difference`` of the
    two ``moves`` and the pair's ``evidence``."""
    tests, values, evidence = [], {}, {}
    dataset_of = _datasets(measurements)
    for row in measurements:
        if row['test'] not in tests:
            tests.append(row['test'])
        values.setdefault((row['test'], row['candidate']), []).append(row['value'])
        known = evidence.setdefault((row['test'], row['candidate']), _evidence(row))
        if known != _evidence(row):
            raise ValueError('replicates_of_a_candidate_differ_in_evidence:' + row['test'])
    candidates = sorted({candidate for _, candidate in values})
    sheets = {candidate: {} for candidate in candidates}
    entries, admitted, differentials = {}, {}, []

    def score(candidate):
        return math.fsum(_sheet_value(held) for held in sheets[candidate].values())
    for position, test in enumerate(tests):
        measured = [candidate for candidate in candidates if (test, candidate) in values]
        changes = {candidate: sheet_weight(test) * test_value([row for row in measurements if row['test'] == test], candidate)
                   for candidate in measured}
        pair = lead_pair({candidate: score(candidate) for candidate in measured if candidate in entries})
        if pair is not None:
            first, second = pair
            difference = abs(changes[first] - changes[second])
            weaker = min(evidence[test, first], evidence[test, second])
            differentials.append({'test': test, 'pair': [first, second], 'value': weaker * difference,
                                  'difference': difference, 'evidence': weaker,
                                  'moves': [changes[first], changes[second]]})
        for candidate in measured:
            sheets[candidate].setdefault(_kind(test), []).append((dataset_of.get(test), changes[candidate]))
            if candidate not in entries and changes[candidate] > 0:
                entries[candidate], admitted[candidate] = score(candidate), position
    test_credits = {test: math.fsum([evidence[test, candidate] * entries[candidate] for candidate in entries
                                     if tests[admitted[candidate]] == test]
                                    + [row['value'] for row in differentials if row['test'] == test]) for test in tests}
    datasets = {}
    for test in tests:
        if test in dataset_of:
            held = datasets.setdefault(dataset_of[test], {'best': 0.0, 'best_test': None, 'earned': {}})
            held['earned'][test] = max(0.0, test_credits[test] - held['best'])
            if held['best_test'] is None or test_credits[test] > held['best']:
                held['best'], held['best_test'] = test_credits[test], test
    entry_credits = {test: math.fsum(evidence[test, candidate] * entries[candidate] for candidate in entries
                                     if tests[admitted[candidate]] == test) for test in tests}
    return {'scores': {candidate: score(candidate) for candidate in sorted(entries)},
            'sheets': {candidate: {kind: _sheet_value(held) for kind, held in sheets[candidate].items()}
                       for candidate in sorted(entries)},
            'entries': entries, 'entry_credits': entry_credits, 'differentials': differentials,
            'test_credits': test_credits, 'datasets': datasets,
            'credit': math.fsum([credit for test, credit in test_credits.items() if test not in dataset_of]
                                + [held['best'] for held in datasets.values()])}


GROUP_PREFIX = 'group:'


def group_key(members):
    """The candidate key of a group of candidates (their own keys): the same whatever the order they are given in."""
    return GROUP_PREFIX + '|'.join(sorted(members))


def regrouped(measurements, groups):
    """The measurements read under a grouping (the owner, 2026-11-23: "regrouping AUTOMATICALLY merges and rescores
    annotation scorings"; the design ``docs/plan/designs/a102_regrouping.md``). ``groups`` is a list of groups, each a
    list of candidate keys; a candidate in no group is read as before. The records stay as observed: only the candidate a
    measurement is read as changes, to its group's key (``group_key``). The measurements of the members of one group in
    one test are then that one candidate's replicates, so its value in the test is their largest: for a database search,
    whose measurements are the hits, exactly the value the test would have given under one name. A ``cluster`` test gives
    one measurement per candidate (its share of its sequences in the target's cluster, with its ``size``), so the members
    of a group are joined into one measurement there: the group's share over all its sequences (the sum of
    ``in_target_cluster`` over the sum of ``size``), with the summed size as its evidence, again as one name would have
    measured."""
    key_of = {member: group_key(group) for group in groups for member in group}
    rows, joined = [], {}
    for row in measurements:
        if row['candidate'] not in key_of:
            rows.append(row)
        elif row['test'].split('@', 1)[0].split(':', 1)[0] == 'cluster':
            held = joined.get((row['test'], key_of[row['candidate']]))
            if held is None:
                held = joined[row['test'], key_of[row['candidate']]] = {**row, 'candidate': key_of[row['candidate']]}
                rows.append(held)
            else:
                held['size'] += row['size']
                held['in_target_cluster'] += row['in_target_cluster']
            held['value'] = held['in_target_cluster'] / held['size']
        else:
            rows.append({**row, 'candidate': key_of[row['candidate']]})
    return rows


def credit_under(measurements, groups):
    """The credit of ``measurements`` with each test's differential taken under the grouping ``groups`` and each test's
    entries taken as found: the entry of a candidate is paid once, by its name as found, and does not change with a
    grouping; the differential of a test is that of the two leading candidates of the table read under the grouping.
    A test's credit is the sum of the two, and the tests add up as in ``differential_credit`` (the tests of one dataset
    together earn the largest of their test credits). With no group it is ``differential_credit(measurements)['credit']``.

    For a fixed grouping it never falls as measurements are added: a held test's entries and its differential depend
    only on the tests before it, so every term is fixed once computed, the terms are never negative, and a dataset's
    largest test credit can only rise."""
    found = differential_credit(measurements)
    if not groups:
        return found['credit']
    grouped = differential_credit(regrouped(measurements, groups))
    dataset_of = _datasets(measurements)
    test_credits = {test: math.fsum([found['entry_credits'][test]]
                                    + [row['value'] for row in grouped['differentials'] if row['test'] == test])
                    for test in found['test_credits']}
    best = {}
    for test, credit in test_credits.items():
        if test in dataset_of:
            best[dataset_of[test]] = max(best.get(dataset_of[test], 0.0), credit)
    return math.fsum([credit for test, credit in test_credits.items() if test not in dataset_of] + list(best.values()))


def grouped_credit(measurements, groupings):
    """The credit of ``measurements`` given the groupings the episode holds (each a list of groups): the HIGHEST
    ``credit_under`` over them, no grouping being one of them (the owner, 2026-11-23: "improving that honesty should earn
    credit"; "flipping back and forth without new evidence should be net neutral"). A grouping that makes the two leading
    candidates two different functions gives real differentials and raises it; a grouping already held, or one that is
    no better, adds nothing; it never falls, because each ``credit_under`` never falls and a grouping, once held, stays
    held. With no grouping held it is the credit as before."""
    return max([credit_under(measurements, ())] + [credit_under(measurements, groups) for groups in groupings])


def standing(measurements):
    """Where each candidate stands before a further test: ``{candidate: {'sheets', 'score', 'listed'}}`` for every
    candidate measured so far (listed or not): its value on each sheet (the sum of its values in the tests of that kind),
    its score (the sum of its sheet values) and whether it is on the list (its score is above zero; values are never
    below zero). A sheet value from the tests of one dataset is the largest of them (``_sheet_value``)."""
    held, dataset_of = {}, _datasets(measurements)
    for row_test, row_candidate in dict.fromkeys((row['test'], row['candidate']) for row in measurements):
        held.setdefault(row_candidate, {}).setdefault(_kind(row_test), []).append(
            (dataset_of.get(row_test), sheet_weight(row_test) * test_value(
                [row for row in measurements if row['test'] == row_test], row_candidate)))
    sheets = {candidate: {kind: _sheet_value(values) for kind, values in kinds.items()}
              for candidate, kinds in held.items()}
    return {candidate: {'sheets': kinds, 'score': math.fsum(kinds.values()), 'listed': math.fsum(kinds.values()) > 0}
            for candidate, kinds in sheets.items()}


def test_ceiling(held, measurable, family, unseen=0, limit=None):
    """The most one further test can add to the credit of one target, from where the list stands: a PROVED maximum.

    ``held`` is ``standing`` of the target. The test measures candidates of ``measurable`` (identifiers, each possibly
    not yet held) and up to ``unseen`` others never met, at most ``limit`` candidates in all when ``limit`` is given.

    Proof. Scores are additive and a candidate's value in a test of ``family`` is in [0, w], ``w`` = ``SHEET_WEIGHT[family]`` (the raw
    value is in [0, 1]), so the test moves a score by its value, between 0 and ``w``. The test is the last one, so it earns:

    * for each candidate not on the list that it admits, the entry score (its first score), at most ``w``;
    * ONE differential, the absolute difference of the moves of the top two of the listed candidates it measures, which are two
      numbers in [0, w]: at most ``w``, and only when at least two listed candidates are measured (the test that admits a candidate
      earns that candidate's entry only, and no other pair earns anything);
    * nothing else.

    With ``m`` listed candidates measured (``count`` of them are named) and ``new`` others new, the bound is ``w`` x ((1 if
    ``m`` >= 2) + the new ones admitted); with a ``limit`` of ``k`` the new ones number at most ``k - m``, and the bound is the
    largest of that over ``m`` from 0 to ``min(k, count)``. Tight: the top two at ``w`` and 0, every new candidate at ``w``."""
    weight = SHEET_WEIGHT[family]
    listed = {candidate for candidate, state in held.items() if state['listed']}
    count = len({candidate for candidate in measurable if candidate in listed})
    new = len({candidate for candidate in measurable if candidate not in listed}) + unseen
    if limit is None:
        return weight * float((1 if count >= 2 else 0) + new)
    return weight * float(max((1 if m >= 2 else 0) + min(limit - m, new) for m in range(min(limit, count) + 1)))


def dataset_test_ceiling(bound, best):
    """The most one further test of a dataset can add to the credit, given ``bound``, the most that test's own credit (its
    entries plus its differential) can be (for a clustering, ``cluster_test_bound``), and ``best``, the largest test credit of the dataset's tests held
    so far (``differential_credit(...)['datasets'][dataset]['best']``, 0 with none): ``max(0, bound - best)``.

    Proof. The dataset contributes the largest test credit of its tests to the credit, and nothing else of the credit changes
    when a test is appended (earlier entries and differentials are fixed; the new test's entries and differential are its own
    test credit). So the credit rises by ``max(0, T - best)`` where ``T`` is the new test's credit, and ``T <= bound``."""
    return max(0.0, bound - best)


def cluster_test_bound(held, sizes):
    """The most the credit of ONE cluster test can be, ``B``, over the candidates of ``sizes`` (candidate -> sequences in the planned
    set), from where the list stands (``held``, ``standing`` of the target): ``w (sum of r_c over the unlisted candidates measured +
    min(r_a, r_b) of the top two listed candidates measured)``; the second term only with two listed candidates measured. See
    ``cluster_test_ceiling``."""
    weight = SHEET_WEIGHT['cluster']
    measured = {candidate: cluster_evidence(size) for candidate, size in sizes.items() if size > 0}
    listed = {candidate: held[candidate]['score'] for candidate in measured if held.get(candidate, {}).get('listed')}
    new = math.fsum(r for candidate, r in measured.items() if candidate not in listed)
    pair = lead_pair(listed)
    return weight * (new + (0.0 if pair is None else min(measured[pair[0]], measured[pair[1]])))


def cluster_test_ceiling(held, sizes, best):
    """The most one further graded clustering of a dataset can add to the credit of one target: a PROVED, TIGHT maximum.

    ``held`` is ``standing`` of the target; ``sizes`` maps each candidate (identifier) the clustering's set has a group of
    sequences for to ``n_c``, its number of sequences in the planned set (the commission's plan is deterministic:
    ``bvbrc_msa_alignment.plan_rows``; a candidate with none gives no measurement and is left out); ``best`` is the dataset's
    largest test credit so far (``differential_credit(...)['datasets'][dataset]['best']``, 0 with none). With ``w`` =
    ``SHEET_WEIGHT['cluster']`` and ``r_c = cluster_evidence(n_c)``, the ceiling is ``max(0, B - best)`` with ``B = w (sum of
    r_c over the unlisted candidates + min(r_a, r_b))``, ``a`` and ``b`` the top two of the listed candidates (the highest scores in
    ``held``, a tie by candidate key); the pair term is absent with fewer than two listed candidates.

    Proof.

    1. The test measures each candidate group once: its value is ``w`` x the share of the group's sequences in the target's
       cluster, so ``0 <= v_c <= w`` (``cluster_sheet.group_values``; a group with share 0 is still measured), and its evidence is
       ``r_c``, fixed by the plan (``_evidence``). Nothing else is measured: the set holds only the target and the named
       candidates' sequences. So the listed candidates the test measures are the listed ones with a group, and which two of them
       are the top two is fixed by ``held`` (their scores before the test).
    2. Appended last, the test's own credit ``T`` is ``r_c v_c`` for each candidate it admits (unlisted: no earlier value above 0,
       so its entry score is its sheet value from the dataset, the largest over the dataset's tests, which is ``v_c``), plus
       ONE differential ``min(r_a, r_b) |v_a - v_b|`` for the top two listed (``differential_credit``). ``r_c v_c <= r_c w`` and
       ``|v_a - v_b| <= w``, so ``T <= B``.
    3. The dataset earns the largest test credit of its tests and nothing else of the credit changes when its test is appended
       (``dataset_test_ceiling``), so the credit rises by ``max(0, T - best) <= max(0, B - best)``.
    4. Tight: each group has at least one sequence, so a share of 0 and a share of 1 are both outcomes the clustering can give; the
       partition that puts every unlisted group and the group of ``a`` in the target's cluster and the group of ``b`` outside it
       (the other groups anywhere) gives exactly ``T = B``.

    Not bounded further, and why: which partition MCL gives depends on the sequences and on the tuning the child's model chooses
    after the commission, so no partition is excluded before the clustering runs."""
    return dataset_test_ceiling(cluster_test_bound(held, sizes), best)


def _new_and_pair_room(held, maxima, measurable):
    """The largest rise of the credit over values ``0 <= v_c <= maxima[c]`` of the ``measurable`` candidates in one test appended
    last: the entries of the candidates not listed (each at its maximum) plus one differential, the difference of the moves of the
    top two listed candidates measured, at most the larger of their maxima; which listed candidates are measured is the test's
    outcome (one with no value to find is not measured), so any two listed candidates can be the top two measured, and the
    bound is the largest maximum among the listed ones when there are at least two of them."""
    measured = [candidate for candidate in dict.fromkeys(measurable) if maxima[candidate] > 0]
    listed = [maxima[candidate] for candidate in measured if held.get(candidate, {}).get('listed')]
    new = math.fsum(maxima[candidate] for candidate in measured if not held.get(candidate, {}).get('listed'))
    return new + (max(listed) if len(listed) >= 2 else 0.0)


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
       ``m_c``) and ONE differential: ``|v_a - v_b|`` for the top two (highest score before the test) of the listed candidates
       it measures (``differential_credit``). A candidate with no new site is not measured (it earns nothing and is no partner),
       so which listed candidates are measured, and so which two are the top two, is the outcome of the alignment.
    3. Whatever the outcome, the two moves are in [0, ``m``] of their candidates, so the differential is at most the larger of the
       two ``m``, hence at most the largest ``m_c`` among the listed candidates; and it needs two listed candidates measured. So the
       rise is at most the sum of ``m_c`` over the unlisted candidates plus, with at least two listed candidates eligible, the
       largest ``m_c`` among the listed ones (``_new_and_pair_room``). It is a bound, not tight to the last site: the partner is
       measured with a value of at least one site.
    4. A candidate with fewer than ``MINIMUM_GROUP_SIZE`` sequences has no conserved site and is no partner, and a site
       needs two groups, so fewer than two eligible candidates, or an alignment that repeats a held one exactly (the same
       sequences in the same order: the same input, nothing new), earns 0. The caller passes only eligible candidates and
       decides the repeat (``credit.ceiling``).

    Not bounded further, and why: which columns the aligner gives a group depends on every other group in the alignment
    (removing or adding a group can move columns), so the positions of one group in a new alignment context are
    not fixed by its sequences; a count of residues or a share argument over the sequences would need the columns
    fixed. Those parts keep the open bound (every position not seen as a matched site of the candidate)."""
    return _new_and_pair_room(held, maxima, measurable)


def metacats_test_ceiling(held, maxima, measurable):
    """The most one further MetaCATS report of a named alignment can add to the credit of one target: a PROVED maximum.

    ``held`` is ``standing`` of the target; ``measurable`` lists the candidates (identifiers) of the alignment's groups;
    ``maxima`` maps each to ``m_c`` = (its matched conserved sites in that alignment, with a target position, that no held
    MetaCATS report confirmed: ``candidate_measurements.unconfirmed_matched_sites``) x ``SITE_WEIGHT`` x ``SHEET_WEIGHT['msa']``.

    Proof. The report's value for ``c`` is ``W`` x (its matched sites of that alignment whose column is significant and that no
    earlier report confirmed) (``confirmed_site_values``); a confirmed site is one of the alignment's matched sites of ``c``
    (fixed by the held alignment's sheet, whatever columns the service finds significant), and a site already confirmed is not
    counted, so the count is between 0 and the number of matched sites not yet confirmed; weighted by the msa sheet's weight,
    ``0 <= v_c <= m_c``. A candidate with ``m_c`` = 0 gets no measurement (it earns nothing and is no partner). The report is
    one test appended last, so the credit rises by the entries of the candidates it admits (each ``v_c``) plus ONE differential,
    ``|v_a - v_b|`` of the top two listed candidates it measures (``differential_credit``; it is no dataset test, so nothing
    else changes). Which listed candidates are measured is the report's outcome, so the differential is at most the largest
    ``m_c`` among the listed candidates, with at least two of them measurable: the bound ``_new_and_pair_room`` computes (the
    same as for an alignment: ``msa_test_ceiling`` step 3). A report of an alignment already analysed by a held report is
    refused by the request check (the reuse key), so its ceiling is 0; the caller decides that."""
    return _new_and_pair_room(held, maxima, measurable)
