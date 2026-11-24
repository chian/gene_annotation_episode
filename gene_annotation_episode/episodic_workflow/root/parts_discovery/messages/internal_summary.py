"""Where the episode stands, as a pure function of the loop's view: the commission, one row per completed unit (a tool call), the
piece, what the sheets held show (the description, the readings of the protein genes, the RNA scan), the reading reported, the
leading parts and the controller's yield table.

THE PIECE is the scope's one subject, which must be an ``input`` record of the DNA molecule (a wrong commission raises here, where
the record is read). ``piece``: ``ref`` and ``length``. ``description``: the facts of the held description sheet (``None`` before
it is held). ``readings``: one row per gene-finding sheet held (``held_sheets.reading_row``: mode, code, code_applied, gene_count,
median_gene_nt, coding_share, score_sum, where held), in the order held; ``reported``: the held reading of the highest
``score_sum`` (``None`` before one is held); ``rna_scans``: one row per RNA scan held; ``leading_parts``: the leading parts of the
reported reading and the scan (``held_sheets.leading_parts``).

``returned_refs`` are the record lists ``final_to_parent`` returns (``committed_record_refs``: the graded records the credit reads,
and ``data_product_refs``: every held data-product row), each CLOSED UNDER NAMING by ``job_records.returned_with_names`` (the
records chosen with everything they name, recursively, among the held records): the parent holds what a returned record names."""
from gene_annotation_episode.episodic_workflow.episode_support.grading.parts_discovery.held_sheets import (
    held_descriptions, held_readings, held_rna_scans, leading_parts, reading_row, reported_reading, rna_scan_row)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_records import returned_with_names
from gene_annotation_episode.episodic_workflow.episode_support.records.data_products import products
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table

# What the model is shown of a completed or failed tool unit (the tool's own result fields: numbers, booleans, marks and a failure code).
RESULT_FIELDS = {'describe_piece': ('failure_code', 'length', 'gc_fraction', 'gc_skew', 'window_count'),
                 'find_genes': ('failure_code', 'mode', 'code', 'code_applied', 'gene_count', 'median_gene_nt', 'coding_share',
                                'score_sum'),
                 'find_rna_genes': ('failure_code', 'hit_count', 'part_count', 'part_bit_score_sum')}
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
