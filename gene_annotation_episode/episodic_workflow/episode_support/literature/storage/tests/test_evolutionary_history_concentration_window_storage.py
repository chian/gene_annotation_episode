"""The concentration-window repository on the custody-scoped store: population from the retained figure workbook
and page of the matched-estimator case, the saved sheet read back and its requested cells projected, through the
real runner."""
import json
from pathlib import Path

from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.evolutionary_history_evidence.literature_concentration_window_storage import POPULATION, REQUESTED

from .evolutionary_history_world import call, read, run, world  # noqa: F401
from .test_evolutionary_history_endpoint_signal_storage import bound, retained

INPUTS = Path(__file__).resolve().parents[2] / 'inputs/experimental_activity_evidence/tests/fixtures'
CASE = INPUTS / 'research_reference/a105_matched_estimator_source_260/originals'
REPOSITORY = 'literature_concentration_window_storage:LiteratureConcentrationWindowRepository'
SHEET = {'from_step': 0, 'path': ['result', 'sheet_ref']}
REQUESTED_CELLS = ['substrate_loss', 'coordinate_span', 'fate_fraction']


def test_a_concentration_window_sheet_is_saved_read_back_and_its_cells_projected(world):  # noqa: F811
    selection = json.loads((INPUTS / 'concentration_window/SOURCE_SELECTION_PROPOSAL_002.json').read_text())
    workbook, workbook_artifacts = retained(world, (CASE / 'elife65773_fig6.xlsx').read_bytes(),
                                            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    page, page_artifacts = retained(world, (CASE / 'elife65773.html').read_bytes(), 'text/html')
    selection = bound({**selection, 'requested_cells': REQUESTED_CELLS},
                      {'source:elife65773_original_fig6_xlsx': workbook, 'source:elife65773_original_html': page})
    arguments = {'version': POPULATION, 'selection': selection,
                 'return_context': []}
    populate = call(REPOSITORY, 'populate', arguments, scope=world['scope'], assignment={REQUESTED: REQUESTED_CELLS})
    populate['arguments']['role'] = 'reader'
    populated, held, saved, cells = run(world, 'window', [populate,
        read(REPOSITORY, 'held_sheet_refs'),
        read(REPOSITORY, 'read', SHEET),
        read(REPOSITORY, 'project_cells', [SHEET], components=REQUESTED_CELLS)],
        held=[workbook, page, *workbook_artifacts, *page_artifacts])
    sheet = populated['result']['sheet_ref']
    assert populated['status'] == 'completed' and held == [sheet]
    assert saved['input_source_ref'] == workbook
    assert [cell['component'] for cell in cells] == REQUESTED_CELLS
    assert {cell['sheet_ref'] for cell in cells} == {sheet}
