"""The scoring sheet of candidate taxa: what the graded classification sheets an episode holds say about which organism
a sequence is from, as one row per candidate taxon with its score, and the credit of having found and separated them.

A candidate is a taxon that a test called: a node of the taxonomy that received support of its own. Taxa are nested (a
family holds its genera and species), and the owner's rule for that (2026-11-24) is: "this support from vaguer levels
makes sense with the fines grain level having the most score. never rivals, just different supporting bits of info.
rivals are when there is a difference in call that is not nested." So:

* A test's support at a taxon is a BIT of information for that taxon and for every finer candidate inside it. The value
  of a candidate in a test is the sum of the test's bits along the candidate's lineage (the candidate and each of its
  ancestors). A candidate's score is the sum of its values over the tests, each times the weight of the test's sheet. The
  finest-grain candidate the signals agree on therefore has the most score.
* A candidate and its ancestor are never rivals. Two candidates are RIVALS when neither is on the other's lineage.

A test is one graded source: ``<sheet>@<source reference>``. The sheets (a kind of test) and their bits:

* ``kraken2:<index>`` (the ``kraken2_classification_sheet`` of ``kraken2_grader``): the bit at a taxon is the share of
  the sequence's k-mers the index maps to that taxon itself (``kmers_direct`` over all k-mers). The bits of one test sum
  to at most 1. Kraken 2 itself decides this way: it sums the k-mers along each root-to-leaf path and takes the leaf with
  the most.

The weight of a sheet is one over its typical strong value, so that a strong result of each sheet counts about 1
(``TYPICAL_STRONG_VALUE``, derived from stored real runs, the derivation beside each value).

Which candidates a test can measure. A test measures a candidate only when the test's database holds the candidate's
part of the taxonomy (``covers_taxon_ids`` of the grading: the top taxa of the index; the viral index holds viruses only,
so it says nothing for or against a bacterium).

The credit follows the reference's differential credit (``sequence_homology_evidence/differential_credit``; the owner's
rules are quoted in the build procedure, Step 7), with the nesting:

* Entry. A candidate is admitted on positive evidence (a first bit of its own). A new possibility earns its score at entry.
  A finer candidate under a listed one earns what it adds: its score less the score of its deepest listed ancestor. A
  vaguer candidate above a listed one earns nothing at entry: it is a supporting bit of a possibility already listed.
  (The last two sentences are the building session's reading of "never rivals, just different supporting bits".)
* Differential. A test earns the absolute difference of the moves of ONE pair: the two leading rivals among the candidates
  listed before the test that the test can measure (the highest score, then the highest score among its rivals). With no
  such pair, no differential.
* Credit is the sum of the entries and the differentials. It never falls; the same test held twice is one test.

Measurements of different targets are never compared: every table is per target.

Nothing here reads a file or runs a tool: it reads the records the episode holds, through the reader it is given."""
import math

from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.tool_grading_artifacts import (
    source_tool_grading_entries)
from gene_annotation_episode.episodic_workflow.episode_support.grading.taxonomic_classification.kraken2_grader import (
    SHEET as KRAKEN2_SHEET)

# The typical strong value of each sheet: the value of the right candidate when the sequence's own genome is in the index.
# Derived 2026-11-24 from the stored real classifications of runs/organism_kmer_check_1 (hepatitis E virus M73218 and three
# slices of it, each against both indexes; read by the grader in runs/kraken2_grader_check_1):
#   kraken2:viral         0.988, 0.917, 1.000 for 7207, 1000 and 300 letters: median 0.988
#   kraken2:standard_8gb  0.067, 0.085, 0.053 for the same three, and 0.068 for 60 kb of the E. coli chromosome (its k-mers
#                         with a taxon; nearly all of them lie on the lineage of Escherichia coli): median 0.068. The index is
#                         capped at 8 GB and holds a part of the k-mers of its genomes, hence the low share.
# One virus and one bacterium: re-derive as classifications of other organisms accumulate.
TYPICAL_STRONG_VALUE = {'kraken2:viral': 0.988, 'kraken2:standard_8gb': 0.068}
SHEET_WEIGHT = {sheet: 1 / value for sheet, value in TYPICAL_STRONG_VALUE.items()}


def held_sources(reader):
    """The sources the episode holds, in the order it obtained them (receipt order)."""
    return [ref for ref in reader.refs() if ref.startswith('source_')]


def sheet_of(test):
    return test.split('@', 1)[0]


