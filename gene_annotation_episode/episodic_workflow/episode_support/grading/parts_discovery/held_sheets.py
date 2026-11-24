"""What the parts-discovery head holds: its graded sheets read back from custody, the READING it reports, its leading parts and the
arithmetic of its credit.

A source record of provider ``piece_description``, ``gene_finding`` or ``rna_gene_finding`` carries its retained grading sheet
(``tool_grading_artifacts``); the readers here take the held sources in the order they were held. ``reading_row`` is the sheet of
one reading of the piece's protein genes without its gene rows; the READING THE HEAD REPORTS is the held one with the highest
``score_sum`` (the earliest held on a tie).

THE ANNOTATION SCORES. A protein gene's score is the finder's score for it; an RNA gene's score is its bit score; a reading's score
is its ``score_sum``. They are states, recomputed from what is held.

THE CREDIT (progress, never a score): ``part_units['protein_gene']`` times the highest ``score_sum`` over the readings held (a reading
earns only above zero) plus ``part_units['rna_gene']`` times the sum of the bit scores of the RNA parts held. A second reading earns
only the amount by which it beats the best so far, a repeat earns nothing, and the credit never falls."""
from gene_annotation_episode.episodic_workflow.episode_support.grading.parts_discovery import (
    description_sheet, gene_finding_sheet, rna_gene_sheet)
from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence.tool_grading_artifacts import (
    source_tool_grading_entries)

PART_KINDS = ('protein_gene', 'rna_gene')
LEADING_PER_KIND = 10
READING_FIELDS = ('piece_ref', 'mode', 'code', 'code_applied', 'gene_count', 'median_gene_nt', 'coding_share', 'score_sum')


def piece_sequence(reader, piece_ref):
    """The piece's sequence (upper case) read from the held ``input`` record."""
    return reader.get_artifact(reader.get(piece_ref)['sequence_ref']).decode('ascii').strip().upper()


def held_sheets(records, provider):
    """``[(source reference, sheet)]`` of the held sources of ``provider``, in the order held."""
    found = []
    for source in records.list('source'):
        if source['provider'] != provider:
            continue
        (entry,) = source_tool_grading_entries(records, source['id'])
        found.append((source['id'], entry['grading']['sheet']))
    return found


def reading_row(source_ref, sheet):
    """One reading without its genes: the sheet's scalars and where it is held."""
    return {'source_ref': source_ref, **{name: sheet[name] for name in READING_FIELDS}}


def held_descriptions(records):
    return held_sheets(records, description_sheet.PROVIDER)


def held_readings(records):
    """The readings held, as ``(source reference, sheet)``."""
    return held_sheets(records, gene_finding_sheet.PROVIDER)


def held_rna_scans(records):
    return held_sheets(records, rna_gene_sheet.PROVIDER)


def reported_reading(rows):
    """The reading the head reports among ``rows`` (``reading_row``): the highest ``score_sum``, the earliest held on a tie."""
    best = None
    for row in rows:
        if best is None or row['score_sum'] > best['score_sum']:
            best = row
    return best


def part_credit(part_units, readings, rna_scans):
    """The credit of the held readings (``reading_row`` each) and RNA scans (``rna_scan_row`` each): see the module."""
    protein = max([0.0, *(row['score_sum'] for row in readings)])
    rna = sum(row['part_bit_score_sum'] for row in rna_scans)
    return part_units['protein_gene'] * protein + part_units['rna_gene'] * rna


def rna_scan_row(source_ref, sheet):
    return {'source_ref': source_ref, 'piece_ref': sheet['piece_ref'], 'hit_count': sheet['hit_count'],
            'part_count': sheet['part_count'], 'part_bit_score_sum': sheet['part_bit_score_sum']}


def leading_parts(reading_sheet, rna_sheet):
    """The leading parts: per kind the ``LEADING_PER_KIND`` parts of the highest score first, the protein genes of the reported
    reading, then the RNA genes. Each: ``kind``, ``begin``, ``end``, ``strand``, ``partial_begin``, ``partial_end``, ``score`` and
    for an RNA gene ``family_accession``. An RNA gene runs off an end of the piece where its ``truncation`` says so: on the plus
    strand the 5' end is the beginning, on the minus strand the 3' end is."""
    genes = sorted(reading_sheet['genes'], key=lambda row: -row['score'])[:LEADING_PER_KIND]
    parts = [{'kind': 'protein_gene', 'begin': row['begin'], 'end': row['end'], 'strand': row['strand'],
              'partial_begin': row['partial_begin'], 'partial_end': row['partial_end'], 'score': row['score']} for row in genes]
    if rna_sheet is not None:
        hits = sorted((row for row in rna_sheet['hits'] if not row['overlapped']), key=lambda row: -row['bit_score'])
        beginning = {'+': "5'", '-': "3'"}
        ending = {'+': "3'", '-': "5'"}
        parts.extend({'kind': 'rna_gene', 'begin': row['begin'], 'end': row['end'], 'strand': row['strand'],
                      'partial_begin': row['truncation'] in (beginning[row['strand']], "5'&3'"),
                      'partial_end': row['truncation'] in (ending[row['strand']], "5'&3'"), 'score': row['bit_score'],
                      'family_accession': row['family_accession']} for row in hits[:LEADING_PER_KIND])
    return parts


__all__ = ['LEADING_PER_KIND', 'PART_KINDS', 'READING_FIELDS', 'held_descriptions', 'held_readings', 'held_rna_scans', 'held_sheets',
           'leading_parts', 'part_credit', 'piece_sequence', 'reading_row', 'reported_reading', 'rna_scan_row']
