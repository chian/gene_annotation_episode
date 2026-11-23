"""The endpoint-signal repository on the custody-scoped store: population from the retained primary page and
figure of the source240/238 case, the saved sheet read back and its requested cells projected, through the real
runner."""
import json
from pathlib import Path

from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.evolutionary_history_evidence.literature_endpoint_signal_storage import POPULATION, REQUESTED, ENDPOINT_SIGNAL_REQUEST_SCHEMA

from .evolutionary_history_world import call, read, run, world  # noqa: F401

CALCULATIONS = Path(__file__).resolve().parents[2] / 'calculations/experimental_activity_evidence/tests/fixtures'
CASE = CALCULATIONS / 'research_reference/a105_quantitative_contributor_case_238/originals'
REPOSITORY = 'literature_endpoint_signal_storage:LiteratureEndpointSignalRepository'
SHEET = {'from_step': 0, 'path': ['result', 'sheet_ref']}


def retained(world, original, media_type, text=None):
    """A source record of the retained ``original`` bytes (and of ``text`` as its text representation); the
    source reference and the artifacts to pass in custody."""
    store = world['store']
    artifact = store.artifact(original, media_type)
    text_artifact = artifact if text is None else store.artifact(text, 'text/plain')
    reference = store.put('source', {'provider': 'test', 'accession': None, 'uri': None, 'artifact_ref': artifact,
                                     'text_ref': text_artifact, 'request_ref': None, 'version': None,
                                     'retrieved_at': None}, origin='external')['id']
    return reference, list(dict.fromkeys([artifact, text_artifact]))


def bound(value, references):
    if isinstance(value, dict):
        return {key: bound(item, references) for key, item in value.items()}
    if isinstance(value, list):
        return [bound(item, references) for item in value]
    return references.get(value, value) if isinstance(value, str) else value


def test_an_endpoint_signal_sheet_is_saved_read_back_and_its_cells_projected(world):  # noqa: F811
    selection = json.loads((CALCULATIONS / 'endpoint_signal_components/EXAMPLE_INPUT_002.json').read_text())
    page, page_artifacts = retained(world, (CASE / 'primary.html').read_bytes(), 'text/html',
                                    (CASE / 'primary_text.txt').read_text())
    figure, figure_artifacts = retained(world, (CASE / 'figure4.jpg').read_bytes(), 'image/jpeg')
    selection = bound(selection, {'source_kaster_primary': page, 'source_kaster_original_figure4': figure})
    requested = selection['requested_cells']
    arguments = {'version': POPULATION, 'selection': selection,
                 'return_context': {name: [] for name in
                                    ENDPOINT_SIGNAL_REQUEST_SCHEMA['properties']['return_context']['properties']}}
    populate = call(REPOSITORY, 'populate', arguments, scope=world['scope'], assignment={REQUESTED: requested})
    populate['arguments']['role'] = 'reader'
    populated, held, saved, cells = run(world, 'endpoint', [populate,
        read(REPOSITORY, 'held_sheet_refs'),
        read(REPOSITORY, 'read', SHEET),
        read(REPOSITORY, 'project_cells', [SHEET], components=requested)], held=[page, figure, *page_artifacts, *figure_artifacts])
    sheet = populated['result']['sheet_ref']
    assert populated['status'] == 'completed' and held == [sheet]
    assert saved['input_source_ref'] == page
    assert [cell['component'] for cell in cells] == requested
    assert {cell['sheet_ref'] for cell in cells} == {sheet}
