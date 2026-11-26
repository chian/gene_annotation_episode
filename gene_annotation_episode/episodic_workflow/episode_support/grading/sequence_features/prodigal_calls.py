"""The converter of one graded run of the gene finder Prodigal (Pyrodigal) on a nucleotide sequence into statements about
its features: the call sheet of the run (``prodigal_feature_call_sheet``) and the rows the sheet of feature calls reads
from it.

The grader (``prodigal_grader.grade_prodigal``) states the facts of every gene the finder called: its interval and strand
on the searched sequence, whether it runs off the lower or the upper edge of that sequence, its protein, the finder's
confidence and score, and the stops in the protein. A gene finder states a gene WITH ITS ENDS: where it starts and where
it stops. Where a gene runs off an edge of the searched sequence, the finder does not say where it starts or ends on that
side: the gene goes on past what was searched.

So each gene is one statement of a coding sequence (``CDS``, ``feature_types.CODING``) on its strand, at its positions,
and it claims an end only on a side where it does not run off the edge:

* ``claims_start`` (the end at the LOWER position) is true when the gene does not run off the lower edge;
* ``claims_end`` (the end at the UPPER position) is true when the gene does not run off the upper edge.

A gene with both is a FEATURE CALL; a gene with one or none is a CLAIM (``feature_candidates``).

FACTS OF THE INSTALLED PYRODIGAL (3.7.1, ``.venv/lib/python3.12/site-packages/pyrodigal/lib.pyx``), read on 2026-11-25:

* The edges are those of the sequence, not of the gene's reading: ``Gene.partial_begin`` is "Whether the gene overlaps
  with the start of the sequence" and ``Gene.partial_end`` "with the end of the sequence" (lines 2662-2678). On the plus
  strand they read the edge flag of the start codon's node and of the stop codon's node; on the minus strand the other way
  round (``partial_begin`` reads the stop node, ``partial_end`` the start node). On either strand, then,
  ``partial_begin`` is the lower-coordinate edge and ``partial_end`` the upper one, and they map to ``claims_start`` and
  ``claims_end`` as above without regard to the strand. (``sequence_ops.predict_genes`` returns them as they are,
  ``sequence_ops.py`` line 104.)
* The coordinates of a gene are one-based and the end is included (lines 2614-2618); ``sequence_ops.predict_genes``
  turns them into zero-based positions with the end not included (``start = begin - 1``, ``end = end``,
  ``sequence_ops.py`` line 102).
* The interval of a complete gene INCLUDES ITS STOP CODON. On the plus strand the gene's end is the stop node's position
  plus 3 (line 3255), on the minus strand its begin is the stop node's position minus 1 (line 3266). The translation shows
  it: ``Gene.translate`` translates every codon of the interval (``nucl_length // 3``, line 3012) and takes the stop off
  only when asked not to include it (``include_stop=False``) and the stop is not at an edge (lines 3024-3026);
  ``predict_genes`` calls it with the default ``include_stop=True`` (line 2936; ``sequence_ops.py`` line 105). So a
  complete gene's protein ends in ``*`` and its interval is three times the protein's symbols (as the grader checks,
  ``prodigal_grader.py`` line 106). A gene that runs off the edge where its reading ends (the upper edge on the plus
  strand, the lower on the minus) has no stop codon in it.
* The finder calls no gene shorter than 90 letters, nor one shorter than 60 letters at an edge, and lets two genes share
  at most 60 letters (the defaults of ``GeneFinder``: line 5116).
* ``Gene.confidence`` is a percentage from 0 to 100 computed from the gene's score (line 2861).

The value a statement carries into the feature calls (``bit``) is the finder's confidence as a share: confidence / 100.
A starting rule of 2026-11-25 with no run behind it. The other facts (score, protein length, internal stops, the stop at
the end) are kept for the grading of the statements as they are refined.

The searched sequence can be the sequence the statements are about, or a nucleotide sequence derived from it (an
extracted stretch, a reverse complement, a spliced sequence: its record has a ``mapping``). The positions of each gene on
the searched sequence are then carried back by that mapping (``sequence_mapping.map_interval``), as
``blast_claims._on_the_subject`` does: the strand flips when the mapping's path runs on the minus strand of that sequence,
and so do the two edges (the lower edge of the searched sequence is then the upper position of the sequence it came
from).

No I/O: this module reads a grading and returns values."""
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_features.feature_candidates import (
    ALTERNATIVES, READERS, SHEET_WEIGHT)
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_features.feature_types import CODING
from gene_annotation_episode.episodic_workflow.episode_support.readers.sequence_operations.sequence_mapping import (
    map_interval)

