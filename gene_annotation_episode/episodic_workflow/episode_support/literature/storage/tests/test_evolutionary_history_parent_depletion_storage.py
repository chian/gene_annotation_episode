"""The parent-depletion repository on the custody-scoped store: a sheet saved from a workbook row, read back,
projected and listed, through the real runner."""
from hashlib import sha256

from .evolutionary_history_world import call, function, read, run, source, world  # noqa: F401
from .xlsx_fixture import MEDIA_TYPE, workbook

REPOSITORY = 'literature_parent_depletion_storage:LiteratureParentDepletionRepository'
HEADERS = {'A': 'Time', 'B': 'Bio', 'C': 'Stdev1', 'D': 'Ab', 'E': 'Stdev2', 'F': 'inactive_enzyme', 'G': 'Stdev3',
           'I': 'Compound', 'J': 'Submix', 'K': 'Difference_dead_enzyme', 'L': 'Difference_abio'}
ROW = {'A': 24, 'B': 0.5, 'C': 0.1, 'D': 0.9, 'E': 0.05, 'F': 1.0, 'G': 0.2, 'I': 'ParentX', 'J': 'Mix1', 'K': -0.5,
       'L': -0.4}
SHEET = {'from_step': 0, 'path': ['result', 'sheet_ref']}


def selection(world_source, data):
    return {'version': 'a105_parent_depletion_xlsx_selection_v1', 'source_ref': world_source,
            'expected_sha256': sha256(data).hexdigest(), 'sheet_name': 'Data', 'compound': 'ParentX',
            'submix': 'Mix1', 'time_hours': 24}


def test_a_parent_depletion_sheet_is_saved_read_back_and_projected(world):
    data = workbook({'Data': {1: HEADERS, 2: ROW}})
    saved_source, artifact = source(world, data, MEDIA_TYPE)
    populated, held, saved, available, cells = run(world, 'depletion', [
        call(REPOSITORY, 'populate', selection(saved_source, data), scope=world['scope']),
        read(REPOSITORY, 'held_sheet_refs'),
        read(REPOSITORY, 'read', SHEET),
        read(REPOSITORY, 'available_sheet_refs', {}),
        read(REPOSITORY, 'project_cells', [SHEET])], held=[saved_source, artifact])
    sheet = populated['result']['sheet_ref']
    assert held == [sheet] and available == [sheet]
    assert saved['input_source_ref'] == saved_source and saved['extraction']['row_number'] == 2
    assert {row['sheet_ref'] for row in cells} == {sheet}
    assert len(cells) == len(populated['result']['cells']) > 0
    assert cells == populated['result']['cells']
