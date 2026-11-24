"""Where the episode stands, as a pure function of the loop's view: the commission, one row per completed unit (a tool call), the
piece, what the sheets held show (the description, the readings of the protein genes, the RNA scan), the reading reported, the
leading parts and the controller's yield table.

THE PIECE is the scope's one subject, which must be an ``input`` record of the DNA molecule (a wrong commission raises here, where
the record is read). ``piece``: ``ref`` and ``length``. ``description``: the facts of the held description sheet (``None`` before
it is held). ``readings``: one row per gene-finding sheet held (``reading_row``: mode, code, code_applied, gene_count,
median_gene_nt, coding_share, score_sum, where held), in the order held; ``reported``: the held reading of the highest
``score_sum`` (``None`` before one is held); ``rna_scans``: one row per RNA scan held; ``leading_parts``: the leading parts of the
reported reading and the scan (``leading_parts``).

``returned_refs`` are the record lists ``final_to_parent`` returns (``committed_record_refs``: the graded records the credit reads,
and ``data_product_refs``: every held data-product row), each CLOSED UNDER NAMING by ``job_records.returned_with_names`` (the
records chosen with everything they name, recursively, among the held records): the parent holds what a returned record names."""
from gene_annotation_episode.episodic_workflow.episode_support.grading.gene_finding import gene_finding_sheet
from gene_annotation_episode.episodic_workflow.episode_support.grading.rna_gene_finding import rna_gene_sheet
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_composition import description_sheet
from gene_annotation_episode.episodic_workflow.episode_support.grading.tool_grading.tool_grading_artifacts import held_grading_sheets
from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_records import returned_with_names
from gene_annotation_episode.episodic_workflow.episode_support.records.data_products import products
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table

PART_KINDS = ('protein_gene', 'rna_gene')
LEADING_PER_KIND = 10
READING_FIELDS = ('piece_ref', 'mode', 'code', 'code_applied', 'gene_count', 'median_gene_nt', 'coding_share', 'score_sum')


def held_descriptions(records):
    """``[(source reference, sheet)]`` of the description sheets held, in the order held."""
    return held_grading_sheets(records, description_sheet.PROVIDER)


def held_readings(records):
    """The readings held (gene-finding sheets), as ``(source reference, sheet)``, in the order held."""
    return held_grading_sheets(records, gene_finding_sheet.PROVIDER)


def held_rna_scans(records):
    """The RNA scan sheets held, as ``(source reference, sheet)``."""
    return held_grading_sheets(records, rna_gene_sheet.PROVIDER)


def reading_row(source_ref, sheet):
    """One reading without its genes: the sheet's scalars and where it is held."""
    return {'source_ref': source_ref, **{name: sheet[name] for name in READING_FIELDS}}


def reported_reading(rows):
    """The reading the episode reports among ``rows`` (``reading_row``): the highest ``score_sum``, the earliest held on a tie."""
    best = None
    for row in rows:
        if best is None or row['score_sum'] > best['score_sum']:
            best = row
    return best


def rna_parts(sheet):
    """This episode's rule for which hits of an RNA scan sheet are parts: a hit is an ``rna_gene`` unless the program marked it as
    overlapped by a better hit of its clan. An RNA gene's score is its bit score."""
    return [row for row in sheet['hits'] if not row['overlapped']]


def rna_scan_row(source_ref, sheet):
    """One RNA scan without its hits: where it is held, its hit count, and this episode's parts of it (their count and the sum of
    their bit scores)."""
    parts = rna_parts(sheet)
    return {'source_ref': source_ref, 'piece_ref': sheet['piece_ref'], 'hit_count': sheet['hit_count'],
            'part_count': len(parts), 'part_bit_score_sum': sum(row['bit_score'] for row in parts)}


