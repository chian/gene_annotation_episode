"""The relative-signal sheet repository on the custody-scoped store: population from a JATS comparison sentence, the
saved sheet read back and its cells projected, through the real runner."""
from .evolutionary_history_world import call, read, run, source, world  # noqa: F401

JATS = ('<article><body><sec id="s1"><p>GeneX protein was 45% (mutant) of wild type in the strain.</p></sec>'
        '</body></article>')
RATIO = 'literature_ratio_storage:LiteratureRatioRepository'
SHEET = {'from_step': 0, 'path': ['result', 'sheet_ref']}


def test_a_relative_signal_sheet_is_saved_read_back_and_projected(world):
    table, artifact = source(world, JATS, 'application/xml')
    arguments = {'source_ref': table, 'source_kind': 'primary_jats', 'section_id': 's1', 'paragraph_index': 0,
                 'subject': 'GeneX', 'variant': 'mutant', 'reference_literal': 'wild type',
                 'visual_source_refs': [], 'signal_kind': 'unknown', 'reference_role': 'unknown',
                 'arrangement': 'unknown', 'interpretation_witnesses': []}
    populated, held, saved, cells = run(world, 'ratio', [
        call(RATIO, 'populate', arguments, scope=world['scope']),
        read(RATIO, 'held_sheet_refs'),
        read(RATIO, 'read', SHEET),
        read(RATIO, 'project_cells', [SHEET])], held=[table, artifact])
    sheet = populated['result']['sheet_ref']
    assert populated['status'] == 'completed' and held == [sheet]
    assert saved['input_source_ref'] == table
    assert saved['comparison']['variant'] == 'mutant' and saved['comparison']['reference_literal'] == 'wild type'
    assert {row['sheet_ref'] for row in cells} == {sheet}
    assert 0.45 in [value for row in cells for value in row['value_candidates']]