def sheet_weight(test):
    sheet = sheet_of(test)
    if sheet not in SHEET_WEIGHT:
        raise ValueError('taxon_sheet_has_no_stated_weight:' + sheet)
    return SHEET_WEIGHT[sheet]


def _kraken2(grading):
    """``(sheet name, covers, rows)`` of one Kraken 2 grading: a row per taxon with k-mers of its own."""
    sheet = grading['sheet']
    total = sheet['kmers']['all']
    rows = [{'taxon_id': row['taxon_id'], 'name': row['name'], 'rank_code': row['rank_code'],
             'lineage_taxon_ids': list(row['lineage_taxon_ids']), 'bit': row['kmers_direct'] / total}
            for row in sheet['taxa'] if row['kmers_direct'] > 0]
    return 'kraken2:' + grading['index']['index'], list(grading['index']['covers_taxon_ids']), rows


READERS = {KRAKEN2_SHEET: _kraken2}


def taxon_tests(reader, scope, sources):
    """The tests the episode holds, in arrival order: ``[{'test', 'target', 'covers', 'rows'}]``, one per graded
    classification sheet of a source whose operand is a subject of ``scope``. ``rows`` are the test's bits (``taxon_id``,
    ``name``, ``rank_code``, ``lineage_taxon_ids``, ``bit``); a test that found nothing has no row and is still a test."""
    scope = reader.validate_scope(scope)
    tests = []
    for reference in sources:
        source = reader.get(reference)
        for entry in source_tool_grading_entries(reader, reference):
            schema = entry['grading']['sheet'].get('schema')
            if schema not in READERS:
                continue
            target = source['operand_refs'][0]
            if target not in scope['subject_refs']:
                continue
            sheet, covers, rows = READERS[schema](entry['grading'])
            tests.append({'test': sheet + '@' + reference, 'target': target, 'covers': covers, 'rows': rows})
    return tests


def nested(first, second):
    """Whether one of two candidates (each ``{'taxon_id', 'lineage_taxon_ids'}``) is on the other's lineage."""
    return first['taxon_id'] in second['lineage_taxon_ids'] or second['taxon_id'] in first['lineage_taxon_ids']


def measurable(candidate, covers):
    """Whether a test whose database holds the taxa ``covers`` (and what is below them) can measure the candidate."""
    return any(taxon in candidate['lineage_taxon_ids'] for taxon in covers)


def _order(candidates, scores):
    """The candidate ids, the highest score first; on a tie the finer candidate, then the lower id."""
    return sorted(scores, key=lambda taxon: (-scores[taxon], -len(candidates[taxon]['lineage_taxon_ids']), taxon))


def lead_rivals(candidates, scores, covers=None):
    """``(leader, rival)`` among the listed candidates (those a test with ``covers`` can measure, or all with ``None``):
    the highest score and the highest score among its rivals; ``None`` when there are not two."""
    listed = [taxon for taxon in _order(candidates, scores) if covers is None or measurable(candidates[taxon], covers)]
    if not listed:
        return None
    rivals = [taxon for taxon in listed[1:] if not nested(candidates[listed[0]], candidates[taxon])]
    return (listed[0], rivals[0]) if rivals else None