SHEET = 'prodigal_feature_call_sheet'
GRADED_SHEET = 'prodigal_sheet'
PROGRAM = 'pyrodigal'
# The family of technique: a gene finder reads the signal of the sequence itself (codon usage, start codons, ribosome
# binding sites), not its likeness to known sequences.
FAMILY = 'sequence_signal'
FLIP = {'+': '-', '-': '+'}


def _on_the_subject(start, end, strand, partial_begin, partial_end, searched_mapping):
    """``(segments, strand, claims_start, claims_end)`` of a gene at ``[start, end)`` on ``strand`` of the searched
    sequence, on the sequence the statements are about: the searched sequence itself, or the sequence its mapping
    (``searched_mapping``) carries the interval back to (the module's description)."""
    if searched_mapping is None:
        return [{'start': start, 'end': end}], strand, not partial_begin, not partial_end
    path = map_interval(searched_mapping, start, end)
    along = path[0]['strand'] == '+'
    segments = sorted(({'start': row['start'], 'end': row['end']} for row in path), key=lambda segment: segment['start'])
    if along:
        return segments, strand, not partial_begin, not partial_end
    return segments, FLIP[strand], not partial_end, not partial_begin


def prodigal_call_sheet(grading, *, code, mode, searched_mapping=None):
    """The call sheet of one graded run (``grade_prodigal``): ``{'schema', 'program', 'pyrodigal_version', 'code', 'mode',
    'searched_length', 'gene_count', 'genes'}`` with one row per gene in the finder's order: its ``kind`` (``CDS``),
    ``strand``, ``segments``, ``claims_start`` and ``claims_end`` on the sequence the statements are about; its
    ``searched_interval`` and ``searched_strand`` on the searched sequence, and the finder's ``partial_begin`` and
    ``partial_end`` there (it runs off the lower, the upper edge); the finder's ``confidence`` (percent) and ``score``;
    ``protein_length`` (amino-acid symbols, the stop not counted), ``internal_stop_count`` and ``terminal_stop``.
    ``code`` and ``mode`` are the genetic code and the mode of the run; ``searched_mapping`` is the mapping of the
    searched sequence when it was derived from the sequence the statements are about."""
    genes = []
    for row in grading['scores']['candidates']:
        start, end = row['relative_interval']
        segments, strand, claims_start, claims_end = _on_the_subject(
            start, end, row['strand'], row['partial_begin'], row['partial_end'], searched_mapping)
        genes.append({
            'index': row['candidate_index'], 'kind': CODING, 'strand': strand, 'segments': segments,
            'claims_start': claims_start, 'claims_end': claims_end,
            'searched_interval': [start, end], 'searched_strand': row['strand'],
            'partial_begin': row['partial_begin'], 'partial_end': row['partial_end'],
            'confidence': row['native_confidence_percent'], 'score': row['native_score'],
            'protein_length': row['protein_length_aa'], 'internal_stop_count': row['internal_stop_count'],
            'terminal_stop': row['terminal_stop']})
    return {'schema': SHEET, 'program': PROGRAM, 'pyrodigal_version': grading['sheet']['pyrodigal_version'],
            'code': code, 'mode': mode, 'searched_length': grading['sheet']['input_length'], 'gene_count': len(genes),
            'genes': genes}


def call_bit(gene):
    """The value a gene carries into the feature calls: the finder's confidence as a share (the module's description)."""
    return gene['confidence'] / 100


def read_call_sheet(grading):
    """The reader of a kept call sheet for the sheet of feature calls (``feature_candidates.READERS``): ``(sheet name,
    covers, rows)``. The sheet name is ``sequence_signal:prodigal:<code>:<mode>``; a gene finder can speak of coding
    sequences only; one row per gene, with the feature record that states it."""
    sheet = grading['sheet']
    return (FAMILY + ':prodigal:' + str(sheet['code']) + ':' + sheet['mode'], [CODING],
            [{'kind': gene['kind'], 'strand': gene['strand'], 'segments': gene['segments'],
              'claims_start': gene['claims_start'], 'claims_end': gene['claims_end'], 'feature_ref': gene['feature_ref'],
              'bit': call_bit(gene)}
             for gene in sheet['genes']])


# Entered into the sheet of feature calls when this module is imported: the reader of the kept call sheet, and the weight
# of the family of technique a gene finder belongs to. The bit is the finder's confidence as a share, so the weight is 1.
# A starting value of 2026-11-25 with no run behind it.
READERS[SHEET] = read_call_sheet
SHEET_WEIGHT[FAMILY] = 1.0
# A gene finding is made under one genetic code, and a sequence has one: findings under different codes are alternatives
# (``feature_candidates.ALTERNATIVES``), never added together.
ALTERNATIVES[SHEET] = lambda grading: ('genetic_code', str(grading['sheet']['code']))

__all__ = ['FAMILY', 'GRADED_SHEET', 'PROGRAM', 'SHEET', 'call_bit', 'prodigal_call_sheet', 'read_call_sheet']
