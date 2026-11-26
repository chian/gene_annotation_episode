"""The converter of one graded database search into claims about which organism the searched sequence is from: the
subscoring sheet ``search_taxon_claim_sheet`` and the rows the scoring sheet of candidate taxa reads from it.

Every hit of a search comes from an organism: the database gives each hit its taxon (the hit's ``taxid`` in the grader's
association of the hit, the taxon of its genome). That is evidence about the organism side's question. The owner
(2026-11-25): a whole-genome hit "should augment the organism side like a claim does for our feature calls"; "the whole
genome hit's path to the organism taxa score should be like claim being added to a feature call". So the hits of one
search become TAXON CLAIMS, one per taxon the hits name, kept by the step that keeps the search's feature claims
(``tools/sequence_features/blast_claim_keeping.py``), and the scoring sheet of candidate taxa reads them as a claim test
(``taxon_candidates``: a claim adds to the candidates that include it, waits otherwise, and never opens a candidate).

A claim is the taxon id the database gives and the facts of its hits. Nothing the database says of the taxon's place
among the taxa is taken: when the sheet is made, each taxon is placed on the organism side's one prepared taxonomy
(``ncbi_taxonomy``: its name, rank code and lineage), as the geNomad and VITAP gradings place theirs, so every sheet's taxa
meet on one taxonomy and the scoring sheet reads rows that are already placed. A taxon the prepared taxonomy does not hold
is kept as stated and marked not placed (``placed`` false): it is not guessed. (The prepared taxonomy holds only the taxa
under Viruses and the children of the root; that gap is closed by preparing the whole taxonomy, not by code.)

The sheet, going down the hits in the order of their rank (``hit_index``), per taxon named by the hits:

* ``taxon_id``: the taxon the database gives the hit; ``placed``, and when placed its ``name``, ``rank_code`` and
  ``lineage_taxon_ids`` on the prepared taxonomy (the sheet records which: ``taxonomy``);
* ``hit_count``: the hits of that taxon used;
* of its best hit (the highest ``value``, the earliest rank on a tie): ``best_rank``, ``closeness`` (the identical
  positions over the aligned positions of the hit: ``identical_unique_pair_count`` over ``unique_pair_count`` of the
  grader's measurements) and ``covered_share`` (the share of the searched sequence its alignment covers:
  ``query_paired_coverage``; ``query`` is the program's word for the searched sequence);
* ``value``: closeness times the share covered. A close match over the whole searched sequence is near 1; a close match
  over a tenth of it, or a whole-length match at a third of the positions, is low.

A hit the database gives no taxon is counted (``hits_without_taxon``) and not used; a hit the grader could give no counts
of positions for (its traceback was not complete: the counts are ``None``) is counted (``hits_without_positions``) and not
used.

The value a claim carries into the scoring sheet (``bit``): its value, and the bits of one search sum to at most 1 (the
ceiling proof of the scoring sheet needs it): when the values of a search sum above 1, each is divided by their sum. The
owner, on the closeness times the share covered: "you have the right directionality. the exact numbers and constants will
have to be decided as we tune." A starting rule of 2026-11-25 with no run behind it, to be tuned.

What a search can speak of (``covers``): the top taxa of the set of genomes its database is made from
(``DATABASE_COVERS``, by the set's name, the part of the database's name before its first dot): the viral reference
genomes hold viruses only, the bacteria and archaea genomes hold those two domains. A search says nothing for or against a
taxon outside its set.

No I/O: this module reads a grading and returns values."""
import math

from gene_annotation_episode.episodic_workflow.episode_support.grading.taxonomic_classification.genomad_grader import (
    VIRUSES)
from gene_annotation_episode.episodic_workflow.episode_support.grading.taxonomic_classification.ncbi_taxonomy import (
    identity, taxon_row)

SHEET = 'search_taxon_claim_sheet'
GRADED_SHEET = 'blast_database_sheet'
# The family of technique of the claim sheets: the first part of their sheet name ``search_hits:<program>:<database>``.
FAMILY = 'search_hits'
BACTERIA, ARCHAEA = 2, 2157
# The top taxa of each set of genomes a BV-BRC search database is made from (``bvbrc_job_route``: ``viral-reference`` and
# ``bacteria-archaea``, as proteins, genes and genome sequences).
DATABASE_COVERS = {'viral-reference': [VIRUSES], 'bacteria-archaea': [BACTERIA, ARCHAEA]}


