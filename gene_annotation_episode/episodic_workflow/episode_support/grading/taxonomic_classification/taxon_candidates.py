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
* ``genomad:<database version>`` (the ``genomad_classification_sheet`` of ``genomad_grader``): geNomad's three scores of
  the kind of DNA sum to 1 and are its bits. The chromosome and the plasmid score together are the bit at cellular
  organisms (a chromosome or a plasmid is of a cell). The virus score is the bit of the virus side: the share of it that the
  genes' agreement on a lineage carries sits at the deepest taxon of that lineage, the rest at Viruses (all of it there when
  no gene gave a taxonomy). The bits of one test sum to 1 (geNomad writes the scores rounded, so as written they can sum
  to a little more; they are then divided by their sum).
* ``vitap:<database name>`` (the ``vitap_assignment_sheet`` of ``vitap_grader``): the lineage VITAP settled on, and each
  other lineage it considered that is not nested with one already taken (the higher score first; the same lineage cut at
  another depth is not a second call). VITAP's lineage score s has no stated maximum, so the bit of lineage i, at the finest
  taxon of it that resolves, is s_i / (1 + the sum of the taken lineages' scores): it rises with the score, stays below 1,
  and the bits of one test sum to less than 1.

* ``search_hits:<program>:<database>`` (the ``search_taxon_claim_sheet`` of ``search_taxon_claims``): the taxa the hits of
  one database search name, kept by the head that searched (feature calling). These are CLAIMS (below). The bit of a
  claim is the closeness of its taxon's best hit times the share of the searched sequence it covers, the bits of one
  search divided by their sum when it is above 1, so they sum to at most 1.

The weight of a sheet is one over its typical strong value, so that a strong result of each sheet counts about 1
(``TYPICAL_STRONG_VALUE``, derived from stored real runs, the derivation beside each value). The claim sheets have one
weight for their family (``search_hits``), whatever the program and database.

CLAIMS. A claim test is read by a claim reader (``CLAIM_READERS``). The owner (2026-11-25): a whole-genome hit "should
augment the organism side like a claim does for our feature calls"; "the whole genome hit's path to the organism taxa
score should be like claim being added to a feature call"; it needs "an auto-scoring feature", not a re-commission. So,
as claims are kept in the sheet of feature calls (``sequence_features/feature_candidates``):

* A claim is a taxon id and a bit, and nothing else. The table holds the tree: it places the claim's taxon on the one
  prepared taxonomy (``ncbi_taxonomy.prepared_taxonomy``: its name, rank code and lineage), which is how it sees that a
  claim at a species lies inside a candidate family. The taxonomy is a fixed fact, not a property of a run, and it is
  loaded only when a claim test is held.
* A claim never admits a candidate. Its bit at taxon T is a bit like any other: it adds to the score of every listed
  candidate that is T or lies inside T, from the moment the claim is held, whatever the order (a candidate admitted
  later has in its score the bits of the claims held before it on its lineage).
* A claim no listed candidate is T or lies inside WAITS: it adds to no score and is listed (``waiting``), with its
  ``reason``. The owner: "a claim finer than any candidate waits and gets half credit if it is at least consistent with
  the max resolution of the claim". A claim whose T lies inside a listed candidate (the candidate is on T's lineage: the
  claim agrees with it as far as it goes, and is finer) waits (``finer_than_its_candidate``) and earns, once, half the
  weight of its sheet times its bit, when it is the first claim held at its taxon. A claim no listed candidate is on a
  line with (neither inside it nor containing it: it disagrees with what is listed, or nothing is listed) waits
  (``no_candidate_on_its_lineage``) and earns nothing.
* A claim at a taxon the prepared taxonomy does not hold cannot be placed: it adds to nothing, earns nothing and is listed with
  the reason ``taxon_not_in_taxonomy``, so the gap is visible. It is not guessed.

Measurements of the organism side are of the sequence that is placed; a search's claims are about the sequence its hits
are on, so a claim test is read for a sequence of the scope only when its source's operand is that sequence.