def target_table(tests):
    """The arithmetic of one target's tests (``taxon_tests`` rows of that target, in arrival order): ``candidates`` (per
    taxon id its row facts), ``scores``, ``sheets`` (per candidate, per sheet, its summed weighted value), ``entries`` (per
    candidate its entry credit and the test that admitted it), ``differentials`` (per test at most one: the pair, the two
    moves, the difference), ``test_credits`` and ``credit``."""
    candidates, scores, sheets, entries, differentials, test_credits = {}, {}, {}, {}, [], {}
    seen = set()
    for test in tests:
        if test['test'] in seen:
            raise ValueError('taxon_test_held_twice:' + test['test'])
        seen.add(test['test'])
        weight, bits = sheet_weight(test['test']), {row['taxon_id']: row['bit'] for row in test['rows']}

        def move(candidate):
            return weight * math.fsum(bits.get(taxon, 0.0) for taxon in candidate['lineage_taxon_ids'])
        credit = 0.0
        pair = lead_rivals(candidates, scores, test['covers'])
        if pair is not None:
            moves = [move(candidates[taxon]) for taxon in pair]
            differentials.append({'test': test['test'], 'pair': list(pair), 'moves': moves,
                                  'difference': abs(moves[0] - moves[1])})
            credit += abs(moves[0] - moves[1])
        for taxon, candidate in candidates.items():
            change = move(candidate)
            if change:
                scores[taxon] += change
                sheets[taxon][sheet_of(test['test'])] = sheets[taxon].get(sheet_of(test['test']), 0.0) + change
        for row in sorted(test['rows'], key=lambda item: (len(item['lineage_taxon_ids']), item['taxon_id'])):
            taxon = row['taxon_id']
            if taxon in candidates or row['bit'] <= 0:
                continue
            candidate = {key: row[key] for key in ('taxon_id', 'name', 'rank_code', 'lineage_taxon_ids')}
            above = [other for other in candidates if other in candidate['lineage_taxon_ids']]
            below = [other for other in candidates if taxon in candidates[other]['lineage_taxon_ids']]
            # every earlier test's bits on this lineage sit at listed ancestors, so the deepest listed ancestor's score
            # holds them; this test's bits on the lineage are in ``move``
            base = max((scores[other] for other in above), default=0.0)
            own = weight * math.fsum(bits.get(node, 0.0) for node in candidate['lineage_taxon_ids']
                                     if not any(node in candidates[other]['lineage_taxon_ids'] for other in above))
            candidates[taxon], scores[taxon] = candidate, base + own
            sheets[taxon] = dict(sheets[max(above, key=lambda other: scores[other])]) if above else {}
            sheets[taxon][sheet_of(test['test'])] = sheets[taxon].get(sheet_of(test['test']), 0.0) + own
            earned = 0.0 if (below and not above) else scores[taxon] - base
            entries[taxon] = {'test': test['test'], 'credit': earned}
            credit += earned
        test_credits[test['test']] = credit
    return {'candidates': candidates, 'scores': scores, 'sheets': sheets, 'entries': entries,
            'differentials': differentials, 'test_credits': test_credits,
            'credit': math.fsum(test_credits.values())}


def taxon_table(reader, scope, sources):
    """The scoring sheet of the scope: per target its table (``target_table``) with the candidate rows in order (the
    leading candidate first: ``taxon_id``, ``name``, ``rank_code``, ``lineage_taxon_ids``, ``score``, ``sheets``), the
    ``leader``, its leading ``rival`` (or ``None``) and ``agreed_taxon_id`` (the deepest taxon the leader and its rival
    share, ``None`` when they share none or there is no rival); and the ``credit`` of the scope (the sum over targets)."""
    tests = taxon_tests(reader, scope, sources)
    targets = {}
    for target in reader.validate_scope(scope)['subject_refs']:
        table = target_table([test for test in tests if test['target'] == target])
        order = _order(table['candidates'], table['scores'])
        pair = lead_rivals(table['candidates'], table['scores'])
        agreed = None
        if pair is not None:
            shared = [taxon for taxon in table['candidates'][pair[0]]['lineage_taxon_ids']
                      if taxon in table['candidates'][pair[1]]['lineage_taxon_ids']]
            agreed = shared[-1] if shared else None
        targets[target] = {**table, 'rows': [{**table['candidates'][taxon], 'score': table['scores'][taxon],
                                              'sheets': table['sheets'][taxon]} for taxon in order],
                           'leader': order[0] if order else None, 'rival': None if pair is None else pair[1],
                           'agreed_taxon_id': agreed, 'tests': [test['test'] for test in tests if test['target'] == target]}
    return {'targets': targets, 'credit': math.fsum(table['credit'] for table in targets.values())}


def test_ceiling(table, sheet, covers):
    """The most the credit can rise by one new test of ``sheet`` whose database holds ``covers``, from the target's
    ``table`` (``target_table``). The bits of one test sum to at most 1, and a candidate's move is the weight times its
    lineage's bits, so: the entries of a test are at most the weight (each admitted candidate earns at most the weight
    times its own bit, the bits it adds to its deepest listed ancestor; a vaguer candidate above a listed one earns
    nothing), and its one differential is at most the weight (two moves, each between 0 and the weight). The differential
    needs two listed rivals the test can measure."""
    weight = sheet_weight(sheet)
    return weight + (weight if lead_rivals(table['candidates'], table['scores'], covers) is not None else 0.0)


__all__ = ['SHEET_WEIGHT', 'TYPICAL_STRONG_VALUE', 'held_sources', 'lead_rivals', 'measurable', 'nested', 'sheet_of',
           'sheet_weight', 'target_table', 'taxon_table', 'taxon_tests', 'test_ceiling']