def database_set(database):
    """The set of genomes a search database is made from: its name before the first dot."""
    return database.split('.', 1)[0]


def _hit(hit):
    """``(taxon id, value, closeness, covered share)`` of one graded hit; the closeness and the share are ``None`` when
    the grader gave no counts of positions."""
    measured = hit['measurements']
    taxon = hit['associations'][0]['taxid']
    if measured['unique_pair_count'] is None or measured['query_paired_coverage'] is None:
        return taxon, None, None, None
    closeness = measured['identical_unique_pair_count'] / measured['unique_pair_count']
    covered = measured['query_paired_coverage']
    return taxon, closeness * covered, closeness, covered


def _place(taxonomy, taxon):
    """Where the prepared taxonomy has a taxon: its name, rank code and lineage, or not placed."""
    if taxon not in taxonomy['nodes']:
        return {'placed': False, 'name': None, 'rank_code': None, 'lineage_taxon_ids': None}
    row = taxon_row(taxonomy, taxon)
    return {'placed': True, 'name': row['name'], 'rank_code': row['rank_code'],
            'lineage_taxon_ids': row['lineage_taxon_ids']}


def search_taxon_claim_sheet(grading, taxonomy):
    """The subscoring sheet of one graded search (the module's description): ``{'schema', 'program', 'database',
    'taxonomy', 'hit_count', 'hits_without_taxon', 'hits_without_positions', 'claims'}`` with one claim per taxon, the
    highest value first (the lower taxon id on a tie), each placed on ``taxonomy`` (the prepared taxonomy,
    ``ncbi_taxonomy.load_taxonomy``)."""
    sheet = grading['sheet']
    search = sheet['normalized_result']['search']
    taxa, without_taxon, without_positions = {}, 0, 0
    for hit in sorted(sheet['hits'], key=lambda item: item['hit_index']):
        taxon, value, closeness, covered = _hit(hit)
        if taxon is None:
            without_taxon += 1
        elif value is None:
            without_positions += 1
        else:
            taxa.setdefault(taxon, []).append({'best_rank': hit['hit_index'], 'closeness': closeness,
                                               'covered_share': covered, 'value': value})
    claims = []
    for taxon, hits in taxa.items():
        best = max(hits, key=lambda row: (row['value'], -row['best_rank']))
        claims.append({'taxon_id': taxon, **_place(taxonomy, taxon), 'hit_count': len(hits), **best})
    return {'schema': SHEET, 'program': search['program'], 'database': search['request']['database'],
            'taxonomy': identity(taxonomy), 'hit_count': len(sheet['hits']), 'hits_without_taxon': without_taxon,
            'hits_without_positions': without_positions,
            'claims': sorted(claims, key=lambda claim: (-claim['value'], claim['taxon_id']))}


def claim_bits(sheet):
    """The bit of each claim of a kept sheet, in the sheet's order: its value, divided by the sum of the values when they
    sum above 1 (the module's description)."""
    over = max(1.0, math.fsum(claim['value'] for claim in sheet['claims']))
    return [claim['value'] / over for claim in sheet['claims']]


def read_search_taxon_claim_sheet(grading):
    """The reader of a kept claim sheet for the scoring sheet of candidate taxa (``taxon_candidates.CLAIM_READERS``):
    ``(sheet name, covers, rows)`` with one row per claim: ``taxon_id``, ``placed``, ``name``, ``rank_code``,
    ``lineage_taxon_ids`` (as the sheet placed it) and ``bit``."""
    sheet = grading['sheet']
    return (FAMILY + ':' + sheet['program'] + ':' + sheet['database'], list(DATABASE_COVERS[database_set(sheet['database'])]),
            [{'taxon_id': claim['taxon_id'], 'placed': claim['placed'], 'name': claim['name'],
              'rank_code': claim['rank_code'], 'lineage_taxon_ids': claim['lineage_taxon_ids'], 'bit': bit}
             for claim, bit in zip(sheet['claims'], claim_bits(sheet))])


__all__ = ['ARCHAEA', 'BACTERIA', 'DATABASE_COVERS', 'FAMILY', 'GRADED_SHEET', 'SHEET', 'claim_bits', 'database_set',
           'read_search_taxon_claim_sheet', 'search_taxon_claim_sheet']