Which candidates a test can measure. A test measures a candidate only when the test's database holds the candidate's
part of the taxonomy (``covers_taxon_ids`` of the grading: the top taxa of the index; the viral index holds viruses only,
so it says nothing for or against a bacterium).

The credit follows the reference's differential credit (``sequence_homology_evidence/differential_credit``; the owner's
rules are quoted in the build procedure, Step 7), with the nesting:

* Entry. A candidate is admitted on positive evidence (a first bit of its own). A new possibility earns its score at entry.
  A finer candidate under a listed one earns what it adds: its score less the score of its deepest listed ancestor. A
  vaguer candidate above a listed one earns nothing at entry: it is a supporting bit of a possibility already listed.
  (The last two sentences are the building session's reading of "never rivals, just different supporting bits".)
  A claim admits nothing and has no entry. What the claims held before a candidate add to its score is in what it adds,
  less what each of those claims already earned: a claim earns, through its half while it waited and the entries its
  bit is in, at most its weighted bit, once (the half already paid is not paid again, and a claim's bit counted in one
  candidate's entry is not counted in another's).
* Differential. A test earns the absolute difference of the moves of ONE pair: the two leading rivals among the candidates
  listed before the test that the test can measure (the highest score, then the highest score among its rivals). With no
  such pair, no differential. This is a claim test's credit too: a claim that makes another candidate take the lead is
  paid by that difference (the owner: credit is "by the gain in score in the other sheet if it takes over the leading
  score").
* Waiting. A claim test also earns the halves of its waiting claims (CLAIMS above).
* Credit is the sum of the entries, the differentials and the halves. It never falls; the same test held twice is one test.

With no claim test held, the table is the one it was before claims: no claim adds to a score, waits or earns.

Measurements of different targets are never compared: every table is per target.

Nothing here reads a file or runs a tool: it reads the records the episode holds, through the reader it is given."""
import math

from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.tool_grading_artifacts import (
    source_tool_grading_entries)
from gene_annotation_episode.episodic_workflow.episode_support.grading.taxonomic_classification.genomad_grader import (
    CELLULAR, SHEET as GENOMAD_SHEET, VIRUSES)
from gene_annotation_episode.episodic_workflow.episode_support.grading.taxonomic_classification.kraken2_grader import (
    SHEET as KRAKEN2_SHEET)
from gene_annotation_episode.episodic_workflow.episode_support.grading.taxonomic_classification.ncbi_taxonomy import (
    prepared_taxonomy, taxon_row)
from gene_annotation_episode.episodic_workflow.episode_support.grading.taxonomic_classification.search_taxon_claims import (
    FAMILY as CLAIM_FAMILY, SHEET as SEARCH_CLAIM_SHEET, read_search_taxon_claim_sheet)
from gene_annotation_episode.episodic_workflow.episode_support.grading.taxonomic_classification.vitap_grader import (
    SHEET as VITAP_SHEET)

# The typical strong value of each sheet: the value of the right candidate when the sequence's own genome is in the index.
# Derived 2026-11-24 from the stored real classifications of runs/organism_kmer_check_1 (hepatitis E virus M73218 and three
# slices of it, each against both indexes; read by the grader in runs/kraken2_grader_check_1):
#   kraken2:viral         0.988, 0.917, 1.000 for 7207, 1000 and 300 letters: median 0.988
#   kraken2:standard_8gb  0.067, 0.085, 0.053 for the same three, and 0.068 for 60 kb of the E. coli chromosome (its k-mers
#                         with a taxon; nearly all of them lie on the lineage of Escherichia coli): median 0.068. The index is
#                         capped at 8 GB and holds a part of the k-mers of its genomes, hence the low share.
# One virus and one bacterium: re-derive as classifications of other organisms accumulate.
#   genomad:1.9           the value of the family Hepeviridae for the four whole hepevirus genomes of runs/genomad_run_2 whose
#                         relatives are in geNomad's markers (M73218, ON009841, OR232336, OR713884): their virus scores
#                         0.9707, 0.9706, 0.9687, 0.9717, median 0.9707 (the agreement was 1.0 in all four)
#   vitap:DB_hybrid_MSL37_RefSeq209_IMGVR
#                         the bit of the family Hepeviridae for M73218 and two slices of it in runs/vitap_run_2 (the genome
#                         is in VITAP's database): lineage scores 3.191, 2.272, 1.776 with a second lineage at 0.001 or none,
#                         so bits 0.761, 0.694, 0.640: median 0.694
#   search_hits           the family of the claim sheets (every program and database): 1.0, a starting value of 2026-11-25
#                         with no stored run behind it (a close match over the whole searched sequence has a value near 1,
#                         and a search whose values sum above 1 is divided down to 1). To be derived from real runs.
TYPICAL_STRONG_VALUE = {'kraken2:viral': 0.988, 'kraken2:standard_8gb': 0.068, 'genomad:1.9': 0.9707,
                        'vitap:DB_hybrid_MSL37_RefSeq209_IMGVR': 0.694, CLAIM_FAMILY: 1.0}
SHEET_WEIGHT = {sheet: 1 / value for sheet, value in TYPICAL_STRONG_VALUE.items()}
# The bits of one test sum to at most 1 as numbers; summed in floating point, in another order than the proof's, they can
# come out above 1 by a few units in the last place. The ceiling allows for that and for nothing else.
SUM_ROUNDING = 1e-9
# Why a claim waits (the module's description).
FINER, OFF_LINEAGE, NOT_IN_TAXONOMY = 'finer_than_its_candidate', 'no_candidate_on_its_lineage', 'taxon_not_in_taxonomy'
WAITING_REASONS = (FINER, OFF_LINEAGE, NOT_IN_TAXONOMY)


def held_sources(reader):
    """The sources the episode holds, in the order it obtained them (receipt order)."""
    return [ref for ref in reader.refs() if ref.startswith('source_')]


def sheet_of(test):
    return test.split('@', 1)[0]


def is_claim_sheet(sheet):
    """Whether a sheet name is of the claim sheets (its first part is their family)."""
    return sheet.split(':', 1)[0] == CLAIM_FAMILY


def sheet_weight(test):
    """The weight of a test's sheet: by its sheet name, and for a claim sheet by its family."""
    sheet = sheet_of(test)
    key = CLAIM_FAMILY if is_claim_sheet(sheet) else sheet
    if key not in SHEET_WEIGHT:
        raise ValueError('taxon_sheet_has_no_stated_weight:' + sheet)
    return SHEET_WEIGHT[key]


def _kraken2(grading):
    """``(sheet name, covers, rows)`` of one Kraken 2 grading: a row per taxon with k-mers of its own."""
    sheet = grading['sheet']
    total = sheet['kmers']['all']
    rows = [{'taxon_id': row['taxon_id'], 'name': row['name'], 'rank_code': row['rank_code'],
             'lineage_taxon_ids': list(row['lineage_taxon_ids']), 'bit': row['kmers_direct'] / total}
            for row in sheet['taxa'] if row['kmers_direct'] > 0]
    return 'kraken2:' + grading['index']['index'], list(grading['index']['covers_taxon_ids']), rows


def _bit_row(row, bit):
    return {'taxon_id': row['taxon_id'], 'name': row['name'], 'rank_code': row['rank_code'],
            'lineage_taxon_ids': list(row['lineage_taxon_ids']), 'bit': bit}


def _genomad(grading):
    """``(sheet name, covers, rows)`` of one geNomad grading (the module's description states the bits)."""
    sheet = grading['sheet']
    genes = sheet['gene_taxonomy']
    # geNomad writes the three scores rounded to four decimals, so as written they can sum to a little more than 1
    # (0.4501 + 0.4419 + 0.1081 = 1.0001 in run organism_identification_06): they are shares of one, so they are divided by
    # their sum when it is above 1
    over = max(1.0, math.fsum(sheet['kind'].values()))
    kind = {name: value / over for name, value in sheet['kind'].items()}
    bits = {CELLULAR: (sheet['kind_taxa']['cellular'], kind['chromosome_score'] + kind['plasmid_score'])}
    deepest = None if not sheet['taxa'] else sheet['taxa'][-1]
    agreed = 0.0 if deepest is None else kind['virus_score'] * genes['agreement']
    if deepest is not None and deepest['taxon_id'] != VIRUSES:
        bits[deepest['taxon_id']] = (deepest, agreed)
        bits[VIRUSES] = (sheet['kind_taxa']['virus'], kind['virus_score'] - agreed)
    else:
        bits[VIRUSES] = (sheet['kind_taxa']['virus'], kind['virus_score'])
    return ('genomad:' + grading['database']['version'], [VIRUSES, CELLULAR],
            [_bit_row(row, bit) for row, bit in bits.values() if bit > 0])


def _vitap(grading):
    """``(sheet name, covers, rows)`` of one VITAP grading (the module's description states the bits)."""
    sheet = grading['sheet']
    taken = []
    for lineage in ([] if sheet['best'] is None else [sheet['best']]) + sorted(
            sheet['lineages'], key=lambda item: (-item['lineage_score'], item['names'])):
        taxon = lineage['taxon']
        if taxon is None or lineage['lineage_score'] <= 0 or any(nested(taxon, other) for other, _ in taken):
            continue
        taken.append((taxon, lineage['lineage_score']))
    total = 1 + math.fsum(score for _, score in taken)
    return 'vitap:' + grading['database']['name'], [VIRUSES], [_bit_row(taxon, score / total) for taxon, score in taken]


READERS ={KRAKEN2_SHEET: _kraken2, GENOMAD_SHEET: _genomad, VITAP_SHEET: _vitap}
# The readers of claim sheets: ``grading -> (sheet name, covers, rows)`` with one row per claim, ``{'taxon_id', 'bit'}``.
CLAIM_READERS = {SEARCH_CLAIM_SHEET: read_search_taxon_claim_sheet}


def _placed(rows):
    """The claims of a claim test placed on the prepared taxonomy (each with its taxon's name, rank code and lineage), and
    those at a taxon it does not hold (the module's description)."""
    taxonomy = prepared_taxonomy()
    placed, unplaced = [], []
    for row in rows:
        if row['taxon_id'] in taxonomy['nodes']:
            placed.append(_bit_row(taxon_row(taxonomy, row['taxon_id']), row['bit']))
        else:
            unplaced.append({'taxon_id': row['taxon_id'], 'bit': row['bit']})
    return placed, unplaced


def taxon_tests(reader, scope, sources):
    """The tests the episode holds, in arrival order: ``[{'test', 'target', 'covers', 'rows', 'claim', 'unplaced'}]``,
    one per graded classification sheet or claim sheet of a source whose operand is a subject of ``scope``. ``rows`` are
    the test's bits (``taxon_id``, ``name``, ``rank_code``, ``lineage_taxon_ids``, ``bit``); a test that found nothing has
    no row and is still a test. ``claim`` says whether it is a claim test; a claim test's rows are its claims placed on
    the prepared taxonomy, and ``unplaced`` its claims at taxa the taxonomy does not hold."""
    scope = reader.validate_scope(scope)
    tests = []
    for reference in sources:
        source = reader.get(reference)
        for entry in source_tool_grading_entries(reader, reference):
            schema = entry['grading']['sheet'].get('schema')
            if schema not in READERS and schema not in CLAIM_READERS:
                continue
            target = source['operand_refs'][0]
            if target not in scope['subject_refs']:
                continue
            if schema in READERS:
                sheet, covers, rows = READERS[schema](entry['grading'])
                tests.append({'test': sheet + '@' + reference, 'target': target, 'covers': covers, 'rows': rows,
                              'claim': False, 'unplaced': []})
                continue
            sheet, covers, claims = CLAIM_READERS[schema](entry['grading'])
            rows, unplaced = _placed(claims)
            tests.append({'test': sheet + '@' + reference, 'target': target, 'covers': covers, 'rows': rows,
                          'claim': True, 'unplaced': unplaced})
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


def _waiting_row(claim, candidates):
    """The row of a placed claim no listed candidate is or lies inside: the deepest listed candidate on its lineage (the
    one it is consistent with), or none, and why it waits."""
    consistent = [other for other in candidates if other in claim['lineage_taxon_ids']]
    deepest = max(consistent, key=lambda other: (len(candidates[other]['lineage_taxon_ids']), -other), default=None)
    return {'taxon_id': claim['taxon_id'], 'lineage_taxon_ids': list(claim['lineage_taxon_ids']), 'bit': claim['bit'],
            'support': claim['support'], 'consistent_taxon_id': deepest,
            'reason': FINER if consistent else OFF_LINEAGE, 'credit': claim['waiting_credit'], 'test': claim['test']}


def target_table(tests):
    """The arithmetic of one target's tests (``taxon_tests`` rows of that target, in arrival order): ``candidates`` (per
    taxon id its row facts), ``scores``, ``sheets`` (per candidate, per sheet, its summed weighted value), ``entries`` (per
    candidate its entry credit and the test that admitted it), ``differentials`` (per test at most one: the pair, the two
    moves, the difference), ``waiting_credits`` (per claim test the halves its waiting claims earned), ``waiting`` (the
    claims held that no listed candidate is or lies inside, from all the records held: taxon id, lineage, bit, weighted
    ``support``, ``consistent_taxon_id``, ``reason``, ``credit`` and ``test``; the best supported first),
    ``outstanding_claim_support`` (what the placed claims' weighted bits could still earn in entries: each one's weighted
    bit less what it earned), ``test_credits`` and ``credit``. With no claim test, ``waiting_credits`` and ``waiting`` are
    empty, ``outstanding_claim_support`` is 0 and every other number is as it was before claims."""
    candidates, scores, sheets, entries, differentials, test_credits = {}, {}, {}, {}, [], {}
    claims, waiting_credits = [], {}      # the placed claims held so far, in arrival order (the module's description)
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
        if test['claim']:
            # a claim admits nothing; one that no listed candidate is or lies inside waits, and earns half its weighted
            # bit when a listed candidate is on its lineage and it is the first claim held at its taxon (the strongest
            # first)
            halves = 0.0
            for row in sorted(test['rows'], key=lambda item: (-item['bit'], item['taxon_id'])):
                if row['bit'] <= 0:
                    continue
                taxon = row['taxon_id']
                home = [other for other in candidates if taxon in candidates[other]['lineage_taxon_ids']]
                consistent = [other for other in candidates if other in row['lineage_taxon_ids']]
                first = not any(claim['taxon_id'] == taxon for claim in claims)
                half = weight * row['bit'] / 2 if (not home and consistent and first) else 0.0
                claims.append({'test': test['test'], 'sheet': sheet_of(test['test']), 'taxon_id': taxon,
                               'lineage_taxon_ids': list(row['lineage_taxon_ids']), 'bit': row['bit'],
                               'support': weight * row['bit'], 'earned': half, 'waiting_credit': half})
                halves += half
            waiting_credits[test['test']] = halves
            credit += halves
            test_credits[test['test']] = credit
            continue
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
            # the claims held before this test at taxa on its lineage below every listed ancestor: no listed ancestor's
            # score holds them, and they are support of this candidate (none without a claim test)
            under = [claim for claim in claims if claim['taxon_id'] in candidate['lineage_taxon_ids']
                     and not any(claim['taxon_id'] in candidates[other]['lineage_taxon_ids'] for other in above)]
            candidates[taxon], scores[taxon] = candidate, base + own + math.fsum(claim['support'] for claim in under)
            sheets[taxon] = dict(sheets[max(above, key=lambda other: scores[other])]) if above else {}
            sheets[taxon][sheet_of(test['test'])] = sheets[taxon].get(sheet_of(test['test']), 0.0) + own
            for claim in under:
                sheets[taxon][claim['sheet']] = sheets[taxon].get(claim['sheet'], 0.0) + claim['support']
            if below and not above:
                earned = 0.0
            else:
                # what those claims already earned is not paid again; from here each has earned its weighted bit
                earned = max(0.0, scores[taxon] - base - math.fsum(claim['earned'] for claim in under))
                for claim in under:
                    claim['earned'] = claim['support']
            entries[taxon] = {'test': test['test'], 'credit': earned}
            credit += earned
        test_credits[test['test']] = credit
    waiting = [_waiting_row(claim, candidates) for claim in claims
               if not any(claim['taxon_id'] in candidates[other]['lineage_taxon_ids'] for other in candidates)]
    waiting.extend({'taxon_id': row['taxon_id'], 'lineage_taxon_ids': [], 'bit': row['bit'],
                    'support': sheet_weight(test['test']) * row['bit'], 'consistent_taxon_id': None,
                    'reason': NOT_IN_TAXONOMY, 'credit': 0.0, 'test': test['test']}
                   for test in tests for row in test['unplaced'] if row['bit'] > 0)
    return {'candidates': candidates, 'scores': scores, 'sheets': sheets, 'entries': entries,
            'differentials': differentials, 'waiting_credits': waiting_credits,
            'waiting': sorted(waiting, key=lambda row: (-row['support'], row['taxon_id'], row['test'])),
            'outstanding_claim_support': math.fsum(claim['support'] - claim['earned'] for claim in claims),
            'test_credits': test_credits, 'credit': math.fsum(test_credits.values())}


def taxon_table(reader, scope, sources):
    """The scoring sheet of the scope: per target its table (``target_table``, its ``waiting`` claims among it) with the
    candidate rows in order (the leading candidate first: ``taxon_id``, ``name``, ``rank_code``, ``lineage_taxon_ids``,
    ``score``, ``sheets``), the ``leader``, its leading ``rival`` (or ``None``) and ``agreed_taxon_id`` (the deepest taxon
    the leader and its rival share, ``None`` when they share none or there is no rival); and the ``credit`` of the scope
    (the sum over targets)."""
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
    lineage's bits, so its one differential is at most the weight (two moves, each between 0 and the weight); the
    differential needs two listed rivals the test can measure. Besides it:

    * A test that admits (not a claim test): its entries are at most the weight plus the outstanding claim support. Each
      admitted candidate earns the weight times the bits it adds below its deepest listed ancestor (the bits of the
      candidates of one test at nodes no other of them counts) plus, for each claim held below that ancestor on its
      lineage, the claim's weighted bit less what the claim already earned, after which the claim has earned its weighted
      bit and adds nothing to another entry; a vaguer candidate above a listed one earns nothing. With no claim held the
      outstanding support is 0 and the bound is the weight.
    * A claim test admits nothing: it earns at most the halves of its waiting claims, half the weight times bits that sum
      to at most 1."""
    weight = sheet_weight(sheet) * (1 + SUM_ROUNDING)
    differential = weight if lead_rivals(table['candidates'], table['scores'], covers) is not None else 0.0
    if is_claim_sheet(sheet):
        return weight / 2 + differential
    return weight + table['outstanding_claim_support'] * (1 + SUM_ROUNDING) + differential


__all__ = ['CLAIM_READERS', 'FINER', 'NOT_IN_TAXONOMY', 'OFF_LINEAGE', 'READERS', 'SHEET_WEIGHT', 'TYPICAL_STRONG_VALUE',
           'WAITING_REASONS', 'held_sources', 'is_claim_sheet', 'lead_rivals', 'measurable', 'nested', 'sheet_of',
           'sheet_weight', 'target_table', 'taxon_table', 'taxon_tests', 'test_ceiling']
