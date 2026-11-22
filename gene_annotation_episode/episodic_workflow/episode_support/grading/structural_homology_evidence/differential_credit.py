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
  value (the mean E = B F of the hits with sites) in [0, 1] as well; the third, ``bound_partner`` (the mean E(hit, partner) = B F
  of the hits bound to a partner), likewise in [0, 1]; the fourth, ``ligand_transplant`` (the value of a ligand's best AlphaFill transplant, fit x no_clash), in (0, 1].
- A subscoring sheet is a kind of test: the part of the test name before ``@``
  (``structure_search:foldseek:tmalign:<database>``). A candidate's value on a sheet is the SUM of its values in the tests of
  that kind.
- The score ``S_c`` of a candidate is the SUM of its sheet values, which is the sum of its values over all the tests it has
  undergone so far. A test therefore moves the score by exactly the candidate's value in it, never below zero.
- A candidate is a possibility only on positive evidence: it is admitted with its first value above zero and earns its score
  after the test that admitted it. A candidate that never scored above zero is not on the list and earns nothing.
- THE DIFFERENTIAL OF A TEST IS ONE PAIR'S (the owner, 2026-11-20: "if S_A moves +0.5 and S_B only moves +0.1, then you have
  differentiated the lead candidates by 0.4"; 2026-11-21: "Do you not remember that you only do the differential between the top two
  candidates?"; "Okay keep the top two"; A101 has the same rule). Among the candidates already on the list BEFORE a test (admitted by an
  earlier test) that the test measures, whatever their kind (``product:``, ``ligand:``, ``nucleic_acid:``; a test measures candidates
  of its own kind), take the TWO with the highest scores before the test (a tie is broken by the order of the candidate key); the test
  earns ``|d_A - d_B|`` for that pair, ``d_c`` being the change of ``S_c`` over the test (the candidate's weighted value in it), and
  NOTHING for any other pair. With fewer than two such candidates the test earns no differential. The test that admits a candidate
  earns that candidate's entry score only: its rise from nothing is not counted a second time as a differential.

``credit`` is the sum of the entry scores and of the differentials: it never falls. Nothing here reads a record, a file or a
model. A102 has no dataset rule and no evidence weighting in round 1 (those are A101's, for its clustering test)."""
import math

from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence.ligand_transplants_sheet import (
    ELIGIBLE_COMPOUNDS)


# The typical strong value of each sheet's family: the value, in ONE test of the family, of the candidate that leads stored real
# runs (the derivation is written here when there is one).
# no real run yet: 1 until real runs give the family's typical strong value (SOP Step 6)
TYPICAL_STRONG_VALUE = {'structure_search': 1.0,
                        # no real run yet: 1 until real runs give the family's typical strong value (SOP Step 6)
                        'site_correspondence': 1.0,
                        # no real run yet: 1 until real runs give the family's typical strong value (SOP Step 6)
                        'bound_partner': 1.0,
                        # no real run yet: 1 until real runs give the family's typical strong value (SOP Step 6)
                        'ligand_transplant': 1.0}
SHEET_WEIGHT = {family: 1 / value for family, value in TYPICAL_STRONG_VALUE.items()}


def sheet_weight(test):
    """The weight of the family of ``test`` (the part of its name before the first ``:`` or ``@``)."""
    return SHEET_WEIGHT[test.split('@', 1)[0].split(':', 1)[0]]


def _kind(test):
    """The subscoring sheet of a test: its kind, the part of the name before ``@``."""
    return test.split('@', 1)[0]


def lead_pair(scores):
    """The top two of ``scores`` (``{candidate: score}``): the two with the highest scores, a tie broken by the order of the candidate
    key; ``None`` with fewer than two."""
    if len(scores) < 2:
        return None
    first, second = sorted(scores, key=lambda candidate: (-scores[candidate], candidate))[:2]
    return first, second


def differential_credit(measurements):
    """The scores, the sheets and the credit of ``measurements`` (``[{'test', 'candidate', 'value'}]``, in arrival order).
    Also ``entries`` (each admitted candidate's entry score), ``differentials`` (a test has at most one: its ``test``, its
    ``pair`` (the top two of the candidates listed before it that it measured, the higher score first), the credit it earned
    (``value``), the ``difference`` of the two ``moves``) and ``test_credits`` (each test's entries plus its differential)."""
    tests, values = [], {}
    for row in measurements:
        if row['test'] not in tests:
            tests.append(row['test'])
        values.setdefault((row['test'], row['candidate']), []).append(row['value'])
    candidates = sorted({candidate for _, candidate in values})
    sheets = {candidate: {} for candidate in candidates}
    entries, admitted, differentials = {}, {}, []

    def score(candidate):
        return math.fsum(math.fsum(held) for held in sheets[candidate].values())
    for position, test in enumerate(tests):
        measured = [candidate for candidate in candidates if (test, candidate) in values]
        changes = {candidate: sheet_weight(test) * math.fsum(values[test, candidate]) / len(values[test, candidate])
                   for candidate in measured}
        pair = lead_pair({candidate: score(candidate) for candidate in measured if candidate in entries})
        if pair is not None:
            first, second = pair
            difference = abs(changes[first] - changes[second])
            differentials.append({'test': test, 'pair': [first, second], 'value': difference, 'difference': difference,
                                  'moves': [changes[first], changes[second]]})
        for candidate in measured:
            sheets[candidate].setdefault(_kind(test), []).append(changes[candidate])
            if candidate not in entries and changes[candidate] > 0:
                entries[candidate], admitted[candidate] = score(candidate), position
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
    """The most one further structure-search test can add to the credit of one target, from where the list stands: a PROVED
    maximum.

    ``held`` is ``standing`` of the target. The test measures candidates of ``measurable`` (the ``product:`` identifiers, each
    possibly not yet held) and up to ``unseen`` others never met, at most ``limit`` candidates in all when ``limit`` is given.

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


def site_test_ceiling(held, candidates):
    """The most one ``site_correspondence`` test can add to the credit of one target, from where the list stands: a PROVED maximum
    (``held`` is ``standing`` of the target; ``candidates``: the identifiers of the candidates of the graded search it grades, which
    all have a mean B on the search's own test).

    Proof. A candidate's value in the test is its mean E over its hits with sites, ``E = B F``; ``B`` is in [0, 1] (``B = [2 n /
    (L_target + L_reference)] / [1 + (RMSD / 2 A)^2]`` with ``n`` at most the shorter length, so the first factor is at most 1) and
    ``F`` is a mean of residue scores, each a class match 0 or 1 times a kernel in (0, 1]. So the raw value is in [0, 1] and, times
    the family weight ``w``, the candidate's move is in [0, w]. A candidate with no hit with sites is not measured and earns
    nothing. The test is appended last, so it earns (1) the entry of each candidate it admits: none, since a candidate with a mean
    B above 0 was admitted by the search's own test (listed), and one with mean B 0 has B = 0 on every hit, so E = 0 on its hits with
    sites and it is not admitted; (2) ONE differential, ``|d_a - d_b|`` of the top two of the listed candidates it measures (two
    numbers in [0, w]): at most ``w``, and only when at least two listed candidates are measured; (3) nothing else. So the bound is
    ``w`` with two or more listed candidates among ``candidates``, else 0. Tight: the top two at ``w`` and 0."""
    weight = SHEET_WEIGHT['site_correspondence']
    listed = sum(1 for candidate in dict.fromkeys(candidates) if held.get(candidate, {}).get('listed'))
    return weight * float(1 if listed >= 2 else 0)


def bound_partner_test_ceiling(held, possible_partners):
    """The most one ``bound_partner`` test (``partner_contacts``) can add to the credit of one target, from where the list stands: a
    PROVED maximum (``held`` is ``standing`` of the target), given the SET of partner candidates the search's solved entries make
    possible (``possible_partners``: the keys ``ligand:<component id>`` and ``nucleic_acid:dna|rna`` that ``partner_contacts.
    possible_partners`` reads from the held hit metadata).

    Proof. The candidates of the test are the partners some hit chain is bound to. A partner of a hit chain is a molecule of the
    hit's entry, so a ligand candidate is a non-additive chemical component of a non-polymer entity of an entry of the search, and
    a nucleic-acid candidate is ``dna`` or ``rna`` of a nucleic-acid polymer entity of such an entry (a hybrid entity can give
    either). The held hit metadata lists exactly those (RCSB ``nonpolymer_entities`` and the polymer types of
    ``polymer_entities`` per entry); an entry's contents are an UPPER set, since a ligand of the entry need not touch the hit chain;
    and the unit fails (it does not grade) if a file shows a partner outside the entry's listed contents. So every candidate the
    test can measure is in ``possible_partners`` (a set ``P``). A candidate's value in the test is its mean ``E(hit, partner) = B F``
    over the hits bound to it; ``B`` is in [0, 1] and ``F`` is a mean of residue scores, each a class match 0 or 1 times a kernel in
    (0, 1], so the value times the family weight ``w`` is in [0, w], whatever the structures show. A candidate no hit is bound to
    is not measured and earns nothing. The test is appended last (after the unit's first test, which adds product candidates only
    and so changes no partner's standing), so it earns (1) the entry score of each candidate of ``P`` not yet listed that it
    admits: at most ``w`` each, ``u`` of them; (2) ONE differential, ``|d_a - d_b|`` of the top two of the listed candidates
    (any kind; here all partners) it measures: at most ``w``, and only when at least two of ``P`` are listed (``k >= 2``); (3)
    nothing else (a listed candidate not in ``P`` cannot be measured). The bound is ``w (u + (1 if k >= 2))``. Tight: the top two
    at ``w`` and 0, every unlisted candidate at ``w``."""
    weight = SHEET_WEIGHT['bound_partner']
    candidates = list(dict.fromkeys(possible_partners))
    listed = sum(1 for candidate in candidates if held.get(candidate, {}).get('listed'))
    return weight * float(len(candidates) - listed + (1 if listed >= 2 else 0))


def ligand_transplant_test_ceiling(held):
    """The most one ``ligand_transplant`` test (``ligand_transplants``) can add to the credit of one target, from where the list
    stands: a PROVED maximum (``held`` is ``standing`` of the target).

    Proof. The candidates of the test are ``ligand:<compound id>`` of the non-additive compounds of the AlphaFill answer, and
    AlphaFill transplants a fixed list of compounds ("Currently, we are transplanting 2,694 different compounds", the paper);
    the unit raises if an answer holds more distinct non-additive compounds than ``ligand_transplants_sheet.ELIGIBLE_COMPOUNDS``,
    so the test measures at most ``u`` = that many candidates. A candidate's value in the test is the value of its best transplant,
    ``fit x no_clash`` with both degrees in (0, 1], so in (0, 1], and times the family weight ``w`` in (0, w]. The test is appended
    last, so it earns (1) the entry score of each candidate it admits (a first value above zero, which every measured candidate
    has): at most ``w`` each, at most ``u`` of them; (2) ONE differential, ``|d_a - d_b|`` of the top two of the listed candidates it
    measures (two numbers in [0, w]): at most ``w``, and only when at least two listed candidates are measured, which needs at
    least two listed ``ligand:`` candidates; (3) nothing else. The bound is ``w (u + 1)`` with two or more listed ligand candidates,
    else ``w u``. It is constant and loose, not tight. Tight in form: the top two at ``w`` and 0, every unlisted candidate at ``w``."""
    weight = SHEET_WEIGHT['ligand_transplant']
    listed = sum(1 for candidate, state in held.items() if candidate.startswith('ligand:') and state['listed'])
    return weight * float(ELIGIBLE_COMPOUNDS + (1 if listed >= 2 else 0))