def leading_parts(reading_sheet, rna_sheet):
    """The leading parts: per kind the ``LEADING_PER_KIND`` parts of the highest score first, the protein genes of the reported
    reading, then the RNA genes. Each: ``kind``, ``begin``, ``end``, ``strand``, ``partial_begin``, ``partial_end``, ``score`` and
    for an RNA gene ``family_accession``. An RNA gene runs off an end of the piece where its ``truncation`` says so: on the plus
    strand the 5' end is the beginning, on the minus strand the 3' end is."""
    genes = sorted(reading_sheet['genes'], key=lambda row: -row['score'])[:LEADING_PER_KIND]
    parts = [{'kind': 'protein_gene', 'begin': row['begin'], 'end': row['end'], 'strand': row['strand'],
              'partial_begin': row['partial_begin'], 'partial_end': row['partial_end'], 'score': row['score']} for row in genes]
    if rna_sheet is not None:
        hits = sorted(rna_parts(rna_sheet), key=lambda row: -row['bit_score'])
        beginning = {'+': "5'", '-': "3'"}
        ending = {'+': "3'", '-': "5'"}
        parts.extend({'kind': 'rna_gene', 'begin': row['begin'], 'end': row['end'], 'strand': row['strand'],
                      'partial_begin': row['truncation'] in (beginning[row['strand']], "5'&3'"),
                      'partial_end': row['truncation'] in (ending[row['strand']], "5'&3'"), 'score': row['bit_score'],
                      'family_accession': row['family_accession']} for row in hits[:LEADING_PER_KIND])
    return parts


# What the model is shown of a completed or failed tool unit (the tool's own result fields: numbers, booleans, marks and a failure code).
RESULT_FIELDS = {'describe_piece': ('failure_code', 'length', 'gc_fraction', 'gc_skew', 'window_count'),
                 'find_genes': ('failure_code', 'mode', 'code', 'code_applied', 'gene_count', 'median_gene_nt', 'coding_share',
                                'score_sum'),
                 'find_rna_genes': ('failure_code', 'hit_count')}
DESCRIPTION_FIELDS = ('gc_fraction', 'gc_skew', 'window_count', 'window_gc_min', 'window_gc_max', 'ambiguous_nt')


def internal_summary(view):
    records, parent = view.records, view.parent_input
    units, graded = [], []
    for position, outcome in enumerate(view.outcomes):
        result = outcome['outcome']
        units.append({'position': position, 'kind': 'tool', 'tool': outcome['tool'], 'status': result['status'],
                      'arguments': outcome['arguments'], 'record_refs': list(result['record_refs']),
                      'result': {key: result[key] for key in RESULT_FIELDS[outcome['tool']] if key in result}})
        graded.extend(ref for ref in result['graded_refs'] if ref not in graded)
    (piece_ref,) = parent['scope']['subject_refs']
    piece = records.get(piece_ref)
    if not piece_ref.startswith('input_') or piece['molecule'] != 'dna':
        raise ValueError('parts_subject_must_be_an_input_record_of_dna:' + piece_ref)
    descriptions = held_descriptions(records)
    readings = held_readings(records)
    rna_scans = held_rna_scans(records)
    rows = [reading_row(ref, sheet) for ref, sheet in readings]
    reported = reported_reading(rows)
    sheet_of = {ref: sheet for ref, sheet in readings}
    return {**parent,
            'path_depth': len(view.path),
            'units': units,
            'returned_refs': {name: returned_with_names(records, refs) for name, refs in (
                ('committed_record_refs', graded), ('data_product_refs', [row['id'] for row in products(records)]))},
            'piece': {'ref': piece_ref, 'length': piece['length']},
            'description': None if not descriptions else {'source_ref': descriptions[0][0],
                                                           **{name: descriptions[0][1][name] for name in DESCRIPTION_FIELDS}},
            'readings': rows, 'reported': reported,
            'rna_scans': [rna_scan_row(ref, sheet) for ref, sheet in rna_scans],
            'leading_parts': [] if reported is None else leading_parts(sheet_of[reported['source_ref']],
                                                                       rna_scans[0][1] if rna_scans else None),
            'yield_table': (None if view.controller_state is None
                            else yield_table(view.controller_state, forecast_unit='part_credit'))}
