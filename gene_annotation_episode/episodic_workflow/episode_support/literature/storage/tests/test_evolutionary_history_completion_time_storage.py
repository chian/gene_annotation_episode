"""The completion-time repository on the custody-scoped store: a sheet saved from selected spans of a source,
read back, projected and listed, through the real runner."""
from .evolutionary_history_world import call, read, run, source, world  # noqa: F401

REPOSITORY = 'literature_completion_time_storage:LiteratureCompletionTimeRepository'
TEXT = 'The reaction reached completion after 12 min at 30 C.'
SHEET = {'from_step': 0, 'path': ['result', 'sheet_ref']}


def span(source_ref, piece):
    start = TEXT.index(piece)
    return {'source_ref': source_ref, 'representation': 'original', 'start': start, 'end': start + len(piece),
            'quote': piece}


def selection(source_ref):
    unknown = {'value': 'unknown', 'witnesses': []}
    quantity = {'subject': None, 'construct': None, 'preparation': None, 'condition': None, 'endpoint': None,
                'measurement_identity': None,
                'measurement': {'number': {'witness': span(source_ref, '12'), 'number_start': 0, 'number_end': 2},
                                'unit': span(source_ref, 'min')},
                'qualification': {'value': 'reported_point', 'witnesses': [span(source_ref, '12 min')]}}
    return {'source_ref': source_ref, 'source_kind': 'synthetic_fixture', 'experiment': None, 'intended_change': None,
            'other_changes': [], 'comparison': {'endpoint_relation': unknown, 'preparation_relation': unknown,
                                                'pair_relationship': unknown, 'other_changes_status': unknown},
            'quantities': {'numerator': quantity, 'denominator': None}}


def test_a_completion_time_sheet_is_saved_read_back_and_projected(world):
    saved_source, artifact = source(world, TEXT)
    populated, held, saved, cells, available = run(world, 'completion', [
        call(REPOSITORY, 'populate', selection(saved_source), scope=world['scope']),
        read(REPOSITORY, 'held_sheet_refs'),
        read(REPOSITORY, 'read', SHEET),
        read(REPOSITORY, 'project_cells', [SHEET]),
        read(REPOSITORY, 'cell_record_refs', [])], held=[saved_source, artifact])
    sheet = populated['result']['sheet_ref']
    assert held == [sheet] and saved['input_source_ref'] == saved_source
    assert cells == populated['result']['cells'] and {row['sheet_ref'] for row in cells} == {sheet}
    assert available == []
