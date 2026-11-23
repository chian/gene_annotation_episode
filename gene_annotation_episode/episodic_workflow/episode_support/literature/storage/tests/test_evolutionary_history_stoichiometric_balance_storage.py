"""The stoichiometric-balance repository on the custody-scoped store: a sheet saved from one time point of a
workbook, read back, projected and listed, through the real runner."""
from hashlib import sha256

from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.evolutionary_history_evidence.literature_stoichiometric_balance_inputs import (
    HEADERS, MODEL_PREMISE)

from .evolutionary_history_world import call, read, run, source, world  # noqa: F401
from .xlsx_fixture import MEDIA_TYPE, workbook

REPOSITORY = 'literature_stoichiometric_balance_storage:LiteratureStoichiometricBalanceRepository'
SHEET = {'from_step': 0, 'path': ['result', 'sheet_ref']}
CALIBRATION = ('Calibration: G2 (2.5-50 mM), G3/G4 (2.5-15 mM), G5 (1.0-7.5 mM) and G6 (1.0-2.5 mM) were '
               'quantified against standards.')


def data_rows():
    rows = {50: {'A': 'Experiment D'}, 51: {column + '': label for column, label in HEADERS.items()}}
    zero = {'A': 0, 'M': 0, 'B': 20, 'D': 0, 'F': 0, 'H': 0, 'J': 0, 'N': 0}
    point = {'A': 30, 'M': 30, 'B': 10, 'C': 0.5, 'D': 3, 'E': 0.2, 'F': 4, 'G': 0.2, 'H': 2, 'I': 0.1, 'J': 1.5,
             'K': 0.1, 'N': 9, 'O': 0.3}
    return {**rows, 52: zero, 53: point}


def metadata_rows():
    return {3: {'F': 'Experiment D'}, 4: {'A': 'aGlc1-P', 'B': 'mM', 'F': 20}, 5: {'A': 'Cellobiose (G2)', 'B': 'mM', 'F': 20},
            6: {'A': 'Cellodextrin phosphorylase from Clostridium cellulosi', 'B': 'U/mL', 'F': 1},
            7: {'A': 'MES buffer', 'B': 'mM', 'F': 50}, 8: {'A': 'pH', 'B': None, 'F': '7.0'},
            9: {'A': 'Temperature', 'B': '°C', 'F': 45}, 16: {'A': 'Each reaction was carried out in duplicates.'},
            22: {'A': CALIBRATION}, 23: {'A': 'Pi was measured by a colorimetric assay.'}, 29: {'A': MODEL_PREMISE}}


def test_a_stoichiometric_balance_sheet_is_saved_read_back_and_projected(world):
    data = workbook({'Data': data_rows(), 'Metadata': metadata_rows()})
    saved_source, artifact = source(world, data, MEDIA_TYPE)
    selection = {'version': 'a105_stoichiometric_balance_xlsx_selection', 'source_ref': saved_source,
                 'expected_sha256': sha256(data).hexdigest(), 'sheet_name': 'Data', 'panel': 'D', 'row_number': 53,
                 'time_minutes': 30}
    populated, held, saved, cells = run(world, 'balance', [
        call(REPOSITORY, 'populate', selection, scope=world['scope']),
        read(REPOSITORY, 'held_sheet_refs'),
        read(REPOSITORY, 'read', SHEET),
        read(REPOSITORY, 'project_cells', [SHEET])], held=[saved_source, artifact])
    sheet = populated['result']['sheet_ref']
    assert held == [sheet]
    assert saved['input_source_ref'] == saved_source and saved['extraction']['row_number'] == 53
    assert cells == populated['result']['cells'] and {row['sheet_ref'] for row in cells} == {sheet}
