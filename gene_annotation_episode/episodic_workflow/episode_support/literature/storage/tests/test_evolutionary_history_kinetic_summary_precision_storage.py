"""The kinetic summary-precision repository on the custody-scoped store: population from the retained synthetic
sources of the summary-precision fixtures, the saved sheet read back and its requested cells projected, through
the real runner."""
from copy import deepcopy
import json
from pathlib import Path

from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.evolutionary_history_evidence.literature_kinetic_summary_precision_storage import COMPONENTS, POPULATION, REQUESTED, SUMMARY_PRECISION_REQUEST_SCHEMA_V1

from .evolutionary_history_world import call, read, run, source, world  # noqa: F401

FIXTURES = (Path(__file__).resolve().parents[2]
            / 'calculations/experimental_activity_evidence/tests/fixtures/kinetic_summary_precision')
PLACEHOLDER = '@synthetic248'
REPOSITORY = 'literature_kinetic_summary_precision_storage:LiteratureKineticSummaryPrecisionRepository'
SHEET = {'from_step': 0, 'path': ['result', 'sheet_ref']}


def bound(value, reference):
    if isinstance(value, dict):
        return {key: bound(item, reference) for key, item in value.items()}
    if isinstance(value, list):
        return [bound(item, reference) for item in value]
    return reference if value == PLACEHOLDER else value


def test_a_summary_precision_sheet_is_saved_read_back_and_its_cells_projected(world):  # noqa: F811
    case = 'fully_units_known'
    packet = next(item for item in json.loads((FIXTURES / 'SYNTHETIC_PARTIAL_IO_002.json').read_text())
                  if item['case'] == case)
    text = json.loads((FIXTURES / 'SYNTHETIC_FULLY_UNITS_KNOWN_SOURCE_002.json').read_text())['text']
    reference, artifact = source(world, text, 'text/plain')
    requested = list(COMPONENTS)[:3]
    arguments = {'version': POPULATION, 'selection': bound(deepcopy(packet['selection']), reference),
                 'requested_cells': requested,
                 'return_context': {name: [] for name in SUMMARY_PRECISION_REQUEST_SCHEMA_V1['properties']['return_context']['properties']}}
    populate = call(REPOSITORY, 'populate', arguments, scope=world['scope'], assignment={REQUESTED: requested})
    populate['arguments']['role'] = 'reader'
    populated, held, saved, cells = run(world, 'summary_precision', [populate,
        read(REPOSITORY, 'held_sheet_refs'),
        read(REPOSITORY, 'read', SHEET),
        read(REPOSITORY, 'project_cells', [SHEET], components=requested)], held=[reference, artifact])
    sheet = populated['result']['sheet_ref']
    assert populated['status'] == 'completed' and held == [sheet]
    assert saved['input_source_ref'] == reference
    assert [cell['component'] for cell in cells] == requested
    assert {cell['sheet_ref'] for cell in cells} == {sheet}
