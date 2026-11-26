"""The converter of one graded ``cmscan`` scan of a nucleotide sequence into feature calls: the subscoring sheet of the scan
(``infernal_feature_call_sheet``) and the rows the sheet of feature calls reads from it.

WHAT IT READS. The kept sheet of one scan by the shared ``rna_family_scan`` (``rna_family_scan_sheet``, schema
``a102_rna_family_scan_sheet``): Infernal 1.1.5 ``cmscan`` over the covariance models of a database (Rfam), by Rfam's
documented command for annotating a sequence, with ``--cut_ga`` (every hit at or above its family's gathering threshold GA),
both strands searched, and the table in format 2. Per hit the sheet holds its rank, the family's accession and name, its clan,
the positions on the searched sequence (``seq_from``, ``seq_to``: one-based, both included; on the minus strand ``seq_from`` is
the higher), the strand, the truncation mark, the span on the model (``model_from``, ``model_to``, ``model_length``), the bit
score, the family's GA, the value of the hit and the overlap mark of the table.

THE STATEMENTS. A covariance model is fitted to the whole of a structured RNA, so a hit states the RNA itself, where it starts
and where it ends: it is a FEATURE CALL (``feature_candidates``), except at an end where Infernal marks it cut off.

* Positions: zero-based, the end not included, ``start`` the lower position whatever the strand
  (``start = min(seq_from, seq_to) - 1``, ``end = max(seq_from, seq_to)``). When the searched sequence was derived from the
  sequence the statements are about (an extracted stretch: ``searched_mapping``, the ``mapping`` of its record), the
  positions are carried back by its own mapping (``sequence_mapping.map_interval``) and the strand is turned round when the
  stretch was read from the other strand.
* Ends: Infernal marks a hit cut off by an end of the searched sequence (``trunc``: ``no``, ``5'``, ``3'``, ``5'&3'``;
  Infernal user guide, ``tabular.tex``, field 11). A hit claims an end only when it is not cut off there: its 5' end is the
  lower position on the ``+`` strand and the upper on ``-``, its 3' end the other. A hit cut off at one end is a claim with
  the other end; cut off at both, an interior claim. The span on the model is kept with each statement: in Infernal's
  default local mode a hit that is not marked cut off can still begin after the first or end before the last position of
  its model; whether that should withhold an end is not decided here.
* Overlaps: a hit marked ``=`` overlaps a better hit (a lower E-value) that is itself the best of the hits it overlaps
  (``^``); Infernal's own guide for annotating a genome removes the hits marked ``=`` (``tutorial.tex``: "remove any hits
  with '=' in the 'olp' column", the same hits ``--oskip`` omits). They are left out of the statements and counted
  (``overlapped_left_out``). The command has no ``--oclan``, so Infernal marks an overlap between hits of ANY two families
  on one strand, not only of one clan (``tabular.tex``, ``olp``). A hit marked ``$`` overlaps only better hits that are
  not marked ``^``; it is a statement and counted (``overlapped_kept``). The shared scan sheet's own
  ``overlapped_by_a_better_hit_of_the_clan`` is true for both ``$`` and ``=`` and is not read here.
* Kind: ``tRNA`` or ``rRNA`` for the families of ``RFAM_FAMILY_KIND`` (each confirmed by its exact name in the family index of
  Rfam 15.1, ``Rfam.index.json``), ``ncRNA`` for every other family. Rfam's own table of family types (which families are
  genes, and which are cis-regulatory elements such as riboswitches and leaders, or other structures) is not on disk: the
  release installed holds the models, the clan file and the index of names, lengths and thresholds only. Until that table is
  entered, a cis-regulatory family is stated as ``ncRNA``. The owner will help extend the table.
* Value (``bit``): the value the shared sheet gives the hit (``rna_family_scan_sheet.value_of``: ``x^2 / (1 + x^2)`` with ``x``
  the bit score over the family's GA; one half at GA, rising gradually towards one).

The sheet name is ``family_model:cmscan:<database name>:<database version>`` (family of technique ``family_model``) and the
sheet can speak of ``tRNA``, ``rRNA`` and ``ncRNA``.

WORDS. The query is the sequence the root was given; what a scan is run on is the SEARCHED SEQUENCE. The shared sheet calls it
``query_ref`` after its own field; here it is ``searched_ref``.

No I/O: this module reads a grading and returns values."""
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_features.feature_candidates import (
    READERS, SHEET_WEIGHT)
from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence.rna_family_scan_sheet import (
    SCHEMA as SCAN_SHEET)
from gene_annotation_episode.episodic_workflow.episode_support.readers.sequence_operations.sequence_mapping import (
    map_interval)
from gene_annotation_episode.episodic_workflow.episode_support.tools.structure_search.structural_homology_evidence.rna_family_scan import (
    PROGRAM)

SHEET = 'infernal_feature_call_sheet'
FAMILY = 'family_model'
COVERS = ('tRNA', 'rRNA', 'ncRNA')
OTHER_FAMILY_KIND = 'ncRNA'
# The overlap mark of a hit Infernal's annotation guide removes, and the mark of one it keeps though a better hit overlaps it.
LEFT_OUT_MARK, KEPT_OVERLAPPED_MARK = '=', '$'
# The truncation marks of a hit cut off at its 5' end and at its 3' end.
CUT_AT_FIVE, CUT_AT_THREE = ("5'", "5'&3'"), ("3'", "5'&3'")
# Rfam families stated as tRNA or rRNA: accession -> (the family's exact name in ``Rfam.index.json`` of Rfam 15.1, our type).
# Read 2026-11-25 from the index. Families whose names suggest it but do not say it are not entered: RF02545
# ``SSU_trypano_mito`` and RF02546 ``LSU_trypano_mito`` (subunits of the trypanosome mitochondrial ribosome by Rfam's
# naming); the tmRNA families (a tRNA-like and mRNA-like RNA, not a tRNA); RF00233 ``Tymo_tRNA-like`` (a structure of a virus
# genome); the ``xrRNA`` families (exoribonuclease-resistant RNAs, not ribosomal).
RFAM_FAMILY_KIND = {
    'RF00005': ('tRNA', 'tRNA'),
    'RF01852': ('tRNA-Sec', 'tRNA'),
    'RF00001': ('5S_rRNA', 'rRNA'),
    'RF00002': ('5_8S_rRNA', 'rRNA'),
    'RF00177': ('SSU_rRNA_bacteria', 'rRNA'),
    'RF01959': ('SSU_rRNA_archaea', 'rRNA'),
    'RF01960': ('SSU_rRNA_eukarya', 'rRNA'),
    'RF02542': ('SSU_rRNA_microsporidia', 'rRNA'),
    'RF02540': ('LSU_rRNA_archaea', 'rRNA'),
    'RF02541': ('LSU_rRNA_bacteria', 'rRNA'),
    'RF02543': ('LSU_rRNA_eukarya', 'rRNA'),
}


def rfam_family_kind(accession):
    """Our type of an Rfam family (the module's description)."""
    return RFAM_FAMILY_KIND[accession][1] if accession in RFAM_FAMILY_KIND else OTHER_FAMILY_KIND


def _on_the_subject(row, searched_mapping):
    """``(segments, strand)`` of a hit on the sequence the statements are about (the module's description)."""
    start, end = min(row['seq_from'], row['seq_to']) - 1, max(row['seq_from'], row['seq_to'])
    if searched_mapping is None:
        return [{'start': start, 'end': end}], row['strand']
    path = map_interval(searched_mapping, start, end)
    strand = row['strand'] if path[0]['strand'] == '+' else {'+': '-', '-': '+'}[row['strand']]
    return sorted(({'start': part['start'], 'end': part['end']} for part in path), key=lambda part: part['start']), strand


def hit_statement(row, searched_mapping=None):
    """What one hit of the scan sheet states (the module's description)."""
    segments, strand = _on_the_subject(row, searched_mapping)
    five, three = row['truncation'] not in CUT_AT_FIVE, row['truncation'] not in CUT_AT_THREE
    return {'rank': row['rank'], 'family_accession': row['family_accession'], 'family_name': row['family_name'],
            'clan': row['clan'], 'kind': rfam_family_kind(row['family_accession']), 'strand': strand, 'segments': segments,
            'claims_start': five if strand == '+' else three, 'claims_end': three if strand == '+' else five,
            'truncation': row['truncation'], 'model_from': row['model_from'], 'model_to': row['model_to'],
            'model_length': row['model_length'], 'overlap_mark': row['overlap_mark'], 'bit_score': row['bit_score'],
            'ga': row['ga'], 'bit': row['value']}


def infernal_call_sheet(grading, searched_mapping=None):
    """The subscoring sheet of one graded scan (``grading``: the retained grading of ``rna_family_scan``, ``{'sheet'}``):
    ``{'schema', 'program', 'database', 'database_version', 'searched_ref', 'searched_length', 'hit_count',
    'overlapped_left_out', 'overlapped_kept', 'statements'}`` with one statement per hit not left out, in the order of rank.
    ``searched_mapping`` is the mapping of the searched sequence when it was derived from the sequence the statements are
    about."""
    sheet = grading['sheet']
    rows = sheet['rows']
    return {'schema': SHEET, 'program': PROGRAM, 'database': sheet['database'],
            'database_version': sheet['database_version'], 'searched_ref': sheet['query_ref'],
            'searched_length': sheet['query_length'], 'hit_count': sheet['hit_count'],
            'overlapped_left_out': sum(row['overlap_mark'] == LEFT_OUT_MARK for row in rows),
            'overlapped_kept': sum(row['overlap_mark'] == KEPT_OVERLAPPED_MARK for row in rows),
            'statements': [hit_statement(row, searched_mapping) for row in rows if row['overlap_mark'] != LEFT_OUT_MARK]}


def read_call_sheet(grading):
    """The reader of a kept call sheet for the sheet of feature calls (``feature_candidates.READERS``): ``(sheet name,
    covers, rows)``, one row per statement with the feature record that states it."""
    sheet = grading['sheet']
    return (FAMILY + ':' + sheet['program'] + ':' + sheet['database'] + ':' + sheet['database_version'], list(COVERS),
            [{'kind': statement['kind'], 'strand': statement['strand'], 'segments': statement['segments'],
              'claims_start': statement['claims_start'], 'claims_end': statement['claims_end'],
              'feature_ref': statement['feature_ref'], 'bit': statement['bit']}
             for statement in sheet['statements']])


# Entered into the sheet of feature calls when this module is imported: the reader of the kept call sheet, and the weight of
# its family of technique. A hit's value lies in [0.5, 1), so the weight is 1. A starting value of 2026-11-25 with no run
# behind it.
READERS[SHEET] = read_call_sheet
SHEET_WEIGHT[FAMILY] = 1.0

__all__ = ['COVERS', 'FAMILY', 'OTHER_FAMILY_KIND', 'RFAM_FAMILY_KIND', 'SCAN_SHEET', 'SHEET', 'hit_statement',
           'infernal_call_sheet', 'read_call_sheet', 'rfam_family_kind']
